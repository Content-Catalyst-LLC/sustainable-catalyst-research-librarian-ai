from __future__ import annotations

import app.main as main


def _summary(*, records: int, chunks: int = 0, embedded: int = 0) -> dict:
    return {
        "total_records": records,
        "indexed_titles": records,
        "indexed_chunks": chunks,
        "embedded_chunks": embedded,
        "semantic_coverage": (embedded / chunks * 100.0) if chunks else 0.0,
        "storage_engine": "sqlite",
        "schema_version": 10,
        "index_version": 1 if records else 0,
        "checksum": "test",
        "snapshot_count": 0,
        "staging_jobs": 0,
        "stalled_jobs": 0,
        "recovery_needed": False,
        "last_recovery_utc": "",
        "last_rollback_utc": "",
        "last_sync_utc": "2026-07-21T00:00:00+00:00" if records else "",
        "source_site": "https://sustainablecatalyst.com",
        "embedding_model": "gemini-embedding-001",
        "retrieval_profile": "balanced-v6.5.0",
        "benchmark_runs": 0,
    }


def test_status_separates_connected_provider_from_empty_index(monkeypatch) -> None:
    monkeypatch.setattr(main.store, "summary", lambda: _summary(records=0))
    monkeypatch.setattr(main, "provider_configured", lambda: True)
    monkeypatch.setattr(main, "_startup_snapshot", lambda summary=None: {"startup_state": "ready", "startup_phase": "ready", "startup_progress": 100, "service_started_utc": "2026-07-21T00:00:00+00:00", "uptime_seconds": 60, "ready": True})
    monkeypatch.setattr(main.provider_state, "last_success_utc", "2026-07-21T00:00:00+00:00")
    monkeypatch.setattr(main.provider_state, "last_failure_utc", "")
    status = main._status()
    assert status.state == "index-empty"
    assert status.generation_state == "online"
    assert status.index_state == "empty"
    assert status.recommended_action == "build-index"
    assert "Gemini connected" in status.label


def test_status_reports_pending_semantic_indexing(monkeypatch) -> None:
    monkeypatch.setattr(main.store, "summary", lambda: _summary(records=25, chunks=100, embedded=40))
    monkeypatch.setattr(main, "provider_configured", lambda: True)
    monkeypatch.setattr(main, "_startup_snapshot", lambda summary=None: {"startup_state": "ready", "startup_phase": "ready", "startup_progress": 100, "service_started_utc": "2026-07-21T00:00:00+00:00", "uptime_seconds": 60, "ready": True})
    monkeypatch.setattr(main.provider_state, "last_success_utc", "2026-07-21T00:00:00+00:00")
    monkeypatch.setattr(main.provider_state, "last_failure_utc", "")
    status = main._status()
    assert status.state == "indexing"
    assert status.index_state == "ready"
    assert status.embedding_state == "pending"
    assert status.pending_chunks == 60
    assert status.recommended_action == "continue-embeddings"
