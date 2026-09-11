# Proactive Recommendations Catalog

## Overview
The Adobe problem statement explicitly states:
> *"Suggested actions may go beyond the problems found — proactive improvements that would strengthen AI discoverability or engagement even where no explicit defect was detected."*

Proactive recommendations represent high-leverage architectural best practices that elevate a brand from simply "not broken" to "exceptionally optimized for AI synthesis and user engagement."

## Catalog of Proactive Enhancements

### 1. Dedicated `llms.txt` Discovery Manifest
- **Mechanism**: LLMs scraping web domains look for `/llms.txt` (the emerging web standard for AI-friendly markdown documentation) to quickly ingest curated facts without parsing noisy CSS and JavaScript.
- **Trigger**: Domain does not serve `/llms.txt`.
- **Suggested Action**:
  - Summary: "Publish an /llms.txt markdown file at the root domain summarizing core brand capabilities, product offerings, and documentation links."
  - Priority: `medium`
  - Implementation: Create a plain text markdown file at `https://domain.com/llms.txt` with concise bulleted descriptions of each product line.

### 2. FAQPage Structured Data for Conversational Search
- **Mechanism**: Modern conversational search engines (Perplexity, ChatGPT Search, Google AI Overviews) frequently cite question-and-answer pairs formatted in `FAQPage` schema directly in AI answer boxes.
- **Trigger**: Informational, pricing, or product landing pages lacking `FAQPage` JSON-LD.
- **Suggested Action**:
  - Summary: "Embed FAQPage JSON-LD schema on high-traffic product and pricing pages to supply conversational AI engines with verified question-and-answer pairs."
  - Priority: `medium`

### 3. Clear Text Summary Lead (TL;DR) on Informational Pages
- **Mechanism**: Long pages often suffer from LLM "lost in the middle" phenomena. A 2-sentence summary block at the top of complex pages guarantees that machine summarizers extract the core fact.
- **Suggested Action**:
  - Summary: "Include a concise 2-sentence executive summary at the top of technical and service pages to anchor LLM chunking and immediate visitor comprehension."
  - Priority: `medium`

