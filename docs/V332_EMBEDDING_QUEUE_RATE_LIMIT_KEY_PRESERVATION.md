# Research Librarian v3.3.2 — Embedding Queue, Rate Limit Handling, and Key Preservation

This release hardens the Gemini embedding workflow after a successful single embedding test could be followed by failed full embedding runs.

## Added

- Resumable embedding generation: existing embeddings are preserved and skipped by default.
- Delay between Gemini embedding requests for free-tier stability.
- One retry after temporary Gemini rate-limit/server errors.
- Immediate stop on real key/authentication errors.
- Saved-key fingerprint in admin diagnostics so the site owner can see whether the stored key changed without exposing the key.
- Additional settings for delay and retry timing.

## Recommended setup

1. Test one embedding.
2. Set source limit to 5 or 10.
3. Generate embeddings.
4. Increase gradually to 25, 50, 100, then full coverage.
5. Keep resume mode enabled.
