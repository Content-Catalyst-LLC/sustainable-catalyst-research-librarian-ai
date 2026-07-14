# Research Librarian AI v7.0.0 Validation Report

**Release:** Connected Research Intelligence Platform  
**Full package:** `sustainable-catalyst-research-librarian-ai-v7.0.0.zip`  
**WordPress package:** `sustainable-catalyst-research-librarian-ai-wordpress-v7.0.0.zip`

## Scope

v7.0.0 adds persistent private-by-default projects, multi-step investigations, project entities, reusable workflow templates, contradiction reports, uncertainty registers, artifact history, a stable API manifest, a provider-independent generation adapter, and checksum-verified portable project backups. Existing retrieval, citation, recovery, handoff, accessibility, and governance contracts remain active.

## Dedicated v7 verification

- Project create, list, owner-filter, bundle, and update paths
- Investigation persistence
- Evidence/project entity persistence
- Reusable workflow templates
- Contradiction detection
- Uncertainty prioritization
- Backup checksum verification and tamper rejection
- Stable API and platform-summary resources
- Provider-independent generation-adapter contract
- WordPress private-project defaults, nonce protection, owner authorization, and human-publication review

## Automated results

- **66/66** FastAPI/backend tests passed from the repository root
- **66/66** FastAPI/backend tests passed from `backend/`
- **20/20** WordPress/PHP release suites passed
- **672** named PHP contract checks passed, plus functional assertions
- **34** PHP files passed syntax validation in the full repository
- **3** JavaScript files passed Node syntax validation
- **59** JSON files passed parsing validation
- Python compile validation passed
- Push-script Bash syntax validation passed
- Secret-pattern scan passed

## Compatibility

- Plugin/backend version: **7.0.0**
- SQLite schema: **10**
- Knowledge index contract: `sc-research-librarian-knowledge-index/10.0`
- Public workspace contract: `sc-research-librarian-public-workspace/2.0`
- Stable platform API: `sc-connected-research-api/1.0`
- Generation boundary: `sc-generation-adapter/1.0`
- Existing schema-9 data migrates additively; no destructive migration is used
- Free-tier architecture remains supported

## Package validation

The full repository ZIP and WordPress-only ZIP were extracted into clean directories and independently retested. The WordPress package contains no FastAPI backend, pytest suite, Render configuration, or GitHub push script. Both package checksums were verified after creation.

## Python release workflow

The included GitHub push script explicitly selects and verifies Python **3.12**, clears macOS launcher and active-environment overrides, uses copied venv binaries, requires binary dependency wheels, and runs tests from both supported import layouts before pushing or tagging.
