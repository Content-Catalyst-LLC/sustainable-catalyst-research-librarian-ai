# Research Librarian v12.3.0 — Global Source Federation & Original-Language Research

v12.3.0 turns the multilingual foundation from v12.2.0 into a governed global-source research layer. It adds research-scoped federated source registries, original-language acquisition lineage, source-ingestion and retrieval receipts, and explicit separation of descriptive source-quality signals from user trust preferences.

## Authority boundaries

- Original language remains primary; translation/transliteration/normalization remain derived.
- Knowledge Library/connectors remain ingestion authorities. Research Librarian records research context and receipts rather than becoming an unrestricted crawler.
- Platform Core remains contract/provenance authority.
- Source quality is not user trust.
- Retrieval is not truth.
- WordPress remains optional.
- Automatic entity/toponym/citation/evidence resolution remains deferred.

## New objects

Federated source, original-language acquisition, source-ingestion receipt, source-trust preference, federation query plan, federation retrieval receipt, multilingual/Core candidates, and immutable federation snapshots.

## API

Base path: `/v1/research-librarian/global-source-federation`

## Persistence

Migration `043_global_source_federation_original_language_research.sql` adds durable PostgreSQL project, event, and snapshot tables. SQLite remains available for isolated tests/local state.

## Next boundary

**v12.4.0 — Cross-Language Entity & Toponym Resolution**
