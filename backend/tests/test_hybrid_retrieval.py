from pathlib import Path
import tempfile

from app.chunking import chunk_record
from app.models import KnowledgeChunk, KnowledgeRecord
from app.provider import verify_citations
from app.retrieval import retrieve_with_diagnostics
from app.store import KnowledgeStore


def record(record_id: str, title: str, content: str, **kwargs) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=title,
        url=f"https://sustainablecatalyst.com/{record_id}/",
        content=content,
        **kwargs,
    )


def test_section_metadata_creates_page_aware_chunks() -> None:
    item = record(
        "foundation-pdf",
        "Foundation Document",
        "fallback text",
        post_type="document",
        metadata={
            "sections": [
                {"heading": "Planetary boundaries", "page": 14, "text": "A safe operating space depends on ecological ceilings."}
            ]
        },
    )
    chunks = chunk_record(item)
    page_chunks = [chunk for chunk in chunks if chunk.page == 14]
    assert page_chunks
    assert page_chunks[0].heading == "Planetary boundaries"
    assert "safe operating space" in page_chunks[0].passage


def test_bm25_section_passage_beats_generic_summary() -> None:
    records = [
        record("generic", "Sustainability", "General sustainability overview."),
        record(
            "boundaries",
            "Planetary Boundaries and Development",
            "The safe operating space is defined through climate change and biosphere integrity thresholds.",
            headings=["Safe operating space"],
        ),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    results, diagnostics = retrieve_with_diagnostics("biosphere integrity safe operating space", records, chunks, 5)
    assert results[0].id == "boundaries"
    assert results[0].section == "Safe operating space"
    assert results[0].lexical_score > 0
    assert diagnostics["retrieval_mode"] == "exact-title+bm25+rrf"


def test_exact_title_priority_survives_chunk_fusion() -> None:
    records = [
        record("exact", "Systems Thinking", "Short introduction."),
        record("verbose", "Systems Analysis Handbook", "Systems thinking systems thinking systems thinking feedback loops and leverage points."),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    results, _ = retrieve_with_diagnostics("Systems Thinking", records, chunks, 5)
    assert results[0].id == "exact"
    assert results[0].exact_title_match is True


def test_semantic_similarity_is_fused_when_vectors_exist() -> None:
    records = [
        record("alpha", "Urban Resilience", "Infrastructure adaptation."),
        record("beta", "Community Capacity", "Social networks and recovery."),
    ]
    chunks = [
        KnowledgeChunk(chunk_id="a", record_id="alpha", heading="Adaptation", passage="Infrastructure adaptation", embedding=[1.0, 0.0]),
        KnowledgeChunk(chunk_id="b", record_id="beta", heading="Community", passage="Social recovery networks", embedding=[0.0, 1.0]),
    ]
    results, diagnostics = retrieve_with_diagnostics("recovery capacity", records, chunks, 5, [0.0, 1.0])
    assert results[0].id == "beta"
    assert results[0].semantic_score == 1.0
    assert diagnostics["semantic_used"] is True


def test_citation_verification_accepts_known_sources_and_blocks_invention() -> None:
    records = [record("one", "Verified Record", "Evidence text")]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    matches, _ = retrieve_with_diagnostics("Verified Record", records, chunks, 5)
    valid = verify_citations("This is grounded. [SC1]", matches)
    invalid = verify_citations("Invented [SC9](https://example.com/fake)", matches)
    invented_route = verify_citations("Grounded label, invented route [SC1](/platform/not-a-real-route/)", matches)
    assert valid["ok"] is True
    assert invalid["ok"] is False
    assert invalid["invalid_citations"] == ["SC9"]
    assert invalid["unknown_urls"]
    assert invented_route["ok"] is False
    assert invented_route["unknown_urls"] == ["/platform/not-a-real-route/"]


def test_embedding_queue_is_persistent_and_resumable() -> None:
    path = Path(tempfile.mkdtemp()) / "hybrid.sqlite3"
    store = KnowledgeStore(path)
    store.sync(
        [record("one", "Verified Record", "A detailed evidence passage about systems and feedback.")],
        "replace",
        job_id="hybrid-sync",
    )
    pending = store.pending_chunks(10, "gemini-embedding-001")
    assert pending
    assert store.save_chunk_embedding(pending[0].chunk_id, "gemini-embedding-001", [0.1, 0.2, 0.3])
    status = store.embedding_status()
    assert status["embedded_chunks"] == 1
    assert status["pending_chunks"] == status["indexed_chunks"] - 1


def test_unchanged_chunk_retains_embedding_across_rebuild() -> None:
    path = Path(tempfile.mkdtemp()) / "retained.sqlite3"
    local_store = KnowledgeStore(path)
    item = record("stable", "Stable Record", "A stable passage about feedback and resilience.")
    local_store.sync([item], "replace", job_id="stable-sync-1")
    first = local_store.pending_chunks(10, "gemini-embedding-001")[0]
    assert local_store.save_chunk_embedding(first.chunk_id, "gemini-embedding-001", [0.4, 0.5])
    local_store.sync([item], "replace", job_id="stable-sync-2")
    retained = {chunk.chunk_id: chunk for chunk in local_store.chunks()}[first.chunk_id]
    assert retained.embedding == [0.4, 0.5]
    assert retained.embedding_model == "gemini-embedding-001"


def test_changed_chunk_invalidates_only_its_prior_embedding() -> None:
    path = Path(tempfile.mkdtemp()) / "invalidated.sqlite3"
    local_store = KnowledgeStore(path)
    original = record("changing", "Changing Record", "The first version discusses water systems.")
    local_store.sync([original], "replace", job_id="changing-sync-1")
    first = next(chunk for chunk in local_store.pending_chunks(10, "gemini-embedding-001") if chunk.heading == "Article text")
    assert local_store.save_chunk_embedding(first.chunk_id, "gemini-embedding-001", [0.7, 0.1])
    changed = record("changing", "Changing Record", "The revised version discusses energy systems and storage.")
    local_store.sync([changed], "replace", job_id="changing-sync-2")
    chunks = local_store.chunks()
    assert chunks
    assert all(chunk.embedding is None for chunk in chunks)
    assert local_store.embedding_status()["embedded_chunks"] == 0
