# Sustainable Catalyst Research Librarian AI

AI-enabled Research Librarian plugin for Sustainable Catalyst.

This WordPress plugin provides a bounded research-routing assistant for Sustainable Catalyst. It helps visitors navigate platform demos, methodology pages, article maps, repositories, knowledge libraries, feature suggestions, and support paths.

## Website

https://sustainablecatalyst.com/

## Research Librarian Page

https://sustainablecatalyst.com/platform/research-librarian/

## Shortcode

```text
[sustainable_catalyst_research_librarian_ai]
```

## Core Purpose

The Research Librarian helps visitors:

- identify what they are trying to do
- choose the right Sustainable Catalyst starting point
- understand why a route fits
- move toward relevant demos, repositories, article maps, or feature-suggestion paths
- stay inside clear boundaries

## Boundaries

The assistant is for navigation, research orientation, and learning support. It does not provide legal, financial, investment, medical, mental health, tax, compliance, assurance, ESG certification, SDG certification, or other regulated professional advice.

## Knowledge Base

Version 2.1.1 includes WordPress admin support for uploading a markdown or text knowledge seed directly from:

```text
Settings → Research Librarian AI → Knowledge Base Upload
```

The plugin uses the saved OpenAI API key from WordPress settings. The API key should not be committed to GitHub.

## OpenAI Configuration

Configure inside WordPress:

```text
Settings → Research Librarian AI
```

Required fields:

- OpenAI API Key
- Model
- Vector Store ID

The vector store ID begins with `vs_`.

## Repository Safety

Do not commit API keys, secrets, `.env` files, logs, or local WordPress backups.
