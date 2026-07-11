# Install Research Librarian AI v6.1.0

## WordPress installation

1. Open **Plugins → Add New Plugin → Upload Plugin**.
2. Upload `sustainable-catalyst-research-librarian-ai-v6.1.0-wordpress-plugin.zip`.
3. Choose **Replace current with uploaded** when upgrading an existing copy.
4. Activate **Sustainable Catalyst Research Librarian AI**.
5. Confirm the dedicated **Research Librarian AI** top-level WordPress menu appears.

## Configure live AI

1. Open **Research Librarian AI → AI Provider**.
2. Select Gemini or OpenAI.
3. Enter a provider model and paste the server-side API key.
4. Save the provider settings.
5. For Gemini, use **List Available Gemini Models** after the key is saved.
6. Run **Test AI Connection**.
7. Treat the provider as online only after the test succeeds.

Exact provider errors, HTTP status, transport errors, latency, and last-success records are administrator-only. The public assistant receives only a safe availability state.

## Public shortcode

```text
[sustainable_catalyst_research_librarian_ai]
```

Supported alias:

```text
[sc_research_librarian title="Sustainable Catalyst Research Librarian AI"]
```

## Acceptance questions

```text
What Sustainable Catalyst resources should I use to research climate and infrastructure in Pakistan?
```

Expected deterministic route: `country-intelligence`, country `PAK`.

```text
Where can I find live climate dashboards, Earth observation, and public environmental indicators?
```

Expected deterministic route: `site-intelligence`.

## Cache and index review

After upgrading:

- review **Research Librarian AI → Index & Settings**;
- rebuild the knowledge index when appropriate;
- clear WordPress optimization caches;
- clear Cloudflare cache;
- reload the public Research Librarian page.

A valid provider key is not included in the release package. The final live connection test must be completed in the WordPress environment.
