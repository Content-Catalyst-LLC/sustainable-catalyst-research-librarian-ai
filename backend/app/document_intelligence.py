from __future__ import annotations

import base64
from dataclasses import dataclass
import hashlib
from html.parser import HTMLParser
import io
import re
from typing import Any
from urllib.parse import urlparse

DOCUMENT_INTELLIGENCE_SCHEMA = "sc-research-librarian-document-intelligence/1.0"
DOCUMENT_SECTION_SCHEMA = "sc-research-librarian-document-section/1.0"
DOCUMENT_REFERENCE_SCHEMA = "sc-research-librarian-reference/1.0"
DOCUMENT_CITATION_SCHEMA = "sc-research-librarian-citation-mention/1.0"

_DOI_RE = re.compile(r"\b10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.I)
_ARXIV_RE = re.compile(r"\b(?:arXiv\s*:\s*)?(\d{4}\.\d{4,5})(?:v\d+)?\b", re.I)
_PMID_RE = re.compile(r"\bPMID\s*:\s*(\d{6,9})\b", re.I)
_ISBN_RE = re.compile(r"\b(?:ISBN(?:-1[03])?\s*:?\s*)?((?:97[89][- ]?)?[0-9][- 0-9]{8,16}[0-9X])\b", re.I)
_URL_RE = re.compile(r"https?://[^\s<>\]\[(){}\"']+", re.I)
_AUTHOR_YEAR_RE = re.compile(r"\((?:[A-Z][A-Za-z'’-]+(?:\s+et\s+al\.)?(?:\s*(?:;|,)\s*)?)+(?:,?\s*)?(?:19|20)\d{2}[a-z]?\)")
_NUMERIC_CITATION_RE = re.compile(r"\[(\d+(?:\s*[-,]\s*\d+)*)\]")
_REFERENCE_HEADING_RE = re.compile(r"^(references|bibliography|works cited|literature cited)\s*$", re.I)
_HEADING_NUMBER_RE = re.compile(r"^(?:(\d+(?:\.\d+)*)[.)]?\s+)(.{2,180})$")
_FIGURE_RE = re.compile(r"^(?:figure|fig\.)\s*(\d+[A-Za-z]?)?\s*[:.\-]?\s*(.*)$", re.I)
_TABLE_RE = re.compile(r"^table\s*(\d+[A-Za-z]?)?\s*[:.\-]?\s*(.*)$", re.I)
_EQUATION_RE = re.compile(r"^(?:equation|eq\.)\s*(\d+[A-Za-z]?)?\s*[:.\-]?\s*(.*)$", re.I)


def _clean(value: Any) -> str:
    return re.sub(r"[\t\r\f\v ]+", " ", str(value or "")).strip()


def _clean_multiline(value: Any) -> str:
    text = str(value or "").replace("\r\n", "\n").replace("\r", "\n")
    lines = [_clean(line) for line in text.split("\n")]
    out: list[str] = []
    blank = False
    for line in lines:
        if not line:
            if out and not blank:
                out.append("")
            blank = True
        else:
            out.append(line)
            blank = False
    return "\n".join(out).strip()


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def _dedupe(values: list[str], limit: int = 200) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for value in values:
        clean = _clean(value).strip(".,;)")
        key = clean.lower()
        if clean and key not in seen:
            seen.add(key)
            out.append(clean)
        if len(out) >= limit:
            break
    return out


class _HTMLStructureParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.blocks: list[tuple[str, str]] = []
        self._tag = ""
        self._buffer: list[str] = []
        self.title = ""
        self._title_mode = False

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        tag = tag.lower()
        if tag == "title":
            self._title_mode = True
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6", "p", "li", "figcaption", "caption", "blockquote", "pre"}:
            self._flush()
            self._tag = tag

    def handle_endtag(self, tag: str) -> None:
        tag = tag.lower()
        if tag == "title":
            self._title_mode = False
        if self._tag == tag:
            self._flush()

    def handle_data(self, data: str) -> None:
        if self._title_mode and data.strip():
            self.title = _clean((self.title + " " + data).strip())
        if self._tag:
            self._buffer.append(data)

    def _flush(self) -> None:
        if self._tag and self._buffer:
            text = _clean(" ".join(self._buffer))
            if text:
                self.blocks.append((self._tag, text))
        self._tag = ""
        self._buffer = []

    def close(self) -> None:
        self._flush()
        super().close()


def _html_to_text_and_hints(html: str) -> tuple[str, dict[str, Any]]:
    parser = _HTMLStructureParser()
    parser.feed(html)
    parser.close()
    lines: list[str] = []
    for tag, text in parser.blocks:
        if tag.startswith("h") and len(tag) == 2 and tag[1].isdigit():
            level = int(tag[1])
            lines.append("#" * level + " " + text)
        elif tag == "figcaption":
            lines.append("Figure: " + text)
        elif tag == "caption":
            lines.append("Table: " + text)
        else:
            lines.append(text)
    return "\n\n".join(lines), {"title": parser.title}


def _extract_pdf(data: bytes) -> tuple[str, list[dict[str, Any]], dict[str, Any], list[str]]:
    warnings: list[str] = []
    try:
        from pypdf import PdfReader
    except ImportError as exc:  # pragma: no cover
        raise ValueError("PDF parsing requires the pypdf runtime dependency.") from exc
    try:
        reader = PdfReader(io.BytesIO(data), strict=False)
    except Exception as exc:
        raise ValueError(f"Unable to parse PDF: {exc}") from exc
    pages: list[dict[str, Any]] = []
    all_text: list[str] = []
    for index, page in enumerate(reader.pages[:500], start=1):
        try:
            text = _clean_multiline(page.extract_text() or "")
        except Exception as exc:  # pragma: no cover - malformed page edge case
            text = ""
            warnings.append(f"Page {index} text extraction failed: {str(exc)[:180]}")
        pages.append({"page": index, "text": text})
        if text:
            all_text.append(text)
    metadata = {}
    raw_meta = reader.metadata or {}
    for key, value in dict(raw_meta).items():
        metadata[str(key).lstrip("/").lower()] = _clean(value)
    if not all_text:
        warnings.append("PDF contained no extractable text; an OCR stage may be required.")
    return "\n\n".join(all_text), pages, metadata, warnings


def _heading_level(line: str) -> tuple[int, str] | None:
    if line.startswith("#"):
        m = re.match(r"^(#{1,6})\s+(.{2,300})$", line)
        if m:
            return len(m.group(1)), _clean(m.group(2))
    m = _HEADING_NUMBER_RE.match(line)
    if m and len(line) <= 200:
        return min(6, m.group(1).count(".") + 1), _clean(m.group(2))
    normalized = line.strip()
    if 2 <= len(normalized) <= 120 and normalized.upper() == normalized and re.search(r"[A-Z]", normalized):
        return 2, normalized.title()
    known = {"abstract", "introduction", "background", "methods", "methodology", "materials and methods", "results", "discussion", "conclusion", "conclusions", "limitations", "acknowledgements", "acknowledgments", "references", "bibliography", "works cited", "appendix"}
    if normalized.lower().rstrip(":") in known:
        return 2, normalized.rstrip(":")
    return None


def _sections_from_pages(pages: list[dict[str, Any]], fallback_text: str) -> list[dict[str, Any]]:
    source_pages = pages or [{"page": None, "text": fallback_text}]
    sections: list[dict[str, Any]] = []
    current_heading = "Document text"
    current_level = 1
    current_page: int | None = None
    buffer: list[str] = []

    def flush() -> None:
        nonlocal buffer
        text = _clean_multiline("\n".join(buffer))
        if not text:
            buffer = []
            return
        position = len(sections)
        payload = f"{position}\n{current_heading}\n{current_page or 0}\n{text}"
        sections.append({
            "schema": DOCUMENT_SECTION_SCHEMA,
            "section_id": "section:" + _sha(payload)[:24],
            "heading": current_heading[:300],
            "level": current_level,
            "page": current_page,
            "position": position,
            "text": text[:80000],
            "char_count": len(text),
        })
        buffer = []

    for page_item in source_pages:
        page = page_item.get("page")
        for raw_line in str(page_item.get("text") or "").splitlines():
            line = _clean(raw_line)
            if not line:
                if buffer and buffer[-1] != "":
                    buffer.append("")
                continue
            heading = None if _REFERENCE_HEADING_RE.match(current_heading.strip()) else _heading_level(line)
            if heading:
                flush()
                current_level, current_heading = heading
                current_page = int(page) if page else None
            else:
                if current_page is None and page:
                    current_page = int(page)
                buffer.append(line)
    flush()
    if not sections and fallback_text:
        text = _clean_multiline(fallback_text)
        sections.append({"schema": DOCUMENT_SECTION_SCHEMA, "section_id": "section:" + _sha(text)[:24], "heading": "Document text", "level": 1, "page": None, "position": 0, "text": text[:80000], "char_count": len(text)})
    return sections[:500]


def _extract_identifiers(text: str, source_url: str = "") -> dict[str, Any]:
    dois = _dedupe(_DOI_RE.findall(text), 100)
    arxiv = _dedupe([m.group(1) for m in _ARXIV_RE.finditer(text)], 100)
    pmids = _dedupe([m.group(1) for m in _PMID_RE.finditer(text)], 100)
    isbns = _dedupe([m.group(1).replace(" ", "").replace("-", "") for m in _ISBN_RE.finditer(text)], 100)
    urls = _dedupe(_URL_RE.findall(text), 300)
    if source_url and source_url not in urls:
        urls.insert(0, source_url)
    return {"doi": dois, "arxiv": arxiv, "pmid": pmids, "isbn": isbns, "urls": urls}


def _extract_references(sections: list[dict[str, Any]]) -> list[dict[str, Any]]:
    reference_sections = [s for s in sections if _REFERENCE_HEADING_RE.match(str(s.get("heading") or "").strip())]
    if not reference_sections:
        return []
    raw_lines: list[str] = []
    for section in reference_sections:
        lines = [line.strip() for line in str(section.get("text") or "").splitlines() if line.strip()]
        raw_lines.extend(lines)
    entries: list[str] = []
    current = ""
    for line in raw_lines:
        starts = bool(re.match(r"^(?:\[?\d{1,4}\]?\s*[.)]?|[A-Z][A-Za-z'’-]+,\s*[A-Z])", line))
        if starts and current:
            entries.append(current)
            current = line
        else:
            current = (current + " " + line).strip()
    if current:
        entries.append(current)
    output: list[dict[str, Any]] = []
    for index, raw in enumerate(entries[:1000], start=1):
        ids = _extract_identifiers(raw)
        output.append({"schema": DOCUMENT_REFERENCE_SCHEMA, "reference_id": "reference:" + _sha(raw)[:24], "index": index, "raw": raw[:8000], "identifiers": ids})
    return output


def _extract_citations(text: str) -> list[dict[str, Any]]:
    mentions: list[dict[str, Any]] = []
    for pattern, style in ((_AUTHOR_YEAR_RE, "author-year"), (_NUMERIC_CITATION_RE, "numeric")):
        for match in pattern.finditer(text):
            start = max(0, match.start() - 140)
            end = min(len(text), match.end() + 140)
            raw = match.group(0)
            mentions.append({
                "schema": DOCUMENT_CITATION_SCHEMA,
                "citation_id": "citation:" + _sha(f"{match.start()}:{raw}")[:24],
                "style": style,
                "raw": raw,
                "offset": match.start(),
                "context": _clean(text[start:end])[:600],
            })
            if len(mentions) >= 2000:
                return mentions
    return mentions


def _extract_labeled_objects(sections: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]], list[dict[str, Any]]]:
    figures: list[dict[str, Any]] = []
    tables: list[dict[str, Any]] = []
    equations: list[dict[str, Any]] = []
    for section in sections:
        for line in str(section.get("text") or "").splitlines():
            clean = _clean(line)
            for pattern, bucket, kind in ((_FIGURE_RE, figures, "figure"), (_TABLE_RE, tables, "table"), (_EQUATION_RE, equations, "equation")):
                m = pattern.match(clean)
                if not m:
                    continue
                label = _clean(m.group(1) or "")
                caption = _clean(m.group(2) or "")
                bucket.append({
                    "object_id": f"{kind}:" + _sha(f"{section.get('section_id')}:{clean}")[:24],
                    "label": label,
                    "caption": caption[:2000],
                    "page": section.get("page"),
                    "section_id": section.get("section_id"),
                    "raw": clean[:3000],
                })
                break
    return figures[:500], tables[:500], equations[:500]


