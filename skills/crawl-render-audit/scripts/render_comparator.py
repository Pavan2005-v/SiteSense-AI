"""
Render Comparator and Machine-Readable Extraction Analyzer.
Identifies discrepancies between what a browser displays vs what a machine crawler extracts.
Evaluates:
- Client-Side Rendering (CSR) SPA empty shells
- Important business facts trapped in non-text graphics without text equivalents
- Unintended 'noindex' directives on core discoverable pages
- Meaningful canonical conflicts and uncanonicalized duplicate content
"""
from typing import List, Dict, Any, Optional, Set
import re
from urllib.parse import urlparse, urljoin
from bs4 import BeautifulSoup
from skills.common.url_utils import normalize_url


# File name or attribute patterns indicating decorative, icon, or utility imagery
DECORATIVE_IMAGE_PATTERNS = [
    "pixel", "track", "icon", "spacer", "logo", "decorative", "badge",
    "avatar", "thumb", "button", "btn", "arrow", "bullet", "flag",
    "spinner", "loader", "bg-", "background", "social", "glyph", "emoji"
]


class RenderComparator:
    def __init__(self, pages: List[Any]):
        self.pages = pages

    def audit_render_gaps(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Evidence-Driven Check for Genuinely Empty Client-Side Rendered Shells (Category C)
        # Distinguishes:
        # A) Normal JavaScript applications with readable, accessible server-rendered HTML (Not a defect)
        # B) JS-heavy pages where server HTML is thin but accessible content exists (Not a critical defect)
        # C) Genuinely empty/near-empty server response where important public content depends entirely on client execution (Defect)
        spa_empty_pages = []
        for p in self.pages:
            html = p.raw_html or ""
            soup = BeautifulSoup(html, "html.parser")

            # Check for common SPA mounts
            mount_node = (
                soup.find("app-root") or
                soup.find(id=re.compile(r"^(?:root|app|__next)$", re.I)) or
                soup.find(attrs={"id": re.compile(r"^app$", re.I)})
            )
            has_spa_mount = bool(mount_node)
            mount_tag = mount_node.name if mount_node else "div"
            if mount_node and mount_node.get("id"):
                mount_tag = f"{mount_node.name}#{mount_node.get('id')}"

            raw_text = (p.text_content or "").strip()
            raw_text_lower = raw_text.lower()
            html_lower = html.lower()

            # Client fallback / interstitial indicators
            fallback_phrases = [
                "cookies disabled", "please wait", "enable cookies", "enable javascript",
                "javascript is required", "your browser does not support javascript",
                "prerenderready", "window.prerenderready"
            ]
            matched_fallbacks = [fp for fp in fallback_phrases if fp in raw_text_lower or fp in html_lower]

            word_count = len(raw_text.split())
            script_count = len(soup.find_all("script"))

            # Inspect substantive semantic content in initial HTML
            substantive_paras = [
                tag.get_text(strip=True) for tag in soup.find_all(["p", "article", "section", "dd", "li"])
                if len(tag.get_text(strip=True).split()) >= 10 and not any(fp in tag.get_text(strip=True).lower() for fp in fallback_phrases)
            ]
            content_headings = [
                h.get_text(strip=True) for h in soup.find_all(["h1", "h2"])
                if len(h.get_text(strip=True).split()) >= 2 and not any(fp in h.get_text(strip=True).lower() for fp in fallback_phrases)
            ]

            # Category A: Normal JS app with accessible initial HTML -> NEVER a defect
            if word_count >= 120 or len(substantive_paras) >= 2:
                p.is_spa_shell = False
                continue

            # Additional meaningfulness guards (Phase 3): a page whose initial HTML contains
            # structured data, meaningful navigation, or descriptive metadata is NOT an empty shell.
            has_structured_data = len(soup.find_all("script", type="application/ld+json")) > 0
            has_meaningful_nav = len(p.internal_links) >= 8
            has_descriptive_metadata = bool((p.title or "").strip()) and len((p.meta_description or "").split()) >= 8
            meaningful_initial_content = (
                has_structured_data or
                has_meaningful_nav or
                has_descriptive_metadata
            )

            # Category C: Genuinely empty/near-empty server response
            # Mount container is unpopulated, 0 substantive paragraphs, 0 content headings,
            # body text is minimal (< 40 words), AND no meaningful structured data,
            # navigation, or descriptive metadata in the initial representation.
            is_empty_mount = False
            if mount_node:
                mount_inner_text = mount_node.get_text(strip=True)
                is_empty_mount = (len(mount_inner_text.split()) < 10)

            is_genuinely_empty_shell = (
                (has_spa_mount and is_empty_mount) or bool(matched_fallbacks)
            ) and len(substantive_paras) == 0 and len(content_headings) == 0 and word_count < 40 and script_count > 0 and not meaningful_initial_content

            if is_genuinely_empty_shell:
                p.is_spa_shell = True
                sample_text = raw_text[:80].replace("\n", " ") if raw_text else "empty response"
                spa_empty_pages.append((p.url, word_count, mount_tag, sample_text))

        if spa_empty_pages:
            homepage_url = next((pg.url for pg in self.pages if pg.page_type == "homepage"), None)
            # Severity reflects DEMONSTRATED impact on machine consumers of the initial response:
            # - homepage / primary entry page: initial response carries essentially no content -> high
            # - other public pages: partial scope -> medium
            # CRITICAL is reserved for a demonstrated render comparison (initial vs rendered) proving
            # major public content is unavailable in the initial representation. This audit performs
            # no browser rendering, so critical is never claimed from initial HTML alone.
            is_homepage_affected = homepage_url is not None and any(
                normalize_url(u) == normalize_url(homepage_url) for u, _, _, _ in spa_empty_pages
            )
            findings.append({
                "issue_type": "js_render_gap",
                "severity": "high" if is_homepage_affected else "medium",
                "title": f"Initial HTML response is essentially empty; page content may depend on client-side JavaScript on {len(spa_empty_pages)} page(s)",
                "evidence": (
                    f"The initial HTTP response for {len(spa_empty_pages)} page(s) contains essentially no machine-readable "
                    f"content (word counts: {'; '.join(f'{u}: {wc} words' for u, wc, _, _ in spa_empty_pages[:3])}); "
                    f"no substantive paragraphs, content headings, structured data, or meaningful navigation are present. "
                    f"If these pages produce their content via client-side JavaScript, machine consumers that rely on the "
                    f"initial response receive no meaningful content."
                ),
                "action": "Implement Server-Side Rendering (SSR), Static Site Generation (SSG), or prerendering for the affected public routes so that the initial HTTP response contains the primary semantic content without requiring browser JavaScript execution.",
                "why_it_matters": "Machine consumers that do not execute JavaScript (many AI crawlers, simple indexers) extract content from the initial HTTP response. When that response is essentially empty, they cannot extract the page's content, though browsers and rendering-capable crawlers may still see it.",
                "confidence": "medium",
                "root_cause": "Public page routes deliver an empty application shell in the initial HTTP response; content is injected client-side at runtime.",
                "affected_urls": [u for u, _, _, _ in spa_empty_pages],
                "limitations": (
                    "No browser rendering was performed in this audit, so the rendered (post-JavaScript) content could not be "
                    "compared with the initial response. The finding is based on the directly observed emptiness of the initial "
                    "HTTP response; it does not claim that rendering-capable clients cannot access the content."
                )
            })

        # 2. Check for Substantive Facts Locked in Non-Text Graphics
        # Only flag when substantial, informative images (diagrams, charts, product cards) lack descriptions
        substantive_missing_alts = []
        affected_image_urls = []
        total_substantive_images = 0

        for p in self.pages:
            html = p.raw_html or ""
            soup = BeautifulSoup(html, "html.parser")
            imgs = soup.find_all("img")

            for img in imgs:
                src = (img.get("src") or "").lower()
                alt = (img.get("alt") or "").strip()
                role = (img.get("role") or "").lower()
                aria_hidden = (img.get("aria-hidden") or "").lower()

                # Ignore explicitly decorative or utility images
                if role == "presentation" or aria_hidden == "true":
                    continue
                if any(skip in src for skip in DECORATIVE_IMAGE_PATTERNS):
                    continue

                total_substantive_images += 1
                if not alt:
                    substantive_missing_alts.append((p.url, img.get("src", "")[:80]))
                    if p.url not in affected_image_urls:
                        affected_image_urls.append(p.url)

        if total_substantive_images >= 4 and len(substantive_missing_alts) >= 3:
            ratio = len(substantive_missing_alts) / total_substantive_images
            if ratio >= 0.5:
                sample_imgs = [src for _, src in substantive_missing_alts[:3]]
                findings.append({
                    "issue_type": "facts_locked_in_images",
                    "severity": "medium",
                    "title": f"Substantive visual content lacks text descriptions ({len(substantive_missing_alts)} informative images without alt text)",
                    "evidence": f"{len(substantive_missing_alts)} of {total_substantive_images} informative content images ({ratio:.0%}) lack 'alt' attributes or text equivalents. Sample images: {', '.join(sample_imgs)}.",
                    "action": "Add descriptive 'alt' text and accompanying readable text captions to all informative product, architectural, and diagrammatic images.",
                    "why_it_matters": "Images without alt text or textual equivalents prevent text-based AI models and screen readers from extracting facts contained in the graphic.",
                    "confidence": "medium",
                    "root_cause": "Omission of machine-readable `alt` attributes on informative graphics and diagrams.",
                    "affected_urls": affected_image_urls
                })

        # 3. Check for Meta Noindex on Core Discoverable Pages
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

        # 4. Context-Aware Canonical and Duplicate Content Analysis
        # A canonical tag legitimately points to a DIFFERENT preferred URL (normalized,
        # localized, or master variant). A differing path/host is therefore NOT a defect.
        # True canonical defects require direct evidence:
        #   (a) multiple distinct canonical declarations on the SAME page
        #   (b) malformed / invalid canonical URL
        #   (c) a demonstrated canonical cycle across crawled pages (A -> B -> A)
        # Canonical chains (A -> B -> C) and equivalent-target canonicals are valid.
        conflicting_canonicals = []       # (url, detail) — evidence-backed defects only
        canonical_edges: Dict[str, str] = {}   # normalized page url -> normalized single canonical target
        missing_canonicals: Set[str] = set()

        for p in self.pages:
            soup = BeautifulSoup(p.raw_html or "", "html.parser")
            can_tags = soup.find_all("link", rel=re.compile(r"^canonical$", re.I))

            # (a) Multiple canonical tags on the SAME page with DIFFERENT targets is a defect
            if len(can_tags) > 1:
                targets = [t.get("href", "").strip() for t in can_tags]
                distinct_targets = {normalize_url(urljoin(p.url, t)) for t in targets if t}
                if len(distinct_targets) > 1:
                    conflicting_canonicals.append((p.url, f"Multiple canonical tags pointing to different targets: {', '.join(sorted(targets))}"))

            valid_targets = []
            for t in can_tags:
                href = (t.get("href") or "").strip()
                if not href or href.lower() in ("none", "undefined", "null", "javascript:void(0)"):
                    # (b) Malformed / empty canonical declaration
                    conflicting_canonicals.append((p.url, f"Malformed canonical declaration: href='{href}'"))
                    continue
                valid_targets.append(href)

            if not can_tags:
                missing_canonicals.add(p.url)
            elif valid_targets:
                # Resolve relative canonicals against the page URL; normalize for comparison
                primary = urljoin(p.url, valid_targets[0])
                canonical_edges[normalize_url(p.url)] = normalize_url(primary)

        # (c) Detect DEMONSTRATED canonical cycles (A -> B -> A) across crawled pages.
        # Chains (A -> B -> C) are valid per the canonical specification and are NOT reported.
        for start, target in canonical_edges.items():
            if target not in canonical_edges:
                continue  # target page not crawled; a cycle cannot be demonstrated
            seen = set()
            current = start
            while current in canonical_edges and current not in seen and len(seen) <= 10:
                seen.add(current)
                current = canonical_edges[current]
            if current == start and len(seen) >= 1 and start != canonical_edges[start]:
                # Confirmed cycle back to the origin
                cycle_path = " -> ".join(list(seen) + [start])
                if not any(u == start for u, _ in conflicting_canonicals):
                    conflicting_canonicals.append((start, f"Circular canonical chain detected: {cycle_path}"))

        if conflicting_canonicals:
            urls = list(set([u for u, _ in conflicting_canonicals]))
            findings.append({
                "issue_type": "conflicting_canonical",
                "severity": "medium",
                "title": f"Conflicting or circular canonical URL declarations on {len(urls)} page(s)",
                "evidence": f"Pages declare contradictory or malformed canonical link targets (multiple distinct targets on the same page, invalid href values, or a demonstrated canonical cycle): {'; '.join(f'{u}: {c}' for u, c in conflicting_canonicals[:2])}.",
                "action": "Ensure each page declares exactly one valid canonical URL; remove duplicate or contradictory canonical tags and break any canonical loops.",
                "why_it_matters": "Contradictory or circular canonical declarations create index ambiguity, causing AI crawlers and search engines to discard or misattribute content.",
                "confidence": "high",
                "root_cause": "Multiple, malformed, or circular `<link rel='canonical'>` tags configured on the same document.",
                "affected_urls": urls
            })

        # Check for Duplicate Content Without Canonical Resolution
        # Never compare pages using unrendered SPA shells or challenge pages (Section 6)
        content_map: Dict[str, str] = {}
        duplicates_detected = []
        for p in self.pages:
            if getattr(p, "is_spa_shell", False):
                continue
            text = (p.text_content or "").strip()
            text_lower = text.lower()
            if any(err in text_lower for err in ("cookies disabled", "please wait", "javascript is required", "enable cookies")):
                continue
            title = (p.title or "").strip()
            # Signature derived from significant title and initial body text
            sig = f"{title}:::{text[:250]}" if len(text) > 40 else ""
            if sig:
                if sig in content_map:
                    orig_url = content_map[sig]
                    duplicates_detected.append((orig_url, p.url))
                else:
                    content_map[sig] = p.url

        if duplicates_detected:
            dup_urls = list(set([u for pair in duplicates_detected for u in pair]))
            # Only flag if duplicate URLs lack canonical resolution
            unresolved_dups = [u for u in dup_urls if u in missing_canonicals]
            if unresolved_dups:
                findings.append({
                    "issue_type": "unresolved_duplicate_content",
                    "severity": "medium",
                    "title": f"Duplicate content detected on {len(unresolved_dups)} page(s) without canonical resolution",
                    "evidence": f"Multiple crawled URLs serve duplicate or identical content without canonical tags to designate the primary source: {', '.join(unresolved_dups[:3])}.",
                    "action": "Implement canonical link tags on duplicate and parameterized URL variants pointing to the single authoritative master page.",
                    "why_it_matters": "Duplicate pages without canonicals divide entity authority, dilute search rank, and risk contradictory chunk indexing by AI assistants.",
                    "confidence": "high",
                    "root_cause": "Duplicate pages are served at multiple URLs without self-referential or master canonical link tags.",
                    "affected_urls": unresolved_dups
                })

        return findings
