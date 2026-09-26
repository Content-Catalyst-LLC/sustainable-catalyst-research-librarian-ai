from __future__ import annotations

import base64
import os
from pathlib import Path
import shutil

TEST_DATA = Path('/tmp/sc-rl-tests-v850-document-intelligence')
shutil.rmtree(TEST_DATA, ignore_errors=True)
os.environ.setdefault('SC_RL_BACKEND_API_KEY', 'test-key')
os.environ.setdefault('SC_RL_DATA_DIR', str(TEST_DATA))

from fastapi.testclient import TestClient

from app.document_intelligence import DOCUMENT_INTELLIGENCE_SCHEMA, knowledge_metadata, parse_document
from app.main import app
from app.models import KnowledgeRecord
from app.chunking import chunk_record


def test_markdown_scholarly_structure_identifiers_and_references() -> None:
    text = '''# Storage Systems Review

## Abstract
Battery storage is compared with pumped storage (Ahmad, 2026).

## Methods
The dataset is archived at https://example.org/data. DOI 10.1234/example.5678.

## Results
Figure 1: Comparative efficiency by technology
Table 1: Summary statistics
Equation 1: E = mc^2

## References
1. Ahmad, T. (2026). Storage systems. doi:10.5555/reference.1
2. Smith, J. (2025). Grid balancing. https://example.org/paper
'''
    result = parse_document(content=text, media_type='text/markdown', filename='review.md')
    assert result['schema'] == DOCUMENT_INTELLIGENCE_SCHEMA
    assert result['title'] == 'Storage Systems Review'
    assert result['section_count'] >= 4
    assert '10.1234/example.5678' in [x.lower() for x in result['identifiers']['doi']]
    assert result['reference_count'] == 2
    assert result['citation_count'] >= 1
    assert result['figure_count'] == 1
    assert result['table_count'] == 1
    assert result['equation_count'] == 1
    assert result['governance']['llm_extraction'] is False


def test_html_parser_preserves_headings_and_caption_objects() -> None:
    html = '<html><head><title>Carbon Study</title></head><body><h1>Introduction</h1><p>Carbon pathways.</p><h2>Results</h2><p>See [1].</p><figure><figcaption>Emissions pathway</figcaption></figure><table><caption>Scenario totals</caption></table></body></html>'
    result = parse_document(content=html, media_type='text/html', filename='study.html')
    assert result['title'] == 'Carbon Study'
    headings = [s['heading'] for s in result['sections']]
    assert 'Introduction' in headings
    assert 'Results' in headings
    assert result['citation_count'] >= 1
    assert result['figure_count'] == 1
    assert result['table_count'] == 1


def test_document_metadata_feeds_section_aware_chunks() -> None:
    result = parse_document(content='# Introduction\nSolar evidence.\n\n## Methods\nMeasured output.', media_type='text/markdown')
    meta = knowledge_metadata(result)
    record = KnowledgeRecord(id='doc-1', title='Study', url='urn:test:1', content='fallback', metadata=meta)
    chunks = chunk_record(record)
    headings = {c.heading for c in chunks}
    assert 'Introduction' in headings
    assert 'Methods' in headings


def test_api_exposes_document_capabilities_and_parse_contract() -> None:
    client = TestClient(app)
    headers = {'X-SC-RL-Key': 'test-key'}
    cap = client.get('/v1/documents/capabilities', headers=headers)
    assert cap.status_code == 200
    assert cap.json()['version'] == '10.6.0'
    assert cap.json()['schema'] == DOCUMENT_INTELLIGENCE_SCHEMA
    parsed = client.post('/v1/documents/parse', headers=headers, json={'content': '# Test Paper\n\n## Abstract\nEvidence text.', 'media_type': 'text/markdown'})
    assert parsed.status_code == 200
    body = parsed.json()
    assert body['document']['title'] == 'Test Paper'
    assert body['knowledge_metadata']['sections']


def test_async_document_intelligence_job_is_enqueued() -> None:
    client = TestClient(app)
    headers = {'X-SC-RL-Key': 'test-key'}
    response = client.post('/v1/documents/parse/async', headers=headers, json={'content': '## Abstract\nDurable parsing.', 'media_type': 'text/markdown'})
    assert response.status_code == 202
    assert response.json()['job']['job_type'] == 'document-intelligence'


def test_pdf_parser_reports_pages_metadata_and_ocr_boundary() -> None:
    import io
    from pypdf import PdfWriter
    stream = io.BytesIO()
    writer = PdfWriter()
    writer.add_blank_page(width=100, height=100)
    writer.add_metadata({'/Title': 'PDF Research Note', '/Author': 'Researcher One'})
    writer.write(stream)
    result = parse_document(content_bytes=stream.getvalue(), media_type='application/pdf', filename='note.pdf')
    assert result['title'] == 'PDF Research Note'
    assert result['page_count'] == 1
    assert result['extraction_method'] == 'pypdf'
    assert result['authors'] == ['Researcher One']
    assert result['governance']['ocr_performed'] is False
    assert any('OCR' in warning for warning in result['warnings'])
