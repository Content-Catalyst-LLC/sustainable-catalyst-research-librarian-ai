# Research Librarian v3.3.3 — Gemini Key Persistence and Batch Credential Fix

This hotfix protects Gemini/OpenAI keys from accidental overwrites during settings changes and embedding batch runs.

## What changed

- API key fields now use separate replacement inputs instead of posting the stored option field directly.
- Blank password fields preserve the existing saved key.
- Placeholder, masked, browser-autofilled, or incomplete values are rejected and the existing key is preserved.
- A clear-key checkbox is required to intentionally remove a saved key.
- Admin diagnostics show the saved-key fingerprint and the last-run key fingerprint without exposing the key.
- Embedding status includes the key fingerprint used for the last test or batch run.
- Single embedding tests and batch generation now expose whether the key changed between runs.

## Recommended use

1. Paste the Gemini key only when replacing it.
2. Save settings.
3. Click **Test Single Gemini Embedding**.
4. If it passes, run **Generate Gemini Embeddings** with a small source limit.
5. Increase the source limit gradually.

If a browser password manager attempts to autofill the key field, v3.3.3 should preserve the existing key rather than saving the autofilled value.
