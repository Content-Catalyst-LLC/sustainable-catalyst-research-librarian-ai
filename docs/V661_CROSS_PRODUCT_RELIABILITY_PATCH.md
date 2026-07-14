# Research Librarian AI v6.6.1

## Cross-Product Reliability Patch

v6.6.1 hardens the typed platform handoffs introduced in v6.6.0. It keeps Research Librarian responsible for evidence selection and provenance while requiring each destination to declare a compatible version, validate a short-lived delivery token, acknowledge intake through a receipt, and return immutable artifacts through a bounded interface.

## Reliability controls

- Destination-specific minimum supported versions and compatibility states: `compatible`, `unverified`, `incompatible`, and `disabled`.
- Public actions exclude disabled or incompatible products. Unknown versions remain explicitly unverified and require destination-side contract validation.
- Short-lived HMAC delivery tokens can be refreshed without recreating the research context.
- Bounded retry attempts use exponential backoff metadata and stop at the configured ceiling.
- Idempotency keys prevent duplicated preparation, retry, receipt, and artifact-return events.
- Intake receipts bind destination, handoff ID, source fingerprint, delivery token, and status.
- Artifact returns are checked against the original destination, declared artifact types, payload-size limits, and provenance fingerprints.
- Artifact IDs and receipt IDs are immutable. Replaying an identical event is safe; changing the contents under an existing ID is rejected.
- SQLite schema version 8 stores compatibility, retry state, token expiry, receipts, idempotency events, and artifact fingerprints.

## New contracts

- `sc-platform-capabilities/1.1`
- `sc-platform-compatibility/1.0`
- `sc-research-handoff-delivery/1.0`
- `sc-research-handoff-receipt/1.0`

The common handoff, route, and artifact-return contracts remain backward compatible:

- `sc-research-handoff/2.0`
- `sc-research-route/2.0`
- `sc-research-artifact-return/1.0`

## New backend endpoints

```text
GET  /v1/platform/compatibility
POST /v1/handoffs/retry
POST /v1/handoffs/token/refresh
POST /v1/handoffs/receipts
```

The existing capability, prepare, validate, log, artifact-return, and artifact-list endpoints remain available and integration-key protected.

## WordPress bridge

The WordPress plugin adds nonce-protected routes for compatibility reporting, bounded retries, token refresh, receipts, and immutable artifact returns. The public workspace displays destination compatibility and token state and exposes explicit **Retry delivery** and **Refresh token** controls. It never performs destination work automatically.

## Upgrade compatibility

- No destructive migration is performed.
- SQLite advances additively from schema 7 to schema 8.
- Existing handoffs and artifacts remain readable.
- The black-and-green question field, light answer/evidence cards, calibrated retrieval, durable recovery, and accessibility behavior are preserved.
- No paid vector database, message broker, or persistent Render disk is required.
