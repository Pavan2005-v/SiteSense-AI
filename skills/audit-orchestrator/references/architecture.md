# Marketplace Architecture & Composition Model

## Overview
The `audit-orchestrator` is the sole entrypoint skill (`"entrypoint": true` in `marketplace.json`).
It is responsible for accepting the audit target (URL or domain), establishing a bounded, polite crawl, coordinating the 5 specialist skills, normalizing and deduplicating their findings, prioritizing actions, injecting proactive recommendations, and producing a deterministic final report.

```
                  +-----------------------------------+
                  |         Audit Target URL          |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |        Bounded Polite Crawl       |
                  |     (robots.txt, <15 pages, BFS)  |
                  +-----------------------------------+
                                    |
            +-----------------------+-----------------------+
            |                       |                       |
            v                       v                       v
+-----------------------+ +-------------------+ +-----------------------+
|  crawl-render-audit   | | structured-data   | | freshness-            |
| (robots, render gaps, | | (JSON-LD, Product,| | corroboration         |
|  SPA shells, images)  | |  Org, Offer, PDP) | | (staleness, pricing)  |
+-----------------------+ +-------------------+ +-----------------------+
            |                       |                       |
            +-----------------------+-----------------------+
                                    |
            +-----------------------+-----------------------+
            |                                               |
            v                                               v
+-----------------------+                       +-----------------------+
|  entity-clarity-audit |                       |   engagement-audit    |
| (brand ambiguity,     |                       | (value prop, CTAs,    |
|  sameAs anchors)      |                       |  breadcrumbs, dead-end|
+-----------------------+                       +-----------------------+
            |                                               |
            +-----------------------+-----------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |         Deduplication Engine      |
                  |     (Root-cause clustering)       |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |        Prioritization Engine      |
                  |  (Severity + Impact Matrix)       |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |     Proactive Improvement Engine  |
                  |    (llms.txt, Schema FAQs, etc.)  |
                  +-----------------------------------+
                                    |
                                    v
                  +-----------------------------------+
                  |       Final Report Generator      |
                  |   (Strict Adobe JSON Schema)      |
                  +-----------------------------------+
```

## Data Isolation & Pure Functions
1. Specialists do not mutate website state (100% read-only).
2. Specialists do not execute independent network requests if a `CrawlSummary` is provided. They evaluate the parsed document models in parallel or sequence, guaranteeing zero redundant bandwidth consumption and sub-minute execution.
3. Every specialist returns standardized `AuditFinding` instances.
4. The orchestrator owns deduplication, severity normalization, action synthesis, and final JSON report formatting.

