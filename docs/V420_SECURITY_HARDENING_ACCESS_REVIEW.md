# Research Librarian v4.2.0 — Security Hardening, Endpoint Permissions, and Access Review

v4.2.0 adds a security review layer for the Research Librarian infrastructure.

## Purpose

The Research Librarian now has many public and admin surfaces: routing endpoints, retrieval diagnostics, index rebuilds, embeddings, exports, session logs, feedback logs, handoff logs, maintenance actions, and recovery snapshots. This build makes that surface reviewable.

## Added capabilities

- Security-readiness score
- Public-safe security summary
- Admin endpoint inventory
- Public/admin access classification
- Secret-safe key fingerprint diagnostics
- Warnings for missing credentials, empty index state, long retention windows, and disabled export redaction
- Admin-only security audit and export
- Security dashboard under WordPress settings

## Shortcodes

```text
[sc_research_librarian mode="security-summary" title="Research Librarian Security and Access Review"]
[sc_research_librarian_security_summary title="Research Librarian Security and Access Review"]
```

## Endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/security/status
GET  /wp-json/sc-research-librarian-ai/v1/security/endpoints
POST /wp-json/sc-research-librarian-ai/v1/security/run-audit
GET  /wp-json/sc-research-librarian-ai/v1/security/export
```

## Boundary

The public security summary does not expose raw keys, raw logs, raw route sessions, raw feedback records, or admin export payloads. Full endpoint inventory and security exports are restricted to users with `manage_options`.
