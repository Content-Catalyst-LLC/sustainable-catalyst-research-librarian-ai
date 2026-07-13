# Research Librarian AI v6.2.1 Test Results

**Release:** WordPress Indexing and Endpoint Reliability Patch  
**Validation date:** July 13, 2026

## Passed validation

- 15 PHP files passed `php -l`.
- 2 JavaScript files passed `node --check`.
- 45 JSON files parsed successfully.
- 5 WordPress/PHP release test suites passed.
- 83 named PHP contract checks passed, plus the collision-safe bootstrap and route-registration scenario.
- The v6.2.1 endpoint-reliability suite passed 37/37 checks.
- The FastAPI test suite passed 5/5 tests.
- Python application and test modules passed bytecode compilation.
- The release push script passed `bash -n` syntax validation.
- The push-safe scan found no private-key blocks or common GitHub, OpenAI, or Gemini secret patterns.

## Verified v6.2.1 contracts

- Canonical published WordPress records are collected before legacy route-index records.
- Duplicate URLs cannot cause summary-only records to replace full article records.
- Sync jobs preserve per-batch sent, accepted, rejected, state, and backend-total fields.
- WordPress REST, nonce, backend, integration-key, index, provider, WP-Cron, and rate-limit states have distinct diagnostics.
- Expired nonces receive one safe refresh and retry for questions and title suggestions.
- Public rate limits use rolling windows and expose `Retry-After` data.
- Authenticated editors are exempt from public limits by default.
- Administrators can inspect and reset active public rate-limit windows.
- The repair operation tests both public health and the authenticated knowledge-summary endpoint before resynchronizing.
- The public textarea has a black background, green monospace text, green caret, subdued green placeholder, and accessible green focus ring.
- Answer, endpoint-notice, evidence, and source-card surfaces remain light.
- FastAPI sync responses preserve job ID, batch position, and accepted/rejected counts.
- Existing v6.2.0 options, scheduled hook, and class references remain compatible.

## Tests executed

```text
php tests/bootstrap-registration-test.php
php tests/endpoint-reliability-contract-test.php
php tests/gemini-auth-key-compatibility-test.php
php tests/knowledge-intelligence-contract-test.php
php tests/live-ai-provider-contract-test.php
python3 -m pytest -q backend/tests
php -l <all PHP files>
node --check <all public JavaScript files>
python3 -m compileall backend/app backend/tests
bash -n PUSH_RESEARCH_LIBRARIAN_V621.sh
```

## Deployment boundary

These tests validate the packaged source, WordPress registration contracts, JavaScript behavior contracts, and local FastAPI application. They do not simulate the production WordPress host, Cloudflare rules, WP-Cron traffic, or the deployed Render service. After installation, use **Research Librarian AI → Python Intelligence → Repair Endpoint and Resynchronize** to verify the live server-to-server path and rebuild the production index.
