# Sustainable Catalyst Research Librarian AI v6.3.0

## v6.3.0 — Durable Knowledge Index, Sync Ledger, and Recovery

Research Librarian AI v6.3.0 makes the knowledge index restart-safe without requiring a paid database. WordPress remains the canonical publishing and recovery layer. FastAPI now maintains a transactional SQLite runtime index that can be rebuilt automatically from private, compressed WordPress snapshots after an ephemeral Render restart.

### Core v6.3.0 capabilities

- Transactional, multi-batch synchronization: the active index is replaced only after every expected batch arrives.
- Idempotent job IDs and duplicate-batch protection prevent retries from applying the same synchronization twice.
- A SQLite runtime index stores records, metadata, staging jobs, tombstones, checksums, sync history, and rollback snapshots.
- WordPress creates canonical gzip snapshots in a private upload directory protected from direct web access.
- Automatic cold-start recovery detects an empty backend and rehydrates it from the latest verified WordPress snapshot.
- Record-level content hashes distinguish inserts, updates, unchanged records, and deletions.
- Saved, unpublished, trashed, and deleted WordPress records enter a bounded incremental synchronization queue.
- Deleted records create tombstones so removals remain auditable and cannot silently reappear.
- Administrators can compare WordPress and backend manifests, process the incremental queue, create snapshots, recover an empty backend, and roll back the runtime index.
- The v6.2.1 endpoint diagnostics, rolling limits, nonce retry, and black-and-green terminal question field remain intact.

### Primary operations

1. Open **Research Librarian AI → Python Intelligence**.
2. Save the backend URL and shared integration key, then select **Test Backend**.
3. Select **Transactional Full Sync** to create the canonical WordPress snapshot and atomically replace the runtime index.
4. Confirm that WordPress and backend record counts and checksums match.
5. Leave **Automatic cold-start recovery** enabled for free Render deployments.
6. Use **Process Incremental Queue** after editorial changes, **Recover Empty Backend** after an empty-index event, and **Rollback Runtime Index** only when reverting a bad committed sync.

### Runtime and deployment

The included push script requires Python 3.12 and verifies the actual temporary environment before installing dependencies. The Render blueprint pins Python 3.12.12. SQLite remains runtime storage rather than the canonical source, so an ephemeral filesystem is supported: WordPress holds the private recovery snapshot and can restore the backend automatically.

The Python service exposes `/health`, `/status`, `/v1/knowledge/summary`, `/v1/knowledge/manifest`, `/v1/knowledge/snapshots`, `/v1/knowledge/rollback`, `/v1/knowledge/sync`, `/v1/retrieve`, and `/v1/ask`.

See `docs/V630_DURABLE_KNOWLEDGE_INDEX_SYNC_LEDGER_RECOVERY.md` for the release contract and recovery model.

## v6.1.1 — Gemini Authorization Key Compatibility Patch

Version 6.1.1 repairs compatibility with modern Google AI Studio authorization keys, adds actionable Gemini key and quota diagnostics, preserves the v6.1.0 live AI restoration, and keeps deterministic routing as the clearly labeled resilience layer.

### Highlights

- Visible AI Online, Offline, Not Configured, and Not Yet Tested states
- Exact administrator provider errors, HTTP status, transport status, latency, and last-success records
- Gemini model discovery and one-click connection testing
- Country recognition using a 249-record ISO registry
- Pakistan → Country Intelligence → `PAK` routing
- Site Intelligence, Dashboard Studio, Cross-Domain Comparison, Sources and Methodology, and Public Observatories as first-class routes
- Weighted deterministic routing instead of first-match keyword selection
- Dedicated Research Librarian AI admin folder with consolidated subpages
- Public AI status, admin AI test, and admin model-list REST endpoints
- Gemini header authentication, system instructions, model normalization, and configurable timeout
- Regression tests for bootstrap, shortcodes, REST routes, menu consolidation, Pakistan routing, and climate-dashboard routing

