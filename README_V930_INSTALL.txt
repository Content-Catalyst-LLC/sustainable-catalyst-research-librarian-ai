Research Librarian AI v9.3.0 — Peer Review, Replication & Scholarly Validation Environment

Order:
1. Push/tag the repository using PUSH_RESEARCH_LIBRARIAN_V930_PY312.sh.
2. Deploy the backend ZIP with deploy/contabo/upgrade_research_librarian_backend_v9_3_0_contabo.sh.
3. Require the deployer to finish with the v9.3 PASS line.
4. Install sustainable-catalyst-research-librarian-ai-wordpress-v9.3.0.zip in WordPress.

The v9.3 backend adds migration 008_peer_review_replication_validation.sql.
Core's .env.production is optional/unreadable-safe; deployment falls back to the existing Librarian Core write key.
