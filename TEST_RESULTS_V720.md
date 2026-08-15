# Research Librarian AI v7.2.0 Validation Report

**Release:** Library Object Model & Research Context Alignment  
**Source baseline:** v7.1.2 repository package  
**Runtime target:** WordPress + FastAPI, Python 3.12/3.13, Neon Postgres production knowledge index

## Version boundary

The supplied repository was already v7.1.2. Its v7.1.0–v7.1.2 history is the established Neon/Postgres durability line, so the requested Library Object Model & Research Context Alignment work ships as **v7.2.0** rather than reusing v7.1.0.

## Implemented scope

- Added `sc-research-library-object-model/1.0` and normalized Library objects for sources, publications, recommendations, saved searches, watchlists, research queue items, source bundles, Research Rooms, pathways, Workspace notebooks, and Workspace evidence references.
- Added explicit source-scope provenance and fail-private defaults; editorial scope must be explicit rather than inferred from an object type.
- Added `sc-research-context/1.0` with Sustainable Catalyst Collection, My Library, Current Project, and Current Research Room scopes.
- Added one-active-context-per-owner persistence with consistent JSON state and fingerprints.
- Added authenticated WordPress owner resolution before private context is forwarded to FastAPI.
- Added a compact public-assistant Research context control and synchronized context selection with the Connected Research Workspace.
- Added context-aware retrieval priority for already-retrieved verified index records referenced by the selected context.
- Added an explicit generation safety boundary: Library/project/room metadata is untrusted scoping metadata, not instructions, verified evidence, or editorial endorsement.
- Added Library-object project links and portable project backup/import support.
- Advanced the ancillary SQLite schema to 13, the connected API to 1.1, and the public workspace contract to 2.1.
- Preserved the complete v7.1.2 Neon timeout-safe activation and fail-closed database behavior.

## Automated validation

- Backend pytest suite: **103 passed**.
- WordPress/PHP contract and functional suites: **33 test files passed**.
- Dedicated v7.2.0 WordPress release contract: **45 checks passed**.
- PHP syntax validation: **47 files passed**.
- JavaScript syntax validation: **3 files passed**.
- JSON parsing validation: **95 files passed**.
- Python compilation: passed.
- v7.2.0 GitHub push-script shell syntax: passed.
- Production-source secret scan: **0 hits**.

## Dedicated backend coverage

The v7.2.0 backend tests verify:

- Required Library object types and context boundaries.
- Provenance-preserving Library object persistence.
- Project linking without reclassifying the original source scope.
- Mixed personal/project/Research Room context resolution.
- One active context per owner with stale-state repair.
- A 50-object bounded ask context.
- Context metadata in ask workspace/provenance/diagnostics.
- Context-aware retrieval-priority activation.
- Linked Library objects in project backup and dry-run import counts.

## Storage and migration

- Production knowledge generations, records, chunks, and vectors remain in Neon Postgres with pgvector.
- Library object/context state is additive ancillary state in SQLite schema 13.
- No Postgres migration is required for v7.2.0.
- Existing schema-12 ancillary stores migrate by table creation; no destructive migration is used.

## Production boundary

The build environment does not contain the user's live WordPress account data, private Knowledge Library records, Neon credentials, or deployed Render service. Automated validation therefore covers contracts, persistence behavior, authorization boundaries at the WordPress bridge, retrieval behavior, packaging, and regression safety. After deployment, production verification should create one private Library context, select it in the Connected Research Workspace, ask a question through the public Librarian while signed in, and confirm the returned workspace/provenance reports the selected context without exposing it to a logged-out session.

## Package validation

- Full repository ZIP: integrity passed; clean extraction reran **103 backend tests** and all **33 WordPress/PHP test files** successfully.
- WordPress-only ZIP: integrity passed; contains no FastAPI backend, pytest suite, Render configuration, or GitHub push scripts; **14 packaged PHP files** linted and **3 packaged JavaScript files** syntax-checked.
- Release bundle: integrity passed; embedded SHA-256 manifest verified the repository ZIP, WordPress ZIP, push script, and installation note.