See `docs/V610_LIVE_AI_RESTORATION_ADMIN_CONSOLIDATION.md`.


Research Librarian v5.6.0 adds the full Feature Suggestions Feedback Bridge. Contextual route ratings, wrong-route reports, source-card issues, grounding concerns, missing topics, and missing-tool requests are retained in the Librarian queue, normalized for Feature Suggestions v3, published as privacy-minimized Site Intelligence events, protected against duplicate submissions, and assigned receipt-based status records.

## v5.6.0 feedback bridge

- Contextual 1–5 route ratings
- Wrong-route and unclear-answer reports
- Missing-source, missing-topic, missing-tool, and grounding reports
- Feature Suggestions v3 adapter with no hard dependency
- Local queue fallback when Feature Suggestions is unavailable
- Receipt-protected submission status
- 24-hour duplicate protection
- Administrator bridge diagnostics and JSON export
- `librarian.feedback_submitted` and `librarian.feedback_bridge_created` events
- No raw conversation, email, IP, or API-key fields in shared events

**Stable Operations Polish and Release Notes**

Research Librarian v5.5.0 completes the public 5.x roadmap with release-readiness checks, daily operational validation, migration and recovery verification, Workbench and Decision Studio integration health, bounded audit history, administrator operations exports, and public-safe release notes.

## v5.5.0 operations

- Open **Research Librarian AI → Operations**.
- Run the readiness checks and review required versus recommended findings.
- Validate migrations after upgrading.
- Confirm recovery assets, index maintenance, and destination availability.
- Acknowledge the release only after production review.

Public shortcodes:

```text
[sc_research_librarian_release_notes]
[sc_research_librarian_operations_status]
```

Administrator REST endpoints:

```text
GET  /wp-json/sc-research-librarian/v1/operations/status
POST /wp-json/sc-research-librarian/v1/operations/check
GET  /wp-json/sc-research-librarian/v1/operations/export
```

Public release notes:

```text
GET /wp-json/sc-research-librarian/v1/operations/release-notes
```

## Main v5.3.2 shortcodes

```text
[sc_research_librarian mode="article-paths" title="Research Path"]
[sc_research_librarian_article_path_embed title="Research Path" context="calculus systems modeling" question="I need to graph and analyze this formula"]
[sc_research_librarian_article_map_summary title="Research Librarian Article Map Integration"]
[sc_research_librarian_article_route_cards title="Related Research Routes"]
```

## After activation

Go to **Research Librarian AI → Advanced → Article Map Embeds** and review the available path templates. Use the article path embed inside article maps, formula-heavy pages, and long research pages where a reader needs a next step into Workbench, Decision Studio, a module artifact, or the Knowledge Library.

# Sustainable Catalyst Research Librarian v5.1.0

**Live Public Experience QA, Prompt Library, and UX Calibration**

Research Librarian v5.1.0 is a post-stable-release refinement build. It keeps the v5.0.0 stable public release layer and adds a live public experience QA dashboard, prompt library, QA checklist, and public-safe UX status views.

## Main public shortcode

```text
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
```

## New v5.1.0 shortcodes

```text
[sc_research_librarian mode="live-ux" title="Research Librarian Live Public Experience"]
[sc_research_librarian mode="prompt-library" title="Research Librarian Prompt Library"]
[sc_research_librarian_live_ux_summary title="Research Librarian Live Public Experience"]
[sc_research_librarian_prompt_library title="Research Librarian Public Prompt Library"]
[sc_research_librarian_live_qa_checklist title="Research Librarian Live QA Checklist"]
```

## After activation

Go to **Research Librarian AI → Advanced → Live Public Experience QA** and click **Run Live UX QA**. Then test the public prompt library against the live page.

# Sustainable Catalyst Research Librarian v5.0.0

Stable public release layer for source-aware routing, Gemini retrieval, public answer UX, guided research paths, Workbench and Decision Studio handoffs, governance, security, observability, documentation, and release acceptance checks.

