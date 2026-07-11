# Research Librarian AI v6.1.0 Test Results

Release: **Live AI Restoration and Admin Consolidation**

## Validation summary

- PHP syntax: **passed** across 11 PHP files
- JavaScript syntax: **passed** for the public Research Librarian asset
- JSON validation: **passed** across 42 JSON manifests and registries
- Secret scan: **passed**; no Google, OpenAI, GitHub, or private-key credential patterns found
- Backup-artifact scan: **passed**; no `.bak` or `.DS_Store` files included
- Collision-safe bootstrap: **passed**
- Public shortcode registration: **passed**
- AI REST route registration: **passed**
- Dedicated top-level admin menu registration: **passed**
- General WordPress Settings cleanup: **passed**
- Provider submenu registration: **passed**
- Pakistan country routing: **passed**
- Site Intelligence climate-dashboard routing: **passed**
- Gemini request contract checks: **passed**
- Country registry validation: **passed** with 249 records
- Final ZIP structure and archive integrity: **passed during release packaging**

## Bootstrap regression result

```json
{
  "version": "6.1.0",
  "core_loaded": true,
  "legacy_class_detected": true,
  "missing_shortcodes": [],
  "missing_ai_rest_routes": [],
  "top_level_menu": true,
  "settings_menu_cleaned": true,
  "provider_submenu": true,
  "pakistan_route_id": "country-intelligence",
  "pakistan_alpha3": "PAK",
  "pakistan_url": "/platform/site-intelligence/country-intelligence/?country=PAK",
  "dashboard_route_id": "site-intelligence"
}
```

## Provider and public-status contract result

The static release contract completed **20 checks with 20 passed and 0 failed**. It verified:

- public AI status endpoint;
- administrator AI test and model-list endpoints;
- server-side Gemini header authentication;
- Gemini `systemInstruction` usage;
- no query-string API key on the generation endpoint;
- normalized Gemini model names;
- current first-party source records merged into existing indexes;
- Pakistan and Site Intelligence evaluation cases;
- top-level administration and legacy Settings cleanup;
- public status rendering and styling;
- the 249-country registry and Pakistan `PK`/`PAK` record.

## Live-provider boundary

No user API key was embedded in or supplied to the release build. Therefore, the release was not tested against the user's live Gemini or OpenAI account from the build environment. The final provider validation must be completed in WordPress through:

**Research Librarian AI → AI Provider → Test AI Connection**

The plugin reports **AI Online** only after a provider request succeeds. A saved key alone produces **AI Configured — Not Yet Tested**.
