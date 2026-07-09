# Sustainable Catalyst Research Librarian AI

Current release: **v4.4.0 — Editorial Curation, Route Overrides, and Source Weighting**.

Research Librarian is the source-aware routing, indexing, retrieval, evaluation, handoff, governance, maintenance, recovery, security, observability, and editorial curation layer for Sustainable Catalyst. It helps visitors move from a question to the right Sustainable Catalyst page, module, Workbench tool, Decision Studio workflow, repository, methodology page, or feature suggestion route while keeping admin exports, logs, credentials, and operational diagnostics separated from public use.

## v4.4.0 focus

v4.4.0 adds editorial curation controls: route override rules, source weighting rules, boundary pattern rules, an admin curation dashboard, curation test/export endpoints, and public-safe curation summaries. These controls let Sustainable Catalyst deliberately prioritize canonical routes when retrieval scores alone are not enough.

## New v4.4.0 shortcodes

```text
[sc_research_librarian mode="curation-summary" title="Research Librarian Editorial Curation"]
[sc_research_librarian_curation_summary title="Research Librarian Editorial Curation"]
[sc_research_librarian_route_overrides_summary title="Research Librarian Route Overrides"]
```

## New v4.4.0 endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/curation/status
GET  /wp-json/sc-research-librarian-ai/v1/curation/rules
GET  /wp-json/sc-research-librarian-ai/v1/curation/export
POST /wp-json/sc-research-librarian-ai/v1/curation/test
POST /wp-json/sc-research-librarian-ai/v1/curation/reset-defaults
```

## Setup

1. Upload and activate `sustainable-catalyst-research-librarian-ai-plugin-v4.4.0.zip`.
2. Confirm your Gemini/API settings still work if retrieval is enabled.
3. Rebuild the knowledge index if routes or pages changed.
4. Go to **Settings → Research Librarian Curation**.
5. Review default override, source-weight, and boundary rules.
6. Test prompts such as “I need to graph a model,” “I need to compare options and export a brief,” and “Can you certify this as SDG aligned?”

## Public safety

Public curation status exposes counts and high-level posture only. Full rules and curation tests are admin-only.
