# Research Librarian AI v6.1.1 — Gemini Authorization Key Compatibility Patch

Google AI Studio now creates authorization keys by default. The v6.1.0 plausibility validator accepted legacy `AIza` keys but rejected modern key strings that contained periods. In that state, WordPress preserved the previously saved value, so the administrator could paste a valid new key without actually replacing the old credential.

v6.1.1:

- accepts modern URL-safe authorization key strings;
- keeps keys server-side and never renders them back into the page;
- identifies older standard keys and displays restriction/migration guidance;
- converts common Gemini HTTP failures into actionable administrator messages;
- preserves the public-safe fallback message and deterministic country-aware routing.

## Verification

1. Save a synthetic modern key containing periods and confirm the plausibility validator accepts it.
2. Confirm whitespace, masks, placeholders, and short values remain rejected.
3. Confirm PHP syntax, JSON, JavaScript, shortcode, provider-contract, and archive checks pass.
4. Confirm the plugin version and stable tag are 6.1.1.
