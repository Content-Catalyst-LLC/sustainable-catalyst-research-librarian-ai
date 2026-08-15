# v7.7.0 — Global Library Discovery & Federated Research

Research Librarian AI v7.7.0 adds a governed external-discovery layer across fixed scholarly and library providers. The feature expands discovery without collapsing external records into Sustainable Catalyst's editorial collection or treating search results as verified evidence.

## Provider architecture

The server uses fixed adapters for **OpenAlex, Crossref, Europe PMC, Open Library, and arXiv**. Provider identifiers, provider record IDs, access metadata, and retrieval provenance remain attached to normalized results. Arbitrary remote provider URLs are not accepted from the browser.

Results are normalized into `sc-federated-research-result/1.0`. DOI, ISBN, and arXiv identifiers are used for cross-provider deduplication when available. Deduplication may merge equivalent records into one research result, but it preserves every contributing provider and provider-specific record reference.

Provider failures are explicit. A search can complete in a `partial` state when one provider is unavailable; successful provider results remain visible and the failed-provider state is retained with the saved search snapshot.

## Library boundary

Federated discovery is a lead-generation and catalog-retrieval layer. A discovered record is **not** a Sustainable Catalyst editorial recommendation, **not** automatically part of My Library, and **not** verified evidence.

The user must explicitly choose **Save to My Library**. The backend then re-loads the stored search snapshot, selects the exact stored result, and creates a private Library object with `source_scope = external-reference`. The saved object retains provider identity, identifiers, access information, origin metadata, and the federated search/result linkage.

The browser does not send an arbitrary source payload to the import endpoint. This prevents a client from substituting a different record while claiming it came from an audited federated search.

## Research continuity

Federated searches are stored in the ancillary research workspace ledger with owner, project, context, provider status, normalized results, and fingerprints. Searches appear in recent-history UI and are included in project backup/import.

Research-state activity records distinguish `federated-search` from `federated-result-saved`. Search history is workflow memory, not evidence.

## WordPress authorization

WordPress resolves the signed-in user's `owner_ref` server-side. Context and project ownership are checked before search. Saving a result rechecks ownership of the stored search and any supplied context/project before calling the backend import route.

Provider IDs are restricted to the fixed server-supported allowlist. The browser cannot choose an arbitrary remote host. Search terms are transmitted to the selected external providers because those providers execute the search; the signed-in WordPress owner identity is not forwarded to those providers. Server-held provider credentials remain backend-only.

## Persistence boundary

Ancillary SQLite advances from **schema 16 to schema 17** with `research_federated_searches`. This is research-workspace state, not knowledge-index content.

The production knowledge index remains `sc-research-librarian-knowledge-index/13.0`. **No Neon/Postgres knowledge-index migration is required for v7.7.0.**

## Contract versions

- Research Librarian AI: `7.7.0`
- Connected Research API: `sc-connected-research-api/1.6`
- Public workspace: `sc-research-librarian-public-workspace/2.6`
- Ancillary SQLite schema: `17`
- Knowledge index: `sc-research-librarian-knowledge-index/13.0`
- Provider catalog: `sc-federated-provider-catalog/1.0`
- Federated search: `sc-federated-research-search/1.0`
- Federated result: `sc-federated-research-result/1.0`
- Library import: `sc-federated-library-import/1.0`
