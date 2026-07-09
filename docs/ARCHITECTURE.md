# Architecture

Research Librarian is the routing layer for Sustainable Catalyst. It points users to Workbench for calculation, Decision Studio for synthesis, modules for artifacts, and the Knowledge Library for topic context.

It can run in deterministic fallback mode or use Gemini/OpenAI server-side for richer routing explanations.


## v3.2.0 Knowledge Index Layer

The plugin now maintains a local knowledge index stored in `sc_rl_ai_knowledge_index`. The index combines curated source records with recent published WordPress pages/posts and is used by grounded route matching.

Index records include title, URL, type, route ID, summary, topics, source kind, metadata flags, and timestamps. The admin dashboard surfaces stale records, missing summaries, missing topics, duplicate URLs, and route coverage.
