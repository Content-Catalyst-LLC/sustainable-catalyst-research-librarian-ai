# Sustainable Catalyst Research Librarian v5.6.0


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

- Open **Settings → Research Librarian Operations**.
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

Go to **Settings → Research Librarian Article Maps** and review the available path templates. Use the article path embed inside article maps, formula-heavy pages, and long research pages where a reader needs a next step into Workbench, Decision Studio, a module artifact, or the Knowledge Library.

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

Go to **Settings → Research Librarian Live UX** and click **Run Live UX QA**. Then test the public prompt library against the live page.

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
