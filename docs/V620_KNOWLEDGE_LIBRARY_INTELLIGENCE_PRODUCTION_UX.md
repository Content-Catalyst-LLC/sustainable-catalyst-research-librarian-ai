# Research Librarian AI v6.2.0 — Knowledge Library Intelligence and Production UX

## Product correction

v6.2.0 moves the intelligence center out of the WordPress request process and into a dedicated Python service. The WordPress plugin is no longer expected to behave as the entire AI application. It publishes the interface, indexes public content, protects credentials, proxies questions, records feedback, and preserves deterministic continuity. Python performs retrieval and grounded generation.

## Retrieval hierarchy

1. Exact normalized title
2. Title phrase
3. Exact or partial slug
4. Title token coverage
5. Heading coverage
6. Series, article-map, and parent relationships
7. Taxonomy coverage
8. Summary and body-content coverage
9. Broad route context

## Public experience

The answer leads with useful prose, the best verified match, additional exact titles, a research path, related titles, and platform actions. Confidence and retrieval details remain available under **Why these results?** rather than dominating the interface.

## Render deployment

The FastAPI backend is designed for an independent Render web service. The Gemini key and shared integration key live in Render environment variables. WordPress sends content and questions server-to-server. The browser never receives either key.
