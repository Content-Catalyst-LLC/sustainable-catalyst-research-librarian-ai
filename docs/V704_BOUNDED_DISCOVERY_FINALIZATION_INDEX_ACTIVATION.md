# Research Librarian AI v7.0.4

## Bounded Discovery Finalization and Index Activation

v7.0.4 repairs the production transition that could leave a rebuild at **Discovering Legacy** with zero synchronized records.

- Current WordPress sources are authoritative; legacy fallback records are skipped by default.
- Discovery commits its state before finalization begins.
- The staging JSONL file is validated in bounded, cursor-based passes.
- Record hashes and post mappings are accumulated incrementally and reused for the committed ledger.
- No full staging-file scan occurs at the discovery-to-sync transition or ledger save.
- The administration panel reports validated records and bytes processed.
- The previous durable index remains active until the final Python transaction commits.
