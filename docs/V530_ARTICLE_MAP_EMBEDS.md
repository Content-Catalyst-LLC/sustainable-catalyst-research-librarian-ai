# Research Librarian v5.3.0 — On-Page Research Path Embeds and Article Map Integration

This build adds an article-map integration layer for Sustainable Catalyst long-form pages. The goal is to let articles and article maps display compact Research Librarian route guidance without turning every page into a full assistant interface.

## Adds

- Public-safe article path embeds
- Article map route card summaries
- Context-aware article-to-route path templates
- Workbench path targets for formula/model/calculation questions
- Decision Studio path targets for decision brief and tradeoff questions
- Module artifact path targets for Canvas, Data, Impact, Risk, Finance, and Grit workflows
- Admin Article Maps dashboard
- Article-map catalog/export endpoints

## Shortcodes

```text
[sc_research_librarian mode="article-paths" title="Research Path"]
[sc_research_librarian_article_path_embed title="Research Path" context="calculus systems modeling" question="I need to graph and analyze this formula"]
[sc_research_librarian_article_map_summary title="Research Librarian Article Map Integration"]
[sc_research_librarian_article_route_cards title="Related Research Routes"]
```

## Endpoints

```text
GET  /wp-json/sc-research-librarian-ai/v1/article-map/status
GET  /wp-json/sc-research-librarian-ai/v1/article-map/catalog
POST /wp-json/sc-research-librarian-ai/v1/article-map/build
GET  /wp-json/sc-research-librarian-ai/v1/article-map/export
```

## Use

Place the article path embed near formulas, article map sections, demo references, or decision-support sections. Keep the full Research Librarian assistant on the platform page; use this layer as an on-page route hint.
