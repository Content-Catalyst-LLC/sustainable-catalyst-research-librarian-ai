# Research Librarian v12.0.2 — Independent Research Librarian API v1

v12.0.2 converts the v12.0.1 runtime-authority boundary into a stable backend-facing API for non-WordPress clients.

The versioned base path is `/v1/research-librarian`. Additive compatible routes may be added within API v1; breaking contract changes require a new API version.

The v1 surface includes manifest/capabilities/status, calibrated retrieval, project list/create/read, project investigation reads, scientist-environment and dossier reads, runtime-authority access, and immutable API-contract snapshots.

All responses use `sc-research-librarian-independent-api-envelope/1.0`.

Authentication deliberately reuses `X-SC-RL-Key` for this foundation. It is a server/client trust boundary, not end-user identity. Persistent conversations are planned for v12.0.3 and identity/session/access for v12.0.5.

WordPress is not required for the new API. The plugin exposes only compatibility metadata pointing to the backend API.

Migration 037 adds immutable API contract snapshots so clients and deployment tooling can record the exact API manifest they were built against.
