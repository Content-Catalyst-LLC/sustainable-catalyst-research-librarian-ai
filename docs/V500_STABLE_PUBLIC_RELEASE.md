# Research Librarian v5.0.0 — Stable Public Release, Launch Checklist, and Acceptance Gate

Version 5.0.0 is the stable public release layer for the Sustainable Catalyst Research Librarian. It does not replace the retrieval, routing, documentation, handoff, governance, or security layers. It aggregates them into a visible readiness gate so the tool can be treated as a public platform product rather than a sequence of experimental builds.

## What it adds

- Stable public release readiness score
- Public-safe release status endpoint
- Public-safe launch checklist endpoint
- Admin-only acceptance gate runner
- Admin-only release JSON export
- Public stable-release summary shortcode
- Public launch-checklist shortcode
- Endpoint and shortcode inventory
- Release notes and launch checklist documentation

## New endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/stable-release/status
GET  /wp-json/sc-research-librarian-ai/v1/stable-release/checklist
POST /wp-json/sc-research-librarian-ai/v1/stable-release/run-acceptance
GET  /wp-json/sc-research-librarian-ai/v1/stable-release/export
```

## New shortcodes

```text
[sc_research_librarian_stable_release_summary title="Research Librarian Stable Release"]
[sc_research_librarian_launch_checklist title="Research Librarian Launch Checklist"]
```

## Launch checklist

Before treating the Research Librarian as a stable public product, run these checks:

1. Rebuild the knowledge index.
2. Generate Gemini embeddings if semantic retrieval is enabled.
3. Run retrieval evaluation and review weak matches.
4. Test public answer UX on desktop and mobile.
5. Test guided paths at quick, standard, and deep depth.
6. Download Workbench and Decision Studio handoff JSON.
7. Confirm governance, retention, and redaction settings.
8. Run Security Audit.
9. Run Observability Checks.
10. Create a Recovery Snapshot.
11. Generate Documentation Snapshot.
12. Run the v5.0.0 Acceptance Gate.

## Boundary

The stable release summary is public-safe. It does not expose API keys, raw logs, private route sessions, raw queries, sensitive settings, or regulated conclusions.