def parse_document(
    *,
    content: str = "",
    content_bytes: bytes | None = None,
    media_type: str = "text/plain",
    filename: str = "",
    source_url: str = "",
    title_hint: str = "",
) -> dict[str, Any]:
    media = (media_type or "text/plain").split(";", 1)[0].strip().lower()
    warnings: list[str] = []
    pages: list[dict[str, Any]] = []
    source_metadata: dict[str, Any] = {}
    extraction_method = "text-native"
    raw_text = content or ""

    if media == "application/pdf" or filename.lower().endswith(".pdf"):
        data = content_bytes or (base64.b64decode(content) if content else b"")
        raw_text, pages, source_metadata, pdf_warnings = _extract_pdf(data)
        warnings.extend(pdf_warnings)
        extraction_method = "pypdf"
    elif media in {"text/html", "application/xhtml+xml"} or filename.lower().endswith((".html", ".htm")):
        raw_text, hints = _html_to_text_and_hints(content)
        source_metadata.update(hints)
        extraction_method = "stdlib-html"
    elif media in {"text/markdown", "text/x-markdown"} or filename.lower().endswith((".md", ".markdown")):
        raw_text = _clean_multiline(content)
        extraction_method = "markdown-structural"
    else:
        raw_text = _clean_multiline(content)

    raw_text = raw_text[:2_000_000]
    if not raw_text and not pages:
        raise ValueError("Document contains no extractable text.")
    sections = _sections_from_pages(pages, raw_text)
    full_text = "\n\n".join(str(s.get("text") or "") for s in sections) or raw_text
    references = _extract_references(sections)
    citations = _extract_citations(full_text)
    identifiers = _extract_identifiers(full_text, source_url)
    figures, tables, equations = _extract_labeled_objects(sections)

    title = _clean(title_hint or source_metadata.get("title"))
    if not title and media in {"text/markdown", "text/x-markdown"}:
        top = re.search(r"(?m)^#\s+(.{2,300})$", content)
        if top:
            title = _clean(top.group(1))
    if not title:
        for section in sections[:3]:
            heading = _clean(section.get("heading"))
            if heading and heading.lower() not in {"document text", "abstract", "introduction"}:
                title = heading
                break
    if not title:
        title = _clean(filename) or "Untitled research document"

    authors: list[str] = []
    author_meta = _clean(source_metadata.get("author"))
    if author_meta:
        authors = [a.strip() for a in re.split(r"\s*[;,]\s*", author_meta) if a.strip()][:100]

    fingerprint_payload = "\n".join([media, filename, source_url, title, full_text])
    return {
        "schema": DOCUMENT_INTELLIGENCE_SCHEMA,
        "title": title[:500],
        "authors": authors,
        "source_url": source_url[:1600],
        "filename": filename[:500],
        "media_type": media,
        "extraction_method": extraction_method,
        "page_count": len(pages) if pages else None,
        "char_count": len(full_text),
        "word_count": len(re.findall(r"\S+", full_text)),
        "section_count": len(sections),
        "reference_count": len(references),
        "citation_count": len(citations),
        "table_count": len(tables),
        "figure_count": len(figures),
        "equation_count": len(equations),
        "identifiers": identifiers,
        "sections": sections,
        "references": references,
        "citations": citations,
        "tables": tables,
        "figures": figures,
        "equations": equations,
        "source_metadata": source_metadata,
        "warnings": warnings,
        "fingerprint": _sha(fingerprint_payload),
        "governance": {
            "deterministic_extraction": True,
            "ocr_performed": False,
            "llm_extraction": False,
            "not_evidence_judgment": True,
            "platform_core_governs_promoted_evidence": True,
        },
    }


def knowledge_metadata(result: dict[str, Any]) -> dict[str, Any]:
    return {
        "document_intelligence": {
            key: result.get(key)
            for key in (
                "schema", "media_type", "extraction_method", "page_count", "char_count", "word_count",
                "section_count", "reference_count", "citation_count", "table_count", "figure_count",
                "equation_count", "identifiers", "references", "citations", "tables", "figures",
                "equations", "fingerprint", "warnings", "governance",
            )
        },
        "sections": [
            {"heading": s.get("heading", "Document section"), "page": s.get("page"), "text": s.get("text", "")}
            for s in result.get("sections", [])
        ],
    }
