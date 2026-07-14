# Research Librarian AI v6.6.0 — Platform Intelligence and Typed Research Handoffs

## Purpose

v6.6.0 connects verified Research Librarian evidence to specialized Sustainable Catalyst products without reducing those connections to ordinary links or silently executing work. Every handoff is a reviewable, versioned payload with a destination-specific contract, source records, assumptions, uncertainty, a human-confirmation boundary, and a tamper-evident provenance fingerprint.

The release supports Workbench, Decision Studio, Site Intelligence, Sustainable Catalyst Lab, and Feature Suggestions. A destination appears publicly only when its capability is enabled and has a configured URL.

## Versioned contracts

The common transport layer uses:

- `sc-research-handoff/2.0` — complete handoff envelope;
- `sc-research-route/2.0` — destination, version, URL, mode, and routing reason;
- `sc-research-artifact-return/1.0` — completed artifact returned to Research Librarian;
- `sc-platform-capabilities/1.0` — discoverable destination catalog.

Destination payloads use:

- Workbench: `sc-workbench-task/1.0`;
- Decision Studio: `sc-decision-packet-seed/1.0`;
- Site Intelligence: `sc-site-intelligence-query/1.0`;
- Lab: `sc-lab-workflow/1.0`;
- Feature Suggestions: `sc-feature-suggestion/1.0`.

## Capability discovery

FastAPI and WordPress both maintain a capability registry. Each destination publishes:

- stable ID and human-readable label;
- enabled and available state;
- destination URL and declared version;
- common handoff contract;
- accepted context fields;
- expected artifact types.

WordPress merges its local configuration with the backend response. A disabled or unconfigured destination is removed from public action cards instead of producing a broken link.

## Typed payloads

### Workbench

A Workbench task can carry equations, variables, units, assumptions, datasets, requested outputs, validation requirements, and verified source passages. The default outputs include a calculation report, validation warnings, and a reproducible method.

### Decision Studio

A Decision Studio seed can carry the decision question, alternatives, criteria, scenarios, evidence ledger, assumptions, uncertainties, and prior Workbench result IDs. The default outputs include a decision packet, assumption register, uncertainty register, and audit appendix.

### Site Intelligence

A Site Intelligence query can carry places, countries, indicators, time range, event types, source requirements, requested outputs, and evidence context. Source requirements default to public, attributable records with visible freshness and methodology.

### Lab

A Lab workflow can carry a research question, domain, hypotheses, experiment type, datasets, instrumentation, calculations, requested outputs, and evidence context. It remains a research and engineering workflow seed rather than an autonomous experiment.

### Feature Suggestions

An unsupported or missing platform capability can become a typed suggestion record with workflow context and evidence rather than an invented destination action.

## Provenance and validation

Every prepared handoff includes:

- unique handoff ID and creation time;
- Research Librarian release version;
- active research mode and session ID;
- canonical record IDs, URLs, evidence labels, sections, pages, and passages;
- assumptions and uncertainties;
- a source-to-retrieval-to-handoff provenance chain;
- a SHA-256 payload fingerprint;
- explicit human-confirmation requirements.

The validation endpoint rejects unknown schemas, unknown or unavailable destinations, missing destination contracts, and payloads altered after fingerprint generation.

## Artifact returns

A connected product can return a calculation, brief, map, validation report, experiment record, or other declared artifact through `sc-research-artifact-return/1.0`. The return is checked against the stored original handoff. Its provenance is extended with the original handoff fingerprint and the `research_librarian_return` chain event.

SQLite schema version 7 adds ledgers for prepared handoffs and returned artifacts. This is an additive migration and preserves the existing knowledge index, chunks, embeddings, snapshots, benchmark history, calibration profile, synchronization ledger, and recovery data.

## Backend API

```text
GET  /v1/platform/capabilities
POST /v1/handoffs/prepare
POST /v1/handoffs/validate
GET  /v1/handoffs/logs
POST /v1/handoffs/artifacts/return
GET  /v1/handoffs/artifacts
```

All backend handoff endpoints require the integration key. Public browser requests go through the nonce-protected WordPress bridge.

## WordPress bridge

```text
GET  /wp-json/sc-research-librarian-ai/v1/platform/capabilities
POST /wp-json/sc-research-librarian-ai/v1/platform/handoff/prepare
POST /wp-json/sc-research-librarian-ai/v1/platform/handoff/validate
POST /wp-json/sc-research-librarian-ai/v1/platform/artifact/return
GET  /wp-json/sc-research-librarian-ai/v1/platform/handoffs/export
```

The release adds the shortcode:

```text
[sc_research_librarian_platform_handoffs]
```

The administrator screen under **Settings → Research Librarian Handoffs** controls destination availability, URL, declared version, and bounded log retention.

## Public workspace

The ask response advances to `sc-research-librarian-public-workspace/1.2` and adds:

- `capabilities`;
- `typed_handoffs`;
- `provenance`.

The workspace renders only available destinations. Users can inspect and download a preview, or explicitly prepare and validate a fresh typed payload. No destination task is executed automatically.

## Deployment

The backend defaults to the existing Sustainable Catalyst destination URLs. Render can override enabled state, URL, and version using:

```text
SC_RL_WORKBENCH_ENABLED
SC_RL_WORKBENCH_URL
SC_RL_WORKBENCH_VERSION
SC_RL_DECISION_STUDIO_ENABLED
SC_RL_DECISION_STUDIO_URL
SC_RL_DECISION_STUDIO_VERSION
SC_RL_SITE_INTELLIGENCE_ENABLED
SC_RL_SITE_INTELLIGENCE_URL
SC_RL_SITE_INTELLIGENCE_VERSION
SC_RL_LAB_ENABLED
SC_RL_LAB_URL
SC_RL_LAB_VERSION
SC_RL_FEATURE_SUGGESTIONS_ENABLED
SC_RL_FEATURE_SUGGESTIONS_URL
SC_RL_FEATURE_SUGGESTIONS_VERSION
SC_RL_HANDOFF_SOURCE_LIMIT
```

Unknown destination versions remain visible as `unknown` but should be replaced with deployed product versions before cross-product production acceptance testing.

## Compatibility boundary

v6.6.0 preserves the v6.5.1 accessibility and performance behavior, the black-and-green prompt, light answer and source surfaces, calibrated hybrid retrieval, citation verification, deterministic fallback, transactional indexing, recovery snapshots, cold-start recovery, and free-tier architecture. It does not require a paid vector database or persistent Render disk.
