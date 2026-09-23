Research Librarian AI v8.7.0 — Core Evidence Bridge

Release order
1. Push/tag the v8.7.0 repository to GitHub.
2. Deploy the v8.7.0 Python backend to Contabo before installing WordPress.
3. Verify /health reports version 8.7.0 and ready=true.
4. Verify Platform Core v3.3+ remains compatible and write-ready.
5. Verify /v1/core/evidence/capabilities exposes source-snapshot and passage-evidence promotion.
6. Verify v8.6 source identity, v8.5 document intelligence, v8.4 retrieval, and v8.3 durable jobs remain active.
7. Install the v8.7.0 WordPress package.

Governance boundary
- Librarian selects/resolves source and passage candidates.
- Core stores governed SourceSnapshot/EvidenceRecord objects.
- Default passage promotion is neutral, unreviewed, and has no inferred confidence.
- No automatic claim creation, stance inference, confidence inference, truth judgment, or conclusion promotion occurs.
- Citation-only source stubs must be hydrated before snapshot promotion.

VPS runtime root
/opt/sustainable-catalyst/research-librarian-ai
