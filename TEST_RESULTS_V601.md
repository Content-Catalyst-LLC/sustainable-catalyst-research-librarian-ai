# Research Librarian v6.0.1 validation

## Original v6.0.0 bootstrap probe

The original entry file was loaded in a minimal WordPress hook harness with no legacy class preloaded.

```json
{
  "class_exists": true,
  "init_hook_count": 0,
  "admin_menu_hook_count": 0,
  "admin_init_hook_count": 0,
  "rest_hook_count": 0,
  "shortcode_count": 0,
  "settings_filter_count": 0
}
```

This confirms that the class guard detected the class declared later in its own file and returned before bootstrap.

## Patched v6.0.1 regression test

The patched plugin was loaded with a simulated legacy `Sustainable_Catalyst_Research_Librarian_AI` class already present.

```json
{
  "v6_core_loaded": true,
  "legacy_class_detected": true,
  "missing_shortcodes": [],
  "settings_filter_registered": true,
  "settings_page_registered": true,
  "settings_option_registered": true,
  "settings_link_rendered": true,
  "admin_menu_registered": true,
  "admin_init_registered": true,
  "rest_registered": true
}
```

All PHP files passed `php -l`. All JSON files passed parsing validation. No private keys or common live-secret patterns were found.
