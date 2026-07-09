# Research Librarian v4.0.0 — Enterprise Readiness and Release Audit

v4.0.0 consolidates the Research Librarian into an enterprise-readiness release. Earlier versions added product routing, grounded source recommendations, knowledge indexing, Gemini embeddings, embedding diagnostics, evaluation, handoffs, saved sessions, feedback triage, governance, and scheduled maintenance.

This build adds an aggregate readiness layer and release audit so the plugin can be reviewed as infrastructure rather than as a simple chatbot embed.

## New capabilities

- Enterprise readiness score
- Public-safe readiness summary
- Admin-only readiness export
- Release audit snapshot
- REST endpoint inventory
- Shortcode mode inventory
- Manifest inventory
- Aggregated warnings across index, retrieval, evaluation, handoffs, sessions, feedback, governance, and maintenance

## New endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/enterprise/status`
- `GET /wp-json/sc-research-librarian-ai/v1/enterprise/export`
- `GET /wp-json/sc-research-librarian-ai/v1/release/audit`
- `GET /wp-json/sc-research-librarian-ai/v1/release/export`

## New shortcodes

```text
[sc_research_librarian mode="enterprise-summary" title="Research Librarian Enterprise Readiness"]
[sc_research_librarian mode="release-audit" title="Research Librarian Release Audit"]
```

## Deployment review

After installing v4.0.0:

1. Rebuild the knowledge index.
2. Generate Gemini embeddings if semantic retrieval is enabled.
3. Run retrieval evaluation.
4. Run index maintenance.
5. Check `/enterprise/status`.
6. Export `/release/export` as an admin-only deployment record.

The public summaries do not expose API keys. Admin exports should still be reviewed before publication because they can include operational metadata.
