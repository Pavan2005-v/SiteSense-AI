# On-Site Engagement & Visitor Retention Heuristics

## Overview
Discoverability only gets a visitor (or an AI assistant referring a human) to the door. Once a human arrives on a website, they make an engagement decision within 5-10 seconds. If the page lacks an immediate value proposition, presents broken or dead-end navigation, or strands users on deep pages without context, the visitor bounces immediately.

## 1. Above-The-Fold Value Proposition (The "5-Second Rule")
- **The Problem**: Corporate buzzwords and abstract slogans ("Empowering Holistic Transformation", "Unleashing Tomorrow's Synergy") fail to communicate what the product actually does, what problem it solves, or who it is for.
- **Heuristic**:
  - Homepage `<h1>` must contain concrete action/product nouns rather than purely abstract buzzwords.
  - An accompanying subhead (`<p>`) must clarify the specific target audience or capability.
  - Severity: **High** if `<h1>` is missing, empty, or purely buzzwords without explanatory subtext.

## 2. Deep-Page Orientation & Context Retention
- **The Problem**: Over 60% of modern visitors land directly on deep pages (e.g., specific blog posts, documentation pages, or product sub-tiers) via search or AI citations, bypassing the homepage completely.
- **Heuristic**:
  - Pages at depth >= 2 must provide orienting signals: breadcrumb navigation, category tags, or visible parent links.
  - If a deep page has no breadcrumb trail and no parent category link, a visitor arriving via an AI citation has zero context about the broader platform.
  - Severity: **Medium** to **High** depending on percentage of affected pages.

## 3. Navigation Dead Ends
- **The Problem**: A user finishes reading a page (e.g. an article, about page, or product overview) and reaches the bottom with no suggested next step, no related articles, and no clear pathway.
- **Heuristic**:
  - Content pages containing 0 outbound internal body links or next-step CTAs are classified as "Dead Ends".
  - Severity: **High** if product or landing pages end with zero CTA.

## 4. Call-to-Action (CTA) Visibility & Friction
- **The Problem**: Either no primary action is offered ("Where do I buy/try?"), or too many competing high-contrast buttons create decision paralysis.
- **Heuristic**:
  - Key landing pages (homepage, product, pricing) must feature an explicit primary action button (e.g. "Get Started", "Request Demo", "Start Free Trial", "Buy Now").
  - Severity: **High** if primary conversion page has no detectable CTA button or link.

