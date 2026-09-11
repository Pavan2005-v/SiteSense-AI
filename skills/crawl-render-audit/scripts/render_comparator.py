"""
Render Comparator and Machine-Readable Extraction Analyzer.
Identifies discrepancies between what a browser displays vs what a machine crawler extracts.
"""
from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup


class RenderComparator:
    def __init__(self, pages: List[Any]):
        self.pages = pages

    def audit_render_gaps(self) -> List[Dict[str, Any]]:
        findings = []
        
        # 1. Check for SPA Empty Shell (React/Vue/Angular without SSR)
        spa_empty_pages = []
        for p in self.pages:
            html = p.raw_html or ""
            soup = BeautifulSoup(html, "html.parser")
            
            # Check for common SPA mounts
            has_spa_mount = bool(
                soup.find(id=re.compile(r"^(root|app|__next)$", re.I)) or
                soup.find("app-root")
            )
            
            # Count visible text length
            text = p.text_content or ""
            word_count = len(text.split())
            script_count = len(soup.find_all("script"))

            if has_spa_mount and word_count < 50 and script_count > 0:
                spa_empty_pages.append((p.url, word_count))

        if spa_empty_pages:
            sample_urls = [f"{u} ({wc} words in initial HTML)" for u, wc in spa_empty_pages[:3]]
            findings.append({
                "issue_type": "js_render_gap",
                "severity": "critical" if any("home" in u.lower() or u == self.pages[0].url for u, _ in spa_empty_pages) else "high",
                "title": f"Initial HTML is an empty JavaScript container on {len(spa_empty_pages)} page(s)",
                "evidence": f"Found empty SPA mount container (<div id='root'>/app) with minimal initial text on: {'; '.join(sample_urls)}.",
                "action": "Implement Server-Side Rendering (SSR) or Static Site Generation (SSG) so search and AI bots receive readable text in the initial HTTP response without requiring browser JavaScript execution.",
                "why_it_matters": "Empty client-side rendered apps cannot be read by many AI and search agents, meaning your content effectively does not exist for them.",
                "confidence": "high",
                "root_cause": "The site relies heavily on client-side rendering (CSR) without SSR fallback.",
                "affected_urls": [u for u, _ in spa_empty_pages]
            })

        # 2. Check for Text Locked in Images (Non-text representation of facts)
        missing_alt_images = []
        affected_image_urls = []
        total_images = 0
        for p in self.pages:
            html = p.raw_html or ""
            soup = BeautifulSoup(html, "html.parser")
            imgs = soup.find_all("img")
            total_images += len(imgs)
            for img in imgs:
                alt = (img.get("alt") or "").strip()
                src = img.get("src") or ""
                # Ignore tiny tracking pixels or icons
                if not alt and not any(skip in src.lower() for skip in ["pixel", "track", "icon", "spacer", "logo", "decorative"]):
                    missing_alt_images.append((p.url, src))
                    if p.url not in affected_image_urls:
                        affected_image_urls.append(p.url)

        if total_images > 0 and len(missing_alt_images) > 3:
            ratio = len(missing_alt_images) / total_images
            if ratio > 0.4:
                sample_imgs = [src[:60] for _, src in missing_alt_images[:3]]
                findings.append({
                    "issue_type": "facts_locked_in_images",
                    "severity": "medium",
                    "title": f"Important visual content lacks machine-readable descriptions ({len(missing_alt_images)} images without alt text)",
                    "evidence": f"{len(missing_alt_images)} of {total_images} sampled images ({ratio:.0%}) lack 'alt' attributes. Sample images: {', '.join(sample_imgs)}.",
                    "action": "Add descriptive 'alt' text to all informative product, architectural, and diagrammatic images so AI vision-language models and screen readers can parse the information.",
                    "why_it_matters": "Images without alt text prevent AI vision models and standard text extractors from understanding visual information, degrading knowledge extraction.",
                    "confidence": "medium",
                    "root_cause": "Missing `alt` attributes on image tags in the HTML markup.",
                    "affected_urls": affected_image_urls
                })

        # 3. Check for Meta Noindex on Core Discoverable Pages (Part 1 Refinement)
        unintended_noindex_pages = []
        is_homepage_blocked = False

        for p in self.pages:
            html = p.raw_html or ""
            soup = BeautifulSoup(html, "html.parser")
            meta_robots = soup.find("meta", attrs={"name": re.compile(r"^robots$", re.I)})
            if not meta_robots:
                continue

            content = (meta_robots.get("content") or "").lower()
            if "noindex" not in content:
                continue

            # Purpose-aware evaluation: check if page is intentionally non-indexable
            from skills.common.page_classifier import is_legal_page
            is_intentional_noindex = (
                is_legal_page(p.page_type) or
                p.page_type in ("legal", "privacy", "terms", "search", "utility") or
                any(seg in (p.url or "").lower() for seg in [
                    "/privacy", "/terms", "/legal", "/disclaimer", "/cookie",
                    "/search", "/login", "/signin", "/cart", "/checkout", "/account", "/admin"
                ])
            )

            if is_intentional_noindex:
                # Raw observation kept internally, but suppressed from defect findings
                continue

            # Core pages where noindex is a true defect
            if p.page_type in ("homepage", "product_detail", "pricing", "service", "about", "article", "landing", "general"):
                unintended_noindex_pages.append(p.url)
                if p.page_type == "homepage":
                    is_homepage_blocked = True

        if unintended_noindex_pages:
            severity = "critical" if is_homepage_blocked else "high"
            findings.append({
                "issue_type": "meta_noindex_detected",
                "severity": severity,
                "title": f"'noindex' meta tag detected on {len(unintended_noindex_pages)} core discoverable page(s)",
                "evidence": f"Public brand pages contain <meta name='robots' content='noindex'>: {', '.join(unintended_noindex_pages[:3])}.",
                "action": "Remove the 'noindex' directive from public landing and informational pages to allow indexing and retrieval by search engines and AI assistants.",
                "why_it_matters": "A noindex directive on core brand assets prevents search engines and AI assistants from indexing your primary offerings and credentials.",
                "confidence": "high",
                "root_cause": "A `<meta name='robots' content='noindex'>` tag is present in the HTML head of public landing pages.",
                "affected_urls": unintended_noindex_pages
            })

        # 4. Context-Aware Canonical and Duplicate Content Analysis (Part 1, 8)
        # Check for Conflicting Canonicals
        conflicting_canonicals = []
        missing_canonicals = set()
        for p in self.pages:
            canonical_href = None
            if p.canonical_url:
                canonical_href = p.canonical_url
            elif p.raw_html:
                soup = BeautifulSoup(p.raw_html, "html.parser")
                can_tag = soup.find("link", rel=re.compile(r"canonical", re.I))
                if can_tag and can_tag.get("href"):
                    canonical_href = can_tag.get("href").strip()

            if not canonical_href:
                missing_canonicals.add(p.url)
            else:
                from skills.common.url_utils import normalize_url
                norm_canonical = normalize_url(canonical_href)
                norm_page = normalize_url(p.url)
                if norm_canonical != norm_page:
                    conflicting_canonicals.append((p.url, canonical_href))

        if conflicting_canonicals:
            findings.append({
                "issue_type": "conflicting_canonical",
                "severity": "medium",
                "title": f"Conflicting canonical URL declarations on {len(conflicting_canonicals)} page(s)",
                "evidence": f"Pages declare canonical tags pointing to divergent URLs: {'; '.join(f'{u} -> {c}' for u, c in conflicting_canonicals[:2])}.",
                "action": "Ensure canonical link tags accurately reflect the canonical version or are self-referential to avoid content attribution loss.",
                "why_it_matters": "Conflicting canonical declarations instruct search engines and AI crawlers to discard the current page's content in favor of another URL.",
                "confidence": "high",
                "root_cause": "Canonical link tag targets a different URL than the host document.",
                "affected_urls": [u for u, _ in conflicting_canonicals]
            })

        # Check for Duplicate Content Without Canonical Resolution
        content_map = {}
        duplicates_detected = []
        for p in self.pages:
            text = (p.text_content or "").strip()
            title = (p.title or "").strip()
            sig = text[:200] if len(text) > 30 else title
            if sig:
                if sig in content_map:
                    orig_url = content_map[sig]
                    duplicates_detected.append((orig_url, p.url))
                else:
                    content_map[sig] = p.url

        if duplicates_detected:
            dup_urls = list(set([u for pair in duplicates_detected for u in pair]))
            # If any of the duplicate URLs lack canonical resolution
            if any(u in missing_canonicals for u in dup_urls):
                findings.append({
                    "issue_type": "unresolved_duplicate_content",
                    "severity": "medium",
                    "title": f"Duplicate content detected across {len(dup_urls)} URLs without canonical resolution",
                    "evidence": f"Multiple crawled URLs serve duplicate or identical content without canonical tags to designate the primary source: {', '.join(dup_urls[:3])}.",
                    "action": "Implement canonical link tags on duplicate and parameterized URL variants pointing to the single authoritative master page.",
                    "why_it_matters": "Duplicate pages without canonicals divide entity authority, dilute search rank, and risk contradictory chunk indexing by AI assistants.",
                    "confidence": "high",
                    "root_cause": "Duplicate pages are served at multiple URLs without self-referential or master canonical link tags.",
                    "affected_urls": dup_urls
                })

        return findings
