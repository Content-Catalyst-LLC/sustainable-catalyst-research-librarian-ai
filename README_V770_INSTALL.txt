Research Librarian AI v7.7.0 — Global Library Discovery & Federated Research

DEPLOYMENT ORDER
1. Push/deploy the v7.7.0 repository/backend first.
2. Confirm Render reports Research Librarian AI 7.7.0 and backend health is green.
3. Install/update WordPress with sustainable-catalyst-research-librarian-ai-wordpress-v7.7.0.zip.
4. Sign in and open the Connected Research Workspace.

PRODUCTION SMOKE TEST
1. Confirm Connected Research API reports sc-connected-research-api/1.6 and workspace 2.6.
2. Click “Discover globally.”
3. Run a harmless test query with at least two providers selected.
4. Confirm every result shows provider provenance and access state where available.
5. Confirm equivalent DOI/ISBN/arXiv records deduplicate while retaining all contributing provider badges.
6. Confirm a provider failure produces a visible partial-search state rather than hiding the failure or discarding successful results.
7. Open Recent searches and confirm the federated query can be reopened.
8. Before saving, confirm the discovered record is not present in My Library merely because it appeared in search.
9. Click “Save to My Library” on one result.
10. Confirm the saved object is private, source_scope=external-reference, and retains providers, provider record IDs, identifiers, access state, and federated fingerprint provenance.
11. If a project/context is active, confirm the saved object links to that project and the project backup contains federated_searches.
12. Confirm no external discovery result is labeled as Sustainable Catalyst editorial approval or verified evidence.

PRIVACY / GOVERNANCE
Search terms are transmitted to whichever external providers the researcher selects because those providers execute the query. The WordPress user identity is not forwarded to providers. Provider credentials remain backend-only. The browser cannot submit an arbitrary result payload for import: the backend imports only an exact result from an owner-authorized stored search snapshot.

DATABASE
Ancillary SQLite advances to schema 17 for federated search history. The Neon/Postgres knowledge index remains sc-research-librarian-knowledge-index/13.0. No Neon/Postgres knowledge-index migration is required.
