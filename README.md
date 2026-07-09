# Sustainable Catalyst Research Librarian

Sustainable Catalyst Research Librarian is the routing layer for the Sustainable Catalyst platform. It helps visitors choose the right library, module, demo, repository, Workbench tool, or Decision Studio workflow.

Version 3.0.0 upgrades the plugin from a simple AI Q&A box into product-level routing infrastructure aligned with Workbench and Decision Studio.

## What it does

- Routes questions to the Knowledge Library, Platform, Demos, Workbench, Decision Studio, and Catalyst modules
- Explains why a route fits and how it connects to the broader platform
- Supports deterministic fallback routing when no AI provider is configured
- Supports optional Gemini or OpenAI server-side AI responses
- Preserves strict professional boundaries and avoids confidential-data collection
- Generates exportable route notes as Markdown/JSON from the browser
- Provides shortcode modes for full assistant, compact assistant, landing card, and route map

## Shortcodes

```text
[sustainable_catalyst_research_librarian_ai]
[sc_research_librarian]
[sc_research_librarian mode="compact"]
[sc_research_librarian mode="landing" title="Sustainable Catalyst Research Librarian"]
[sc_research_librarian mode="route-map" title="Research Librarian Route Map"]
```

## REST routes

```text
GET  /wp-json/sc-research-librarian-ai/v1/health
GET  /wp-json/sc-research-librarian-ai/v1/routes
POST /wp-json/sc-research-librarian-ai/v1/ask
POST /wp-json/sc-research-librarian-ai/v1/route-note
```

## Scope

The Research Librarian is not a general chatbot. It is site-scoped routing infrastructure for Sustainable Catalyst.

It does not provide legal, financial, medical, tax, engineering, compliance, assurance, ESG/SDG certification, or regulated-information advice.

## Repository

https://github.com/Content-Catalyst-LLC/sustainable-catalyst-research-librarian-ai
