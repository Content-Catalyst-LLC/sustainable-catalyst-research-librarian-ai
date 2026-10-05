# Research Librarian v12.2.0 — Multilingual & Cross-Language Research Intelligence

v12.2.0 establishes the Research Librarian multilingual research layer while preserving original-language evidence as the primary research representation.

## Architectural rule

**Analyze the original language first. Translation is a derived representation.**

The release preserves language, script, regional/variant, and historical-period identity; every translation, transliteration, normalization, and alignment remains separately attributable and traceable.

## New durable research objects

- language profiles;
- original-language source-text references;
- derived translation/transliteration/normalization representations;
- text-alignment records;
- cross-language query plans;
- cross-language retrieval receipts;
- immutable multilingual research snapshots.

## What v12.2 does not do

This release intentionally does not add:
- global source federation;
- automatic new-source ingestion;
- automatic translation or transliteration;
- automatic semantic-equivalence judgments;
- automatic cross-language entity resolution;
- automatic citation resolution;
- automatic evidence resolution;
- automatic truth promotion.

Those boundaries keep v12.2 distinct from:
- **v12.3.0** — Global Source Federation & Original-Language Research;
- **v12.4.0** — Cross-Language Entity, Citation & Evidence Resolution.

## Authority split

- Platform Core remains the governed language/provenance contract authority.
- Research Librarian owns research context, language identity, transformation lineage, alignment provenance, query plans, retrieval receipts, review state, and snapshots.
- Specialist runtimes may perform translation, transliteration, embeddings, alignment, or retrieval; the Librarian records their outputs and provenance.
- WordPress remains optional presentation/compatibility only.

## Persistence

Migration `042_multilingual_cross_language_research_intelligence.sql` creates:
- `sc_rl_multilingual_research_projects`
- `sc_rl_multilingual_research_events`
- `sc_rl_multilingual_research_snapshots`

## API

Prefix:

`/v1/research-librarian/multilingual-research`

Key routes:
- `GET /manifest`
- `GET /capabilities`
- `GET|POST /projects`
- `GET /projects/{id}`
- `POST /projects/{id}/language-profiles`
- `POST /projects/{id}/source-texts`
- `POST /projects/{id}/derived-representations`
- `POST /projects/{id}/alignments`
- `POST /projects/{id}/query-plans`
- `POST /projects/{id}/retrieval-receipts`
- `GET /projects/{id}/lineage`
- `GET /projects/{id}/readiness`
- `GET /projects/{id}/core-candidate`
- `POST /projects/{id}/state`
- `POST /snapshots/freeze`

## Next boundary

v12.3.0 — Global Source Federation & Original-Language Research.
