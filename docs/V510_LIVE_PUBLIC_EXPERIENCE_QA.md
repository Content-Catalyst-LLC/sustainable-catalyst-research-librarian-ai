# Research Librarian v5.1.0 — Live Public Experience QA, Prompt Library, and UX Calibration

Version 5.1.0 is the first post-stable-release refinement build. It focuses on the public visitor experience after the v5.0.0 acceptance gate.

## What this adds

- Live public experience QA status
- Visitor prompt library
- Live QA checklist
- Admin Live UX dashboard
- Public-safe live UX summary
- Public prompt-library shortcode
- Admin-only live UX export
- Route-answer test prompts for Workbench, Decision Studio, Catalyst modules, boundary behavior, and source-card behavior

## New REST endpoints

- `GET /wp-json/sc-research-librarian-ai/v1/live-ux/status`
- `GET /wp-json/sc-research-librarian-ai/v1/live-ux/prompts`
- `GET /wp-json/sc-research-librarian-ai/v1/live-ux/checklist`
- `POST /wp-json/sc-research-librarian-ai/v1/live-ux/run-qa`
- `GET /wp-json/sc-research-librarian-ai/v1/live-ux/export`

## New shortcodes

```text
[sc_research_librarian mode="live-ux" title="Research Librarian Live Public Experience"]
[sc_research_librarian mode="prompt-library" title="Research Librarian Prompt Library"]
[sc_research_librarian_live_ux_summary title="Research Librarian Live Public Experience"]
[sc_research_librarian_prompt_library title="Research Librarian Public Prompt Library"]
[sc_research_librarian_live_qa_checklist title="Research Librarian Live QA Checklist"]
```

## Recommended admin workflow

1. Install v5.1.0.
2. Rebuild the knowledge index.
3. Confirm Gemini embeddings still exist or regenerate them if needed.
4. Run Live UX QA.
5. Run every prompt in the Prompt Library on the public page.
6. Add weak routes to Query Review.
7. Regenerate Documentation Snapshot.

## Public placement

The main public page should still use:

```text
[sc_research_librarian title="Sustainable Catalyst Research Librarian"]
```

The new v5.1.0 prompt library and QA shortcodes are optional and are better suited to a documentation/admin-facing support page unless you want public visitors to see test prompts.
