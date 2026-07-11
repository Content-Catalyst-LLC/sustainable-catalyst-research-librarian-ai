# Sustainable Catalyst Platform Core / Research Librarian inspection

## Result

No Platform Core patch is required.

The supplied Platform Core archive contains a WordPress connector at version 2.6.0 and a FastAPI backend. The WordPress plugin:

- does not define `Sustainable_Catalyst_Research_Librarian_AI`;
- does not include or require the Research Librarian plugin entry file;
- does not register or remove `sustainable_catalyst_research_librarian_ai`, `sc_research_librarian`, `sc_research_guidance_platform`, or `sc_research_guidance_journey`;
- does not filter or rewrite the WordPress active-plugin list;
- does not remove Research Librarian admin menus or plugin action links.

Its Research Librarian references are platform registry identifiers and workflow relationships, such as `research-librarian` and `sc:product:research-librarian`. These references do not load or suppress the WordPress Research Librarian plugin.

## Confirmed Research Librarian defect

The v6.0.0 Research Librarian entry file contained this pattern before its main class declaration:

```php
if ( class_exists( 'Sustainable_Catalyst_Research_Librarian_AI', false ) ) {
    return;
}

final class Sustainable_Catalyst_Research_Librarian_AI {
    // ...
}
```

PHP knows about a top-level class declared later in the same file while that file is executing. Therefore `class_exists()` returned `true` for the plugin's own class, and the plugin returned before completing bootstrap.

WordPress could still read the plugin header and display version 6.0.0 as active. However, the code never reached the class instance creation, Settings filter, admin pages, shortcode registration, REST routes, module initializers, or activation hooks.

This exactly explains the observed state:

- the Plugins screen displayed version 6.0.0 and “Deactivate”;
- no Settings link appeared;
- no Research Librarian Settings pages appeared;
- the shortcode printed literally on the public page.

## Repair applied in Research Librarian v6.0.1

- Removed the self-detecting early return.
- Added unique `SC_RL6_*` internal class names.
- Added unique `sc_rl6_*` bootstrap helper names.
- Preserved the historic main class name through a conditional compatibility alias.
- Raised main shortcode, REST, admin-menu, and settings registration priority to 99.
- Added a legacy-class source notice without aborting the current plugin.
- Tightened duplicate detection so the diagnostics plugin is not treated as a duplicate Research Librarian copy.
- Added a standalone regression test that simulates a preloaded legacy class and verifies all core registrations.

## Validation

- Platform Core WordPress PHP lint: passed.
- Research Librarian v6.0.1 PHP lint: passed for all PHP files.
- Bootstrap regression test: passed.
- Required shortcodes registered in the test harness:
  - `[sustainable_catalyst_research_librarian_ai]`
  - `[sc_research_librarian]`
  - `[sc_research_guidance_platform]`
  - `[sc_research_guidance_journey]`
- Settings action link: registered.
- Main Settings page: registered.
- Main settings option: registered.
- Admin, REST, and shortcode hooks: registered.
