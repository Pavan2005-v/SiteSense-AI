# Applicability Engine & Context Rules

## Overview
The **Applicability Engine** acts as an architectural gatekeeper between site/page classification and specialist skill execution:

```
Crawl
  ↓
Site Classification (ecommerce, saas, corporate, publisher, docs, other)
  ↓
Page Classification (homepage, product_detail, product_listing, pricing, legal, ...)
  ↓
APPLICABILITY ENGINE
  ↓
Specialist Skills (only evaluated where applicable)
  ↓
Observations & Evidence Validation
  ↓
Confirmed Findings
```

This prevents the fundamental flaw of treating web auditing as a single universal checklist.

---

## Page-Type Applicability Matrix

| Audit Check | Applicable Page Types | Exempted Page Types | Rationale |
|---|---|---|---|
| **Product / Offer Schema** | `product_detail` | `homepage`, `about`, `legal`, `privacy`, `terms`, `docs`, `pricing`, `product_listing` | Informational pages, category listings, and legal documents do not sell individual SKUs. |
| **Call-To-Action (CTA)** | `homepage`, `product_detail`, `pricing`, `service`, `landing` | `legal`, `privacy`, `terms`, `documentation`, `article`, `contact`, `search` | Visitors on privacy policies or reference documentation are seeking specific facts, not commercial conversions. |
| **H1 Purpose Orientation** | `homepage`, `product_detail`, `pricing`, `service`, `about`, `article` | Utility pages with clear embedded purpose or search boxes | Evaluates purpose clarity rather than strict HTML tag presence. |
| **Navigation Dead-Ends** | Core site pages (`homepage`, `product_detail`, `pricing`, `service`, `about`) | `legal`, `privacy`, `terms`, `documentation` | Legal policies are intentionally focused single-topic documents. |
| **Breadcrumb Orientation** | Deep content pages (`path depth` $\ge 2$) | `homepage`, root pages, `legal`, `privacy`, `terms` | Legal disclaimers do not require hierarchical breadcrumb navigation. |

---

## Site-Type Applicability Matrix

| Audit Check | Applicable Site Types | Exempted Site Types | Rationale |
|---|---|---|---|
| **Product Schema & Offers** | `ecommerce`, `marketplace` | `corporate`, `saas`, `publisher`, `documentation`, `portfolio`, `nonprofit` | Non-retail organizations do not maintain ecommerce inventories. |
| **Cross-Page Pricing Consistency** | `ecommerce`, `saas`, `marketplace` | `publisher`, `documentation`, `nonprofit`, `portfolio` | Editorial sites and portfolios rarely have structured pricing tiers. |
| **Organization sameAs Anchors** | All sites (Homepage only) | Deep sub-pages | Entity knowledge graph anchoring belongs on the canonical root domain. |

