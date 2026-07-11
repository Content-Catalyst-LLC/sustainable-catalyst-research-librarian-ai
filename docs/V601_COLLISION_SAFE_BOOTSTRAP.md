# v6.0.1 — WordPress Bootstrap Registration Repair

## Confirmed root cause

The failure is inside the Research Librarian v6.0.0 entry file, not Sustainable Catalyst Platform Core.

The v6.0.0 entry file checked `class_exists( 'Sustainable_Catalyst_Research_Librarian_AI', false )` immediately before the class declaration and returned when the result was true. In PHP, a top-level class declared later in the same file is already known when the file executes. The guard therefore detected the plugin's own class and returned on every request.

WordPress could still read the plugin header and show v6.0.0 as active, but the file returned before it reached:

- `Sustainable_Catalyst_Research_Librarian_AI::instance()`
- the Settings action-link filter
- the Settings and Research Guidance Platform admin pages
- shortcode registration
- REST registration
- the v4.x, v5.x, and v6.0 module initializers
- activation and deactivation hook registration

That exactly explains the observed state: the Plugins screen showed version 6.0.0 and Deactivate, but there was no Settings link and the public page printed the shortcode literally.

## Platform Core inspection

The supplied Sustainable Catalyst Platform Core archive was searched across its backend and WordPress plugin. It does not define or include the Research Librarian PHP class, does not register or remove the Research Librarian shortcodes, and does not manipulate the active-plugin list. No Core patch is required.

Core references Research Librarian only as a platform service/entity identifier in the API gateway, service registry, workflow catalog, SDK examples, tests, and a Platform Core relationship shortcode example.

## v6.0.1 repair

- Removed the self-detecting early-return guard.
- Gave v6 internal classes unique `SC_RL6_*` names so a legacy class cannot block the current plugin.
- Gave bootstrap helper functions unique `sc_rl6_*` names.
- Preserved the historic main class name through a compatibility alias only when it is unclaimed.
- Raised core shortcode, REST, settings, and admin registration priority to 99.
- Added an administrator notice that identifies a pre-existing legacy class file and version without aborting v6.
- Tightened duplicate-plugin detection so the separate diagnostics plugin is not misclassified as a Research Librarian installation.
- Added a standalone bootstrap regression test that simulates a legacy class and verifies settings, admin, REST, and all four public shortcodes still register.

## Expected WordPress behavior

After activation, the Plugins screen shows a Settings link. WordPress Settings includes the main Research Librarian page and the Research Guidance Platform page. These public shortcodes register:

- `[sustainable_catalyst_research_librarian_ai]`
- `[sc_research_librarian]`
- `[sc_research_guidance_platform]`
- `[sc_research_guidance_journey]`
