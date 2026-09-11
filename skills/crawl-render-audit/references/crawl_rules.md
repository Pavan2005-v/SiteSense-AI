# Crawl & Indexability Rules Reference

## Overview
AI assistants (such as ChatGPT, Gemini, Claude, and Perplexity) rely on automated retrieval systems (web fetchers, browsing plugins, and web indexers) to locate and ingest brand content. If an automated machine reader cannot crawl or index key pages, the brand becomes effectively invisible to LLMs.

## 1. robots.txt Evaluation Standards
The crawler evaluates `/robots.txt` against both general crawlers (`*`) and major AI search/crawling User-Agents:
- `GPTBot` (OpenAI training/retrieval)
- `ChatGPT-User` (OpenAI browsing in real-time)
- `ClaudeBot` / `anthropic-ai` (Anthropic retrieval)
- `Google-Extended` (Google Gemini training & contextual search)
- `PerplexityBot` (Perplexity AI real-time search)
- `Bytespider` (ByteDance / TikTok AI)

### Severity Rules for robots.txt:
- **Critical**: `Disallow: /` across all bots or explicitly blocking AI browsing agents (`ChatGPT-User`, `PerplexityBot`) from the entire site or primary product/service directories.
- **High**: Disallowing `/about`, `/products/`, `/pricing/`, `/docs/` while allowing the homepage, leading to shallow entity context where LLMs can see the brand name but cannot read what it does or sells.
- **Medium**: Disallowing `/sitemap.xml` or blocking asset directories that contain essential content text files.

## 2. Canonicalization & Meta Indexability Signals
- **`noindex` Directives**: A `<meta name="robots" content="noindex">` or HTTP header `X-Robots-Tag: noindex` on the homepage or core public pages directly blocks AI search engines from indexing the entity.
  - Severity: **Critical** if on homepage or >50% of core landing pages.
- **Canonical URL Conflicts**: If the declared `<link rel="canonical">` points to an external domain, a non-existent URL, or HTTP on an HTTPS site, machine crawlers will discard or de-prioritize the page.
  - Severity: **High** if self-referential canonical is absent on the homepage or points to a 404.

## 3. Sitemap Quality
- Sitemaps (`/sitemap.xml`) allow AI crawlers to discover all deep content without relying on high crawl budget.
- Missing or HTTP 404 on `/sitemap.xml` weakens AI discovery for sites with deep hierarchies (>10 pages).
  - Severity: **Medium**.

## 4. Bounded Politeness Safeguards
- Crawl concurrency: 1-3 parallel requests max.
- Inter-request delay: 0.1s - 0.5s.
- Per-request timeout: 5.0 seconds.
- Maximum crawl depth: 2 (Homepage -> Primary category/product pages -> Specific detail pages).
- Maximum total pages: 15 pages (prioritizing homepage, about, products, services, contact, pricing).
- Read-only: Only HTTP `GET` and `HEAD`. Never `POST`, `PUT`, `DELETE`.

