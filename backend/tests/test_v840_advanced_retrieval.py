from __future__ import annotations

import os
from pathlib import Path
import shutil

TEST_DATA = Path('/tmp/sc-rl-tests-v840-advanced')
shutil.rmtree(TEST_DATA, ignore_errors=True)
os.environ.setdefault('SC_RL_BACKEND_API_KEY', 'test-key')
os.environ.setdefault('SC_RL_DATA_DIR', str(TEST_DATA))

from fastapi.testclient import TestClient

from app.advanced_retrieval import (
    ADVANCED_RETRIEVAL_SCHEMA,
    advanced_retrieve_with_diagnostics,
    apply_retrieval_filters,
    build_query_plan,
)
from app.chunking import chunk_record
from app.main import app
from app.models import KnowledgeRecord


def record(record_id: str, title: str, content: str, **kwargs) -> KnowledgeRecord:
    return KnowledgeRecord(
        id=record_id,
        title=title,
        url=kwargs.pop('url', f'https://example.test/{record_id}/'),
        content=content,
        summary=kwargs.pop('summary', content[:500]),
        **kwargs,
    )


def test_query_plan_decomposes_comparative_request_without_generative_expansion() -> None:
    plan = build_query_plan('Compare solar storage versus wind storage', 4)
    queries = [item['query'].lower() for item in plan['variants']]
    assert plan['intent'] == 'comparative-research'
    assert plan['generative_expansion'] is False
    assert queries[0] == 'compare solar storage versus wind storage'
    assert any('solar storage' in query for query in queries[1:])
    assert any('wind storage' in query for query in queries[1:])


def test_metadata_taxonomy_and_date_filters_are_applied_before_ranking() -> None:
    records = [
        record(
            'solar', 'Solar Systems', 'solar generation storage', post_type='article', source='wordpress',
            modified_utc='2026-08-10T12:00:00Z', taxonomies={'topic': ['energy']}, series='Energy Systems',
        ),
        record(
            'water', 'Water Systems', 'water infrastructure', post_type='page', source='wordpress',
            modified_utc='2025-01-01T00:00:00Z', taxonomies={'topic': ['water']}, series='Infrastructure',
        ),
    ]
    selected, diagnostics = apply_retrieval_filters(
        records,
        {
            'post_types': ['article'],
            'taxonomies': {'topic': ['energy']},
            'modified_from_utc': '2026-01-01T00:00:00Z',
        },
    )
    assert [item.id for item in selected] == ['solar']
    assert diagnostics['active'] is True
    assert diagnostics['records_removed'] == 1


def test_multi_query_fusion_preserves_comparative_sources_and_reports_diagnostics() -> None:
    records = [
        record('solar', 'Solar Storage Systems', 'solar batteries storage dispatch photovoltaic systems'),
        record('wind', 'Wind Storage Systems', 'wind generation storage dispatch turbine systems'),
        record('other', 'Water Treatment', 'membrane filtration drinking water systems'),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    results, diagnostics = advanced_retrieve_with_diagnostics(
        'Compare solar storage versus wind storage', records, chunks, limit=2,
        calibration={'advanced': {'max_queries': 4, 'candidate_pool': 10}},
    )
    assert {item.id for item in results} == {'solar', 'wind'}
    assert diagnostics['schema'] == ADVANCED_RETRIEVAL_SCHEMA
    assert diagnostics['multi_query_enabled'] is True
    assert diagnostics['query_plan']['variant_count'] >= 3
    assert diagnostics['candidate_count'] >= 2
    assert any('multi-query-consensus' in item.retrieval_reasons for item in results)


def test_duplicate_canonical_urls_are_suppressed() -> None:
    records = [
        record('canonical', 'Carbon Accounting Guide', 'carbon accounting scope boundaries', url='https://example.test/carbon/?utm_source=a'),
        record('mirror', 'Carbon Accounting Guide Copy', 'carbon accounting scope boundaries', url='https://example.test/carbon/?utm_source=b'),
        record('distinct', 'Carbon Inventory Methods', 'carbon inventory methods emissions factors'),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    results, diagnostics = advanced_retrieve_with_diagnostics('carbon accounting boundaries', records, chunks, limit=3)
    ids = [item.id for item in results]
    assert not ({'canonical', 'mirror'} <= set(ids))
    assert diagnostics['duplicate_count'] >= 1
    assert any(item['reason'] == 'canonical-url' for item in diagnostics['duplicates_removed'])


def test_exact_title_remains_decisive_after_advanced_reranking() -> None:
    records = [
        record('exact', 'Systems Thinking', 'short systems introduction'),
        record('verbose', 'Systems Thinking Expanded Handbook', 'systems thinking ' * 40 + 'feedback leverage'),
    ]
    chunks = [chunk for item in records for chunk in chunk_record(item)]
    results, diagnostics = advanced_retrieve_with_diagnostics('Systems Thinking', records, chunks, limit=2)
    assert results[0].id == 'exact'
    assert results[0].exact_title_match is True
    assert diagnostics['rerank_enabled'] is True


def test_api_exposes_query_plan_and_advanced_explain_contract() -> None:
    client = TestClient(app)
    headers = {'X-SC-RL-Key': 'test-key'}
    plan = client.post('/v1/retrieval/plan', headers=headers, json={'query': 'solar versus wind', 'limit': 5})
    assert plan.status_code == 200
    assert plan.json()['plan']['schema'] == 'sc-research-librarian-query-plan/1.0'

    explain = client.post(
        '/v1/retrieve/explain',
        headers=headers,
        json={'query': 'systems evidence', 'limit': 5, 'advanced': True, 'include_semantic': False},
    )
    assert explain.status_code == 200
    body = explain.json()
    assert body['schema'] == ADVANCED_RETRIEVAL_SCHEMA
    assert body['diagnostics']['retrieval_mode'].startswith('exact-title+bm25')
    assert body['diagnostics']['advanced_enabled'] is True
