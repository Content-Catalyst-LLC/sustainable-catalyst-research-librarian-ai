# Research Librarian AI v7.2.0 — Library Object Model & Research Context Alignment

## Release purpose

v7.2.0 aligns Research Librarian AI with the expanded Sustainable Catalyst Knowledge Library without collapsing different trust, ownership, or provenance boundaries into a generic search-result model. The release is additive to the v7 connected-research platform and preserves the v7.1.2 Neon/Postgres durability line.

The uploaded source already identified itself as v7.1.2, and v7.1.0 through v7.1.2 are established production releases for Neon durability, fail-closed database identity, and timeout-safe chunk activation. Reusing v7.1.0 would create a release-history collision. This implementation therefore ships as the next compatible feature version, v7.2.0.

## Library-native object contract

The backend now publishes `sc-research-library-object-model/1.0` and stores normalized `sc-research-library-object/1.0` records. Supported object types are:

- source
- publication
- recommendation
- saved search
- watchlist
- research queue item
- source bundle
- research room
- knowledge pathway
- Workspace notebook reference
- Workspace evidence reference

Every object retains an explicit `source_scope`, ownership reference, visibility, status, relationships, and provenance. Project linking creates a `library-object-ref` entity rather than reclassifying or copying the source into a different trust category.

## Research-context contract

`sc-research-context/1.0` defines four explicit scopes:

1. Sustainable Catalyst Collection — public/editorial context.
2. My Library — authenticated private/personal context.
3. Current Project — project-linked working context.
4. Current Research Room — collaborative context.

A saved context can combine these scopes while preserving their labels and source identities. The resolver emits `sc-research-context-resolution/1.0` plus a bounded prompt context. Only 50 context objects can enter a single ask request.

## Public ask integration

The WordPress assistant now has a compact Research context control. Authenticated users can select a saved context from the Connected Research Workspace; the selection is shared through a versioned local-storage key and a same-page custom event. Logged-out users remain on Sustainable Catalyst Collection context.

When a context contains source-record IDs that are also present in the verified knowledge index, the backend expands the initial candidate set and prioritizes those already-retrieved records before applying the normal source limit. Context metadata does not create evidence. External or private objects without verified indexed content remain scoping/navigation metadata only.

## Safety and provenance boundary

Research-context metadata is explicitly treated as untrusted metadata by the generation prompt. Library titles, URLs, labels, project metadata, and Research Room metadata cannot override the visitor question, verified evidence block, citation contract, or governance rules.

Personal saves and recommendations are not Sustainable Catalyst editorial endorsements. Research Room membership is not editorial approval. Publication remains human-controlled.

## Storage and migration

SQLite advances additively from schema 12 to schema 13 for ancillary connected-research state. Two tables are added:

- `research_library_objects`
- `research_contexts`

The production knowledge index remains Neon Postgres with pgvector. No Postgres migration is required for this release because Library object/context state remains in the existing ancillary store boundary.

Activating a new context deactivates the previous context for the same owner and updates both the indexed active flag and stored JSON/fingerprint, preventing stale `active=true` payloads.

## Portable recovery

Project backup bundles now include linked Library objects. Dry-run import reports a Library-object count, and a real import restores those objects before project entity references. Existing project, investigation, handoff, artifact, and checksum behavior remains unchanged.

## API additions

Authenticated backend integration routes:

- `GET /v1/library/object-model`
- `GET|POST /v1/library/objects`
- `GET /v1/library/objects/{object_id}`
- `POST /v1/library/objects/{object_id}/projects/{project_id}`
- `GET /v1/projects/{project_id}/library-objects`
- `GET|POST /v1/research/contexts`
- `GET /v1/research/contexts/{context_id}`
- `GET /v1/research/contexts/{context_id}/resolve`

The connected platform API advances to `sc-connected-research-api/1.1`; the public workspace contract advances to `sc-research-librarian-public-workspace/2.1`.

## WordPress bridge

The WordPress bridge enforces authenticated ownership before exposing private Library objects or research contexts to the browser. The ask endpoint accepts only a context ID from the browser, resolves that context server-side for the current WordPress user, bounds the resolved prompt context, and then forwards it to FastAPI.

This avoids trusting a browser-supplied personal corpus as an authorization mechanism.

## Compatibility

- v7.1.2 Neon/Postgres timeout-safe activation remains intact.
- Existing public questions behave as before when no private context is selected.
- Existing v7 project entities remain valid and provide the compatibility bridge for `library-object-ref` links.
- Existing handoff, governance, retrieval, accessibility, and fallback behavior remains additive.
- The release does not require a second Library account; identity is represented by the existing WordPress owner reference at the bridge boundary.

## Validation target

Release validation covers Python tests, all standalone PHP contract/functional tests, PHP syntax, JavaScript syntax, JSON parsing, Python compilation, package structure, and secret scanning. See `TEST_RESULTS_V720.md` for the final package result.
