# v5.6.0 — Feature Suggestions Feedback Bridge

Research Librarian v5.6.0 connects public route feedback to Feature Suggestions v3 without making either plugin a hard dependency of the other.

## Public workflow

The existing helpful and issue controls now create an internal Research Librarian feedback record and a normalized contextual bridge record. Visitors can provide a 1–5 route rating or report a wrong route, missing source, missing topic, missing tool, unclear answer, or grounding concern.

## Bridge endpoints

- `POST /wp-json/sc-research-librarian/v1/feedback/bridge`
- `GET /wp-json/sc-research-librarian/v1/feedback/bridge/{receipt}`
- `GET /wp-json/sc-research-librarian/v1/feedback/bridge/status` — administrator only
- `GET /wp-json/sc-research-librarian/v1/feedback/bridge/export` — administrator only

## Integration

When Feature Suggestions is active, the bridge publishes the normalized payload through `scfs_research_librarian_feedback`. When it is unavailable, the submission remains in a bounded local queue. The bridge also publishes `librarian.feedback_submitted` and `librarian.feedback_bridge_created` through `sc_platform_event`.

## Privacy and governance

The bridge does not include raw conversation transcripts, names, email addresses, IP addresses, or API keys in shared events. All feedback and roadmap decisions remain subject to human review.
