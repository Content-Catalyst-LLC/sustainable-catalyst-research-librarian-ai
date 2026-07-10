# v5.8.0 — Adaptive Prompt and Survey Experiences

## Purpose

This release connects Research Librarian outcomes to optional, contextual feedback and survey experiences without interrupting normal research use.

## Trigger types

- low confidence
- zero sources
- source opened
- route abandoned
- path completed
- repeated tool demand
- Workbench handoff
- Decision Studio handoff
- always-on embedded experience

## Governance

Consent is required by default. Daily caps, cooldowns, and dismissal windows are enforced in browser storage. Server logs are bounded and contain route/topic references, ratings, event types, and response-presence flags rather than raw public-event text. Site Intelligence events exclude response text.

## Integration

Feature Suggestions receives structured handoffs through `scfs_research_librarian_survey_handoff`. Other consumers can filter `sc_rl_adaptive_survey_handoff`.

## Shortcode

`[sc_research_librarian_adaptive_experience trigger="path_completed"]`
