# Schema.org Expectations by Page Type

## Overview
AI assistants prioritize structured data because JSON-LD schemas explicitly define entity graphs, relationships, prices, authors, and identities in unambiguous, machine-native formats. Without structured data, AI retrieval engines must rely on heuristic text parsing, which introduces extraction errors or leads the AI to overlook the entity altogether.

## Context-Aware Schema Matrix

### 1. Homepage & Root Brand Pages
- **Mandatory Schemas**: `Organization` (or `Corporation` / `LocalBusiness`) and `WebSite`.
- **Key Properties for `Organization`**:
  - `name`: Exact legal or recognized brand name.
  - `url`: Canonical domain root.
  - `logo`: High-resolution logo image URL.
  - `sameAs`: Array of authoritative external profile URLs (Wikidata, Wikipedia, LinkedIn, Crunchbase, official social channels).
  - `description`: Machine-readable summary of organization function.
- **Key Properties for `WebSite`**:
  - `name`: Website name.
  - `url`: Canonical URL.
  - Optional `potentialAction`: `SearchAction` for internal site search.

### 2. Product Detail Pages (PDP)
- **Mandatory Schemas**: `Product` with nested or referenced `Offer`.
- **Key Properties for `Product`**:
  - `name`: Product title.
  - `description`: Detailed product description.
  - `image`: Product image URL.
  - `brand`: Brand entity or string.
- **Key Properties for `Offer`**:
  - `price`: Numeric price (e.g. `29.99` or `"29.99"`).
  - `priceCurrency`: ISO 4217 currency code (e.g. `"USD"`, `"EUR"`).
  - `availability`: Schema availability URI (e.g. `https://schema.org/InStock`).

### 3. Service & Solution Pages
- **Recommended Schemas**: `Service` or `ProfessionalService`.
- **Key Properties**: `name`, `provider`, `serviceType`, `areaServed`, `description`.

### 4. Blog Posts, Articles, and News
- **Mandatory Schemas**: `Article`, `BlogPosting`, or `NewsArticle`.
- **Key Properties**:
  - `headline`: Article headline.
  - `datePublished`: ISO 8601 publication timestamp.
  - `dateModified`: ISO 8601 last modified timestamp.
  - `author`: `Person` or `Organization` entity.
  - `publisher`: Publisher entity with logo.

### 5. Deep Hierarchical Pages
- **Recommended Schema**: `BreadcrumbList`.
- **Key Properties**: `itemListElement` array containing `ListItem` entries with `position`, `name`, and `item` (URL).

