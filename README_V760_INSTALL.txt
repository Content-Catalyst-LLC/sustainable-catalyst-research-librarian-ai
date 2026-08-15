Research Librarian AI v7.6.0 — Workspace Research Handoff & Artifact Promotion

DEPLOYMENT ORDER
1. Push/deploy the v7.6.0 repository/backend first.
2. Confirm Render reports Research Librarian AI 7.6.0 and the backend is healthy.
3. Install/update WordPress with sustainable-catalyst-research-librarian-ai-wordpress-v7.6.0.zip.
4. Sign in with a Workspace/Library account and run the smoke tests below.

MAC TERMINAL
cd ~/Downloads
chmod +x PUSH_RESEARCH_LIBRARIAN_V760_PY312.sh
./PUSH_RESEARCH_LIBRARIAN_V760_PY312.sh

PRODUCTION SMOKE TEST
1. Open the Connected Research Workspace while authenticated.
2. Select a saved Library/project context or an authorized Research Room context.
3. Choose Promote to Workspace.
4. Prepare a Notebook handoff and verify the result shows a packet fingerprint and source count.
5. Download the handoff JSON and verify it contains:
   - schema sc-workspace-research-handoff/1.0
   - workspace_import_contract sc-workspace-research-import/1.0
   - source owner/scope provenance
   - packet_fingerprint
6. Confirm preparation does not claim the artifact was automatically imported or published.
7. Open Workspace separately and use the packet only through an explicit import workflow when that Workspace-side importer is available.
8. If testing a Research Room, verify a member can promote room-shared evidence but an outsider cannot.
9. Verify rejected sources are absent by default; include them only by deliberately enabling the option.
10. Verify prior v7.5 Research Rooms, v7.4 personal research state, v7.3 evidence evaluation, and ordinary Librarian questions still work.

STORAGE
Ancillary SQLite advances to schema 16. The Neon/Postgres knowledge index remains sc-research-librarian-knowledge-index/13.0. No Neon/Postgres knowledge-index migration is required.

IMPORTANT BOUNDARY
v7.6.0 creates a governed promotion outbox and fingerprinted Workspace handoff packet. It does not silently import or publish an artifact in Workspace. An export/import receipt confirms transfer only, never publication, editorial endorsement, or truth.
