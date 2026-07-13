# Research Librarian AI v6.4.0 Validation Report

## Release

- **Version:** 6.4.0
- **Name:** Hybrid Retrieval and Citation Engine
- **Backend storage schema:** SQLite schema 5
- **Knowledge index schema:** `sc-research-librarian-knowledge-index/5.0`
- **Runtime target:** Python 3.12.12
- **Canonical source:** WordPress
- **Semantic storage:** recoverable SQLite chunk embeddings; no paid vector database required

## Hybrid retrieval contract

The dedicated v6.4.0 release contract passed **62/62 checks** covering:

- exact-title priority;
- deterministic section and page chunks;
- bounded WordPress section extraction;
- BM25 lexical retrieval;
- semantic cosine similarity;
- reciprocal-rank fusion;
- intent classification;
- persistent embedding queues and run history;
- semantic-coverage reporting;
- evidence identifiers and citation labels;
- section, page, passage, and retrieval-reason payloads;
- citation-label verification;
- invented-link rejection;
- deterministic evidence fallback;
- embedding status and processing endpoints;
- retrieval explanation endpoint;
- WordPress evidence normalization and public rendering;
- free-tier compatibility.

## Inherited release contracts

- **51/51** cold-start and recovery-hardening checks passed.
- **38/38** endpoint, durable-index, terminal-prompt, and snapshot checks passed.
- Bootstrap registration and legacy-class collision handling passed.
- Gemini authorization-key compatibility passed.
- Knowledge-intelligence and production-answer contracts passed.
- Live provider and country-routing contracts passed.
- Private compressed WordPress snapshot round trip passed.
- Retry exhaustion and duplicate transient-alert suppression passed.

## Backend tests

- **30/30** tests passed from the repository root.
- **30/30** tests passed from `backend/` to verify Render-style imports.
- Exact-title priority survived lexical and semantic fusion.
- BM25 selected the matching article section.
- Page-aware document chunks retained page metadata.
- Semantic similarity participated only when vectors existed.
- Unknown evidence labels and unknown absolute or relative URLs were rejected.
- Embedding batches remained resumable.
- Unchanged chunks retained compatible embeddings after index rebuild.
- Changed chunks invalidated stale embeddings.
- Transactional synchronization, rejection isolation, rollback, snapshot integrity, and legacy JSON migration remained green.

## Syntax and static validation

- **20** PHP files passed `php -l`.
- **2** JavaScript files passed `node --check`.
- **48** JSON files parsed successfully.
- Python source and tests passed `compileall`.
- `PUSH_RESEARCH_LIBRARIAN_V640_PY312.sh` passed Bash syntax validation.
- Push-safe secret-pattern scan returned no matches.

## Runtime note

The build container executed the backend suite with Python 3.13.5. The production runtime, Render blueprint, `runtime.txt`, and push script remain pinned to Python 3.12.12. The push script explicitly creates and verifies a clean Python 3.12 environment before installing dependencies or pushing the release.

## Packaged-artifact validation

The final ZIP was extracted into a clean directory and independently revalidated for:

- release markers and schema markers;
- PHP syntax;
- JavaScript syntax;
- JSON parsing;
- all nine WordPress release suites;
- all 30 backend tests from both import layouts;
- Python compilation;
- push-script Bash syntax;
- secret-pattern scanning;
- SHA-256 integrity.

## Result

**PASS — Research Librarian AI v6.4.0 is ready for repository push, Render deployment, WordPress installation, full synchronization, and bounded embedding generation.**
