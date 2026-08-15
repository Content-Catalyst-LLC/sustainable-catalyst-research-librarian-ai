# Research Librarian AI v7.3.0 — Test Results

Release: **v7.3.0 — Source Evaluation, Evidence Comparison & Research Quality Signals**

## Certification summary

- Backend regression suite: **109 passed / 109 total**
- Backend suite repeated from `backend/`: **109 passed / 109 total**
- WordPress contract + functional test files: **34 passed / 34 total**
- Dedicated v7.3.0 source/evidence-quality contract: **66 passed / 66 checks**
- PHP syntax validation: **48 files passed**
- JavaScript syntax validation: **3 files passed**
- JSON parse validation: **96 files passed**
- Python bytecode compilation: **passed**
- v7.3.0 push-script shell syntax: **passed**
- Secret-pattern scan: **0 hits**

## New v7.3.0 coverage

The release tests verify:

- descriptive source profiles with source type, evidence role, publisher/institution, publication date, methodology, citation metadata, access state, provenance, and known limitations;
- primary/secondary source-role preservation when that metadata exists;
- side-by-side evidence comparison without choosing an automatic winner;
- structural gap detection for missing primary evidence, provider diversity, methods visibility, dates, citation metadata, limitations, and contrasting positions;
- explicit absence of truth scores and credibility scores;
- explicit human-judgment and human-review boundaries;
- context-wide quality review against an authenticated saved research context;
- bounded quality metadata in the existing v7.2 research-context prompt contract;
- owner authorization for private Library objects and contexts at the WordPress bridge;
- admin-only creation of official Sustainable Catalyst editorial source scope through the WordPress bridge;
- optional persistence of source evaluation, evidence comparison, and gap reports using existing project entities;
- preservation of v7.2 Library object/context behavior and v7.1.2 Neon/Postgres durability behavior.

## Storage and migration

No new database migration is required. The production knowledge index remains Neon/Postgres with pgvector. Ancillary connected-workspace data remains on SQLite schema 13. Optional quality reports persist through the existing `research_project_entities` contract and remain included in project backup behavior.

## Release contracts

- Plugin/backend version: `7.3.0`
- Connected Research API: `sc-connected-research-api/1.2`
- Public workspace: `sc-research-librarian-public-workspace/2.2`
- Source evaluation: `sc-source-evaluation/1.0`
- Evidence comparison: `sc-evidence-comparison/1.0`
- Evidence gap report: `sc-evidence-gap-report/1.0`
- Research quality signals: `sc-research-quality-signals/1.0`
