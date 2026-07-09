# Research Librarian v3.9.0 — Scheduled Index Maintenance, Sitemap Sync, and Health Alerts

This build adds an operational maintenance layer for the Sustainable Catalyst Research Librarian.

## Added

- Scheduled knowledge-index rebuild controls
- WordPress cron hook for index maintenance
- Manual Run Index Maintenance action
- Sync Maintenance Schedule action
- Optional sitemap URL ingestion for route coverage
- Sitemap URL limit setting
- Optional embedding generation after maintenance rebuilds
- Maintenance health summary
- Admin maintenance export endpoint
- Public maintenance-summary shortcode
- Warning email option for maintenance failures

## Notes

The maintenance layer is conservative by default. Scheduled rebuilds are off until enabled in settings. Automatic embedding after rebuilds is also off by default because free-tier Gemini keys can hit rate limits. The recommended first configuration is a daily scheduled index rebuild with sitemap ingestion enabled and automatic embeddings disabled.
