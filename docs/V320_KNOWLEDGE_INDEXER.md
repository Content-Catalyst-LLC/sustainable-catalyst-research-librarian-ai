# Research Librarian v3.2.0 — Knowledge Indexer and Admin Crawl Dashboard

v3.2.0 turns the Research Librarian from a source-aware routing assistant into a first-stage knowledge retrieval infrastructure layer.

## Purpose

The indexer tracks the Sustainable Catalyst source universe used for routing. It combines curated source records with recently published WordPress pages and posts. This keeps route recommendations grounded in known pages, modules, demos, methods, and tool routes.

## Admin dashboard

The dashboard shows:

- indexed records
- route groups
- metadata warnings
- stale records
- last indexed timestamp
- crawl mode
- indexed source table
- rebuild/reset/export controls

## Metadata checks

Records can be flagged for:

- missing or short summary
- missing topics
- stale modified date
- duplicate URL

## REST endpoints

```text
GET  /index/summary
GET  /index/records
POST /index/rebuild
GET  /index/export
```

The rebuild endpoint requires administrator permission and a WordPress REST nonce.

## Scope

This is not yet a full vector retrieval system. It is a durable local index and crawl dashboard that prepares the Research Librarian for a later semantic retrieval layer.
