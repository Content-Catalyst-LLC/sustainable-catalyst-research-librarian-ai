Research Librarian AI v8.0.0 — Installation and Production Smoke Test
=====================================================================

DEPLOYMENT ORDER
1. Push/deploy the v8.0.0 repository/backend first.
2. Confirm Render reports Research Librarian version 8.0.0 and the backend is healthy.
3. Install sustainable-catalyst-research-librarian-ai-wordpress-v8.0.0.zip in WordPress.
4. Do not create or run a Neon/Postgres migration for this release. The production knowledge-index schema remains 13.0 / Postgres schema 3.

MAC TERMINAL
cd ~/Downloads
chmod +x PUSH_RESEARCH_LIBRARIAN_V800_PY312.sh
./PUSH_RESEARCH_LIBRARIAN_V800_PY312.sh

PRODUCTION SMOKE TEST
1. Sign in to WordPress and open the Connected Research Workspace.
2. Select or create a saved research context linked to a project with a research objective.
3. Open Research lifecycle and create a lifecycle for the active context.
4. Confirm the lifecycle displays Frame → Discover → Evaluate → Organize → Collaborate → Synthesize → Promote → Preserve.
5. Confirm Frame readiness reflects the project objective/open-question state without changing the current stage automatically.
6. Move to Discover. Confirm the browser asks for explicit confirmation and the returned transition records the authenticated actor and prior/target stages.
7. Create a lifecycle checkpoint. Confirm it returns a SHA-256 fingerprint and remains visible in lifecycle history.
8. Back up the linked project and confirm research_lifecycles includes lifecycle, events, and checkpoints.
9. Confirm Discover globally still requires explicit Save to My Library before an external result becomes a private external-reference object.
10. Confirm Promote to Workspace still creates a governed handoff/outbox and does not claim automatic Workspace import or publication.
11. Log out and confirm private lifecycle/context controls are unavailable to anonymous visitors.

EXPECTED CONTRACTS
Plugin/backend version: 8.0.0
Connected Research API: sc-connected-research-api/2.0
Public workspace: sc-research-librarian-public-workspace/3.0
Research lifecycle: sc-research-lifecycle/1.0
Lifecycle summary: sc-research-lifecycle-summary/1.0
Lifecycle checkpoint: sc-research-lifecycle-checkpoint/1.0
Ancillary SQLite schema: 18
Knowledge index: sc-research-librarian-knowledge-index/13.0
Postgres schema: 3
New Postgres migration: NO
