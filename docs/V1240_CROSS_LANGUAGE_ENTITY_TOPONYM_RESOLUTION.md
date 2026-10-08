# Research Librarian v12.4.0 — Cross-Language Entity & Toponym Resolution

v12.4.0 adds a durable, backend-authoritative resolution layer for multilingual entity mentions and geographic names.

## Architectural boundary

Research Librarian may record mentions, candidate identities/places, aliases, transliterations, translations, evidence references, descriptive scores, review decisions, and immutable snapshots. It does **not** silently create canonical identity truth.

Accepted resolutions require explicit human review. Even an accepted resolution is a governed research decision, not an automatic Platform Core canonical write. Promotion to a canonical Core identity remains a separate explicit action with provenance.

## Entity resolution

The v12.4 object model preserves:

- original mention surface form and original script;
- source and acquisition references;
- language profile and local context;
- candidate entity references and native labels;
- alias/transliteration/translation evidence;
- candidate-generation basis and diagnostics;
- descriptive confidence separate from truth;
- accepted/rejected/deferred/needs-review decisions;
- human reviewer identity and rationale.

## Toponym resolution

Toponym candidates preserve jurisdiction, historical jurisdiction, temporal scope, optional candidate coordinates, native labels, source evidence, and competing candidate records. Politically contested, historical, colonial, exonym/endonym, and renamed-place cases are not silently normalized.

No automatic remote geocoding is introduced in this release.

## Governance

- Original language/script remains primary evidence.
- Translation and transliteration remain derived representations.
- Candidate generation is separate from confirmation.
- Scores are descriptive signals, not truth probabilities.
- Accepted decisions require human review.
- Competing candidates remain preserved.
- Canonical identity promotion is never automatic.
- WordPress remains an optional passive adapter.

## Persistence

Migration `044_cross_language_entity_toponym_resolution.sql` creates PostgreSQL project, event, and immutable snapshot stores. SQLite remains available for test/local isolation.

## API

Prefix:

`/v1/research-librarian/cross-language-entity-toponym-resolution`

The API supports project creation, entity/toponym mentions, candidates, resolution decisions, alias alignments, lineage, readiness, Core-candidate export, state changes, and immutable snapshots.

## Next boundary

v12.5.0 — Cross-Language Citation & Evidence Resolution.