## v5.0.0 additions

- Stable public release readiness score
- Launch checklist
- Admin acceptance gate
- Public-safe stable release summary
- Public-safe launch checklist summary
- Admin-only release export

# Sustainable Catalyst Research Librarian AI

Current version: **v4.9.1 — Public Documentation Page Generator**.

The Research Librarian is the source-aware routing, retrieval, guided-path, and documentation layer for Sustainable Catalyst. It combines deterministic routing, source-aware recommendations, a knowledge index, Gemini embeddings, public answer UX, guided research paths, handoff payloads, query review, governance, maintenance, recovery, security, observability, curation, integration contracts, and now public-safe documentation generation.

## v4.9.1 highlights

- Public documentation page generator
- Documentation catalog
- Generated HTML and Markdown documentation payloads
- Shortcode inventory
- Endpoint group summary
- Admin Documentation dashboard
- Admin-only documentation export
- Public-safe documentation summary shortcode

## Main shortcode

```text
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
```

## Documentation shortcodes

```text
[sc_research_librarian mode="documentation-summary" title="Research Librarian Documentation"]
[sc_research_librarian_documentation_summary title="Research Librarian Documentation"]
[sc_research_librarian_docs_catalog title="Research Librarian Documentation Catalog"]
[sc_research_librarian_documentation_page title="Research Librarian Public Documentation"]
```

## Documentation endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/documentation/status
GET  /wp-json/sc-research-librarian-ai/v1/documentation/catalog
GET  /wp-json/sc-research-librarian-ai/v1/documentation/page
POST /wp-json/sc-research-librarian-ai/v1/documentation/generate
GET  /wp-json/sc-research-librarian-ai/v1/documentation/export
POST /wp-json/sc-research-librarian-ai/v1/documentation/reset
```


## v4.9.1 — Documentation Snapshot Visibility Fix

This hotfix replaces the JavaScript-only documentation snapshot action with nonce-protected admin-post actions, adds visible success/reset notices, adds a generated documentation preview in the admin screen, and provides copy-ready Markdown plus a server-side JSON export.


## v5.2.0 — Public Route Quality Tuning and Source Card Ranking

This release adds a public route-quality layer for tuning the visitor-facing Research Librarian answer experience. It improves source-card ordering, prompt-to-route diagnostics, route repair suggestions, and calibration reporting.

### Added

- Route quality status endpoint
- Source-card ranking endpoint
- Admin route-quality calibration dashboard
- Public route-quality summary shortcode
- Public source-ranking summary shortcode
- Dominant prompt signal detection
- Broad-route demotion for specialized questions
- Route repair suggestions for weak or mismatched answers

### Shortcodes

```text
[sc_research_librarian_route_quality_summary title="Research Librarian Route Quality"]
[sc_research_librarian_source_ranking_summary title="Research Librarian Source Card Ranking"]
```

### Endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/quality/status
POST /wp-json/sc-research-librarian-ai/v1/quality/rank
POST /wp-json/sc-research-librarian-ai/v1/quality/run-calibration
GET  /wp-json/sc-research-librarian-ai/v1/quality/export
```


## v5.3.2 activation note

The v5.3.2 plugin zip uses the stable WordPress folder slug `sustainable-catalyst-research-librarian-ai`. If WordPress shows an activation fatal from a previous package, deactivate older versioned copies of the Research Librarian plugin first, then activate v5.3.2. The fatal is usually caused by two active copies declaring the same PHP class.


## v5.3.2 Activation Repair

v5.3.2 adds a repair layer for stale or duplicate WordPress activation records. If WordPress shows a duplicate-copy notice after an older Research Librarian folder was deleted, use the repair button shown in the admin notice. The repair removes missing or duplicate Research Librarian entries from `active_plugins` while preserving the current stable plugin folder.

Verification endpoint:

