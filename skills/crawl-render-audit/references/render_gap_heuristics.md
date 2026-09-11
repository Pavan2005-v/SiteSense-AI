# Render Gap & Machine-Readable Content Heuristics

## The Core Concept: Human Viewport vs Machine Reader
A human interacting with a modern web browser executes client-side JavaScript, downloads web fonts, renders SVG canvases, and decodes image overlays. 
In contrast, most AI crawlers, search retrieval fetchers (e.g., Python `urllib`, standard cURL, lightweight headless fetchers) consume only the **initial raw HTTP response body** (HTML).
If essential entity facts are only injected dynamically via client-side JavaScript (SPA frameworks like React, Angular, Vue without SSR/SSG), the machine reader sees an empty container:
```html
<div id="root"></div>
```
To the AI assistant, the brand does not exist or has zero stated offerings.

## Detection Heuristics

### 1. The Empty Shell Heuristic (JS-Dependent Core Content)
- **Condition**: Page HTML contains `<div id="root"></div>` or `<div id="app"></div>` or `<app-root></app-root>` with less than 200 words of static text content, while containing large client-side script bundles (`<script src="...bundle.js">`).
- **Impact**: AI search fetchers encounter no readable text regarding the brand's offerings, value proposition, or pricing.
- **Severity**: **Critical** if on Homepage or Product/Service landing pages.

### 2. Facts Trapped in Non-Text Elements (Image/Graphic Locking)
- **Condition**: Important business facts (pricing tables, product specifications, contact telephone/address, client testimonials, feature lists) are delivered as raster images (`<img>`, SVG graphics, canvas elements) without corresponding descriptive text or `alt` text.
- **Evidence Metric**:
  - Images with `alt` missing or generic (e.g. `alt="image"`, `alt="banner"`, `alt="graphic"`).
  - Key sections (e.g., `#pricing`, `.features`) containing high image-to-text ratios (>3 images with <30 words of text).
- **Severity**: **High** if primary value propositions or pricing are locked in images.

### 3. Hidden Content Behind Interaction
- **Condition**: Essential entity facts placed inside unindexed accordions or tabs that require client-side click events to populate into the DOM (e.g., `display: none` without server-rendered DOM nodes).
- **Severity**: **Medium**.

### 4. Text vs Code Ratio
- **Condition**: Extracted text content is less than 5% of total HTML byte size, indicating excessive script/style bloat that dilutes lexical search relevance in RAG chunking pipelines.
- **Severity**: **Medium**.