```text
/wp-json/sc-research-librarian-ai/v1/health
```

Admin-only diagnostics:

```text
/wp-json/sc-research-librarian-ai/v1/activation/status
```

## v5.4.0 pre-v5.4 integration bridge

The repository now includes a compatibility bridge for Feature Suggestions v3, Site Intelligence shared events, and typed Workbench/Decision Studio handoff preparation. Public deep-link actions remain reserved for v5.4.0. See `docs/V533_PRE_V54_INTEGRATION_BRIDGE.md`.


## v5.4.0 — Decision Studio / Workbench Deep-Link Actions

Adds public Route Action Center actions, typed `sc-research-handoff/1.1` payloads, 30-minute handoff tokens, destination resolution, fallback navigation, and shared platform events.


## v5.9.0 Adaptive Prompt and Survey Experiences

The v5.9.0 layer adds a configurable rules engine for contextual prompts and surveys. Administrators can target low-confidence results, zero-source outcomes, route abandonment, completed paths, tool demand, and Workbench or Decision Studio handoffs. Experiences are consent-aware by default and include daily caps, cooldowns, and dismissal windows. Survey and feature-request actions can hand structured context to Feature Suggestions through `scfs_research_librarian_survey_handoff`, while custom consumers can use `sc_rl_adaptive_survey_handoff`. Site Intelligence receives privacy-minimized interaction events rather than response text.

Shortcode:

```text
[sc_research_librarian_adaptive_experience trigger="low_confidence" route="infrastructure-resilience"]
```

Public endpoints evaluate and record experiences; administrator-only endpoints expose rule definitions and aggregate analytics.

## v5.7.0 Research Demand and Knowledge-Gap Intelligence

The v5.7.0 layer aggregates saved route sessions, visitor feedback, Feature Suggestions bridge records, source coverage, low-confidence outcomes, guided-path demand, and evaluation failures into privacy-conscious demand and gap reports. It includes 30-day, 90-day, and all-time windows, advisory opportunity scoring, a protected JSON export, an administrator dashboard, optional thresholded public summaries, and aggregate Site Intelligence events. Raw conversations are not exposed publicly, and all opportunity recommendations remain subject to human review.

Administrator endpoints:

- `GET /wp-json/sc-research-librarian/v1/intelligence/demand`
- `POST /wp-json/sc-research-librarian/v1/intelligence/demand/refresh`
- `GET /wp-json/sc-research-librarian/v1/intelligence/demand/export`
- `GET /wp-json/sc-research-librarian/v1/intelligence/demand/public` (only when enabled)

Public shortcode: `[sc_research_demand_summary]` (disabled by default).

## Closed-loop route improvement

v5.9.0 converts reviewed feedback into versioned route-change proposals with deterministic before/after tests, regression gates, human approval, provenance, audit history, and rollback snapshots. Approved changes are applied through the existing editorial curation registry.

## v6.0.1 — WordPress Bootstrap Registration Repair

Version 6.0.1 fixes the silent bootstrap failure that allowed WordPress to display the plugin as active while preventing Settings pages, shortcodes, REST routes, and module initializers from registering. The repair removes the self-detecting class guard, uses collision-safe v6 internal names, preserves backward compatibility, and includes a standalone regression test.

## v6.0.0 — Integrated Research Guidance Platform

Version 6.0.0 unifies the complete Research Librarian workflow: source-aware routing, article-map paths, Workbench and Decision Studio actions, Feature Suggestions feedback, demand and gap intelligence, adaptive survey experiences, and regression-protected route improvement.

Public shortcodes:

- `[sc_research_guidance_platform]`
- `[sc_research_guidance_journey]`

Administrator REST endpoints:

- `GET /wp-json/sc-research-librarian/v1/platform/guidance/status`
- `GET /wp-json/sc-research-librarian/v1/platform/guidance/export`

Public journey endpoint:

- `GET /wp-json/sc-research-librarian/v1/platform/guidance/journey`
