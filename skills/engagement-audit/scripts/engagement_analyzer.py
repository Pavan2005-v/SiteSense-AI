"""
Analyzes above-the-fold value proposition, headline hierarchy, and call-to-action (CTA) clarity.
"""
from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from skills.common.page_classifier import is_conversion_page


ACTION_CTA_PATTERNS = [
    # Commercial actions
    r"\bget\s+started\b",
    r"\bstart\s+free(?:\s+trial)?\b",
    r"\btry\s+(?:it\s+)?for\s+free\b",
    r"\bsign\s+up\b",
    r"\brequest\s+(?:a\s+)?demo\b",
    r"\bbook\s+(?:a\s+)?demo\b",
    r"\bbuy\s+now\b",
    r"\bcontact\s+sales\b",
    r"\bdownload\s+now\b",
    r"\border\s+now\b",
    r"\bview\s+pricing\b",
    r"\bcheckout\b",
    r"\bsubscribe\b",
    # Marketplace / Platform / Opportunity actions
    r"\bexplore(?:\s+opportunities|\s+competitions|\s+jobs|\s+features|\s+more)?\b",
    r"\bfind\s+(?:jobs|opportunities|internships|talent|work)\b",
    r"\bbrowse(?:\s+opportunities|\s+competitions|\s+jobs|\s+all)?\b",
    r"\bparticipate\b",
    r"\bregister(?:\s+now)?\b",
    r"\bcreate\s+profile\b",
    r"\bapply(?:\s+now)?\b",
    r"\bcompete\b",
    r"\bjoin(?:\s+now|\s+for\s+free)?\b",
    r"\bview\s+opportunities\b",
    r"\blearn\s+more\b",
    r"\blogin\b",
    r"\blog\s+in\b",
    r"\bsearch\b",
    r"\bcontact\s+us\b",
    r"\bschedule\b",
    # Developer / Tool / Open Source / Learning actions
    r"\binstall(?:\s+now|\s+cli|\s+tool|\s+extension|\s+app)?\b",
    r"\bdownload(?:\s+now|\s+for\s+\w+|\s+cli|\s+app|\s+installer|\s+free)?\b",
    r"\bquickstart\b",
    r"\bdocs\b",
    r"\bdocumentation\b",
    r"\bread\s+the\s+docs\b",
    r"\bview\s+docs\b",
    r"\bgetting\s+started\b",
    r"\bstart\s+coding\b",
    r"\bsolve\s+problems?\b",
    r"\bstart\s+solving\b",
    r"\btry\s+(?:it\s+)?out\b",
    r"\bview\s+on\s+github\b",
    r"\bcode\b"
]


def is_noisy_element(tag) -> bool:
    """
    Returns True if an interactive element is noise (accessibility skip links,
    breadcrumb navigation, announcement/security banners, logos, or generic footer links)
    rather than a candidate conversion or primary user action.
    """
    # 1. Check parent containers
    for parent in tag.parents:
        if parent.name in ("footer",):
            return True
        parent_class = " ".join(parent.get("class", [])) if isinstance(parent.get("class"), list) else str(parent.get("class") or "")
        parent_id = str(parent.get("id") or "")
        parent_role = str(parent.get("role") or "")
        parent_aria = str(parent.get("aria-label") or "")
        parent_combined = f"{parent_class} {parent_id} {parent_role} {parent_aria}".lower()

        # Breadcrumbs
        if "breadcrumb" in parent_combined:
            return True

        # Announcement / status / security banners / alerts
        if any(k in parent_combined for k in ("banner", "announcement", "alert", "notice", "notification")):
            return True

        # Cookie / privacy popups / consent
        if any(k in parent_combined for k in ("cookie", "consent", "gdpr")):
            return True

    # 2. Check element itself
    tag_class = " ".join(tag.get("class", [])) if isinstance(tag.get("class"), list) else str(tag.get("class") or "")
    tag_id = str(tag.get("id") or "")
    tag_combined = f"{tag_class} {tag_id}".lower()

    # Accessibility skip links
    text = (tag.get_text(strip=True) or tag.get("aria-label") or tag.get("title") or "").strip()
    text_lower = text.lower()
    if re.search(r"^(?:skip\s+to|jump\s+to|back\s+to\s+top|accessibility)\b", text_lower):
        return True
    if any(k in tag_combined for k in ("skip", "sr-only", "visually-hidden")):
        return True

    # Logos and home links
    href = (tag.get("href") or "").strip()
    if href in ("/", "#", "javascript:void(0)", "javascript:;", "") and len(text.split()) <= 2:
        if any(k in tag_combined for k in ("logo", "brand", "home")):
            return True

    # Security or key rotation notices in text
    if any(k in text_lower for k in ("signing key", "pgp", "security advisory", "status update", "incident")):
        return True

    return False

VAGUE_BUZZWORDS = {
    "synergy", "synergies", "paradigm", "holistic", "empower", "empowering",
    "revolutionizing", "next-generation", "world-class", "innovative", "unleash",
    "frictionless", "game-changing", "disruptive", "cutting-edge"
}


class EngagementAnalyzer:
    def __init__(self, pages: List[Any], site_type: str = "other"):
        self.pages = pages
        self.site_type = site_type

    def audit_value_proposition_and_ctas(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Homepage Value Proposition Analysis
        homepage = next((p for p in self.pages if p.page_type == "homepage"), None)
        if homepage and self.site_type != "search_portal" and not getattr(homepage, "is_spa_shell", False):
            soup = BeautifulSoup(homepage.raw_html, "html.parser")
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
            h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
            title = (homepage.title or "").strip()
            has_aria_label = bool(soup.find(attrs={"aria-label": True}) or soup.find(attrs={"role": True}))

            # ------------------------------------------------------------------
            # Context-aware homepage orientation / purpose evaluator (Phase 4).
            # A missing H1 alone is NOT a defect. The homepage is evaluated on
            # MULTIPLE INDEPENDENT orientation signals; a defect is reported only
            # when the page genuinely fails to communicate what the site is and
            # what visitors can do.
            # ------------------------------------------------------------------
            GENERIC_TITLES = {"home", "index", "welcome", "untitled", "homepage", "main", "portal", "start", "default"}
            signals: List[str] = []
            signal_details: List[str] = []

            # Signal 1: meaningful H1
            if h1s:
                signals.append("h1")
                signal_details.append(f"H1 '{h1s[0][:60]}'")

            # Signal 2: descriptive, non-generic page title (a brand-style single word is valid)
            if title and title.lower().split(":")[0].strip() not in GENERIC_TITLES and title.lower() not in GENERIC_TITLES:
                signals.append("descriptive_title")
                signal_details.append(f"title '{title[:60]}'")
            elif title:
                signal_details.append(f"generic title '{title[:30]}' (no orientation value)")

            # Signal 3: meta description with substantive content
            meta_desc = (homepage.meta_description or "").strip()
            if len(meta_desc.split()) >= 8:
                signals.append("meta_description")
                signal_details.append(f"meta description ({len(meta_desc.split())} words)")

            # Signal 4: substantive semantic heading structure (H1-H3)
            all_headings = [h.get_text(strip=True) for h in soup.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)]
            substantive_headings = [h for h in all_headings if len(h.split()) >= 3]
            if len(substantive_headings) >= 2 or any(len(h.split()) >= 5 for h in all_headings):
                signals.append("semantic_headings")
                signal_details.append(f"{len(substantive_headings)} substantive heading(s)")

            # Signal 5: search utility (broadened detection: name, type, role, form action, aria-label, id)
            is_search_utility = bool(
                soup.find("input", attrs={"name": re.compile(r"^(q|query|search|s|k|wd|search_query|sq)$", re.I)}) or
                soup.find("input", attrs={"type": "search"}) or
                soup.find("input", attrs={"aria-label": re.compile(r"search", re.I)}) or
                soup.find(attrs={"id": re.compile(r"^(q|search|searchbox|search-input|masthead-search-term)$", re.I)}) or
                soup.find("form", attrs={"role": "search"}) or
                soup.find("form", attrs={"action": re.compile(r"search", re.I)})
            )
            if is_search_utility:
                signals.append("search_utility")
                signal_details.append("search input/form")

            # Signal 6: primary navigation landmark with links
            nav_landmark = soup.find("nav") or soup.find(attrs={"role": re.compile(r"^(navigation|banner)$", re.I)}) or soup.find("header")
            nav_link_count = 0
            if nav_landmark:
                nav_links = [a for a in nav_landmark.find_all("a", href=True) if a.get_text(strip=True)]
                nav_link_count = len(nav_links)
                if nav_link_count >= 3:
                    signals.append("navigation_landmark")
                    signal_details.append(f"primary navigation with {nav_link_count} links")

            # Signal 7: substantive body text
            wc = getattr(homepage, "word_count", 0) or len((homepage.text_content or "").split())
            if wc >= 60:
                signals.append("substantive_text")
                signal_details.append(f"{wc} words of body text")

            # __B1__ and __B2__ verdict branches
            non_h1_signal_count = len([s for s in signals if s != "h1"])
            total_signal_count = len(signals)

            if not h1s:
                # Missing H1 alone is informational. A defect requires evidence that the
                # page genuinely fails to communicate purpose/orientation.
                if non_h1_signal_count == 0:
                    findings.append({
                        "issue_type": "missing_h1_heading",
                        "severity": "medium",
                        "title": "Homepage lacks orientation and purpose clarity (no H1 and no alternative orientation signals)",
                        "evidence": (
                            f"Evaluated {homepage.url} for orientation signals: no <h1> element, generic or missing page title, "
                            f"no meta description, no substantive headings, no search interface, no labelled navigation landmark, "
                            f"only {wc} words of body text, and no primary action elements. The page communicates neither what "
                            f"the site is nor what visitors can do."
                        ),
                        "action": "Add a prominent <h1> headline explicitly stating what the site offers, plus a descriptive <title> and meta description and a labelled primary navigation.",
                        "why_it_matters": "Without any headline, description, navigation, or action affordances, visitors and AI retrieval models cannot determine the purpose of the page or the site.",
                        "confidence": "high",
                        "root_cause": "Homepage template omits semantic headings, descriptive metadata, and orientation affordances.",
                        "affected_urls": [homepage.url]
                    })
                elif non_h1_signal_count <= 2:
                    # Some orientation exists but thin; H1 absence is a low-severity advisory,
                    # never a high-severity defect.
                    findings.append({
                        "issue_type": "missing_h1_heading",
                        "severity": "low",
                        "title": "Homepage lacks an H1 headline while providing limited orientation context",
                        "evidence": (
                            f"Evaluated {homepage.url}: no <h1> element found. Observed orientation signals: "
                            f"{'; '.join(signal_details) or 'none'}. The page's purpose is inferable from these signals but "
                            f"lacks a primary headline summarizing it."
                        ),
                        "action": "Add a single descriptive <h1> headline stating the site's core purpose (3-8 words) to strengthen machine and visitor orientation.",
                        "why_it_matters": "An explicit H1 gives AI retrieval models and visitors an unambiguous statement of page purpose, complementing the other orientation signals.",
                        "confidence": "high",
                        "root_cause": "Homepage template omits a primary semantic heading.",
                        "affected_urls": [homepage.url]
                    })
                # else: >= 3 independent non-H1 orientation signals -> the homepage clearly
                # communicates its purpose; a missing H1 is not reported (not a defect).
            elif total_signal_count <= 1 or (total_signal_count <= 2 and wc < 60):
                # H1 exists, but almost nothing else communicates purpose
                findings.append({
                    "issue_type": "weak_homepage_purpose_clarity",
                    "severity": "medium",
                    "title": "Homepage has a primary headline but provides weak purpose context",
                    "evidence": (
                        f"Evaluated {homepage.url}: an H1 ('{h1s[0][:60]}') is present, but the page provides almost no "
                        f"supporting orientation context (only {total_signal_count} of 10 orientation signals present, "
                        f"{wc} words of body text): "
                        f"{'; '.join(signal_details) or 'no title, no meta description, no navigation, no body text, no actions'}. "
                        f"Visitors and machine readers see a headline without context explaining what the site offers or what to do next."
                    ),
                    "action": "Add descriptive supporting context: a meta description, introductory copy under the H1, labelled navigation, and a clear primary action.",
                    "why_it_matters": "A headline without supporting context does not explain what the site is, what it offers, or what the visitor can do, leaving both users and AI models without an actionable understanding.",
                    "confidence": "high",
                    "root_cause": "Homepage renders a headline but omits descriptive metadata, navigation, and content context.",
                    "affected_urls": [homepage.url]
                })
            elif len(h1s) > 2:
                findings.append({
                    "issue_type": "multiple_competing_h1s",
                    "severity": "medium",
                    "title": f"Multiple competing H1 headlines ({len(h1s)}) dilute visual hierarchy",
                    "evidence": f"Found {len(h1s)} distinct <h1> tags on {homepage.url}: {'; '.join(h1s[:3])}.",
                    "action": "Consolidate into a single primary <h1> headline for the core value proposition, downgrading secondary sections to <h2>.",
                    "why_it_matters": "Multiple H1s create competing focal points, making it harder for visitors to parse the most critical message.",
                    "confidence": "high",
                    "root_cause": "Component-based design system incorrectly using H1s for section titles.",
                    "affected_urls": [homepage.url]
                })
            else:
                # Check for vague buzzwords without explanatory content
                h1_text = h1s[0].lower()
                words = set(re.findall(r"\b\w+\b", h1_text))
                buzzword_matches = words.intersection(VAGUE_BUZZWORDS)
                if len(buzzword_matches) >= 2 and len(words) <= 7:
                    findings.append({
                        "issue_type": "vague_buzzword_value_prop",
                        "severity": "medium",
                        "title": f"Vague corporate buzzwords in primary headline ('{h1s[0]}')",
                        "evidence": f"Homepage <h1> uses abstract buzzwords ({', '.join(buzzword_matches)}) without specifying concrete product category or utility.",
                        "action": "Rewrite the primary headline to answer: 1) What is this? 2) Who is it for? 3) What outcome does it deliver?",
                        "why_it_matters": "Vague buzzwords fail to answer the visitor's primary question ('What is this?'), resulting in lost engagement.",
                        "confidence": "medium",
                        "root_cause": "Overly conceptual copywriting lacking concrete product descriptors.",
                        "affected_urls": [homepage.url]
                    })

        # 2. CTA Verification on Key Conversion & Marketplace Pages
        conversion_pages = []
        for p in self.pages:
            # Unrendered client-side SPA shells lack static interactive elements: insufficient evidence -> suppress
            if getattr(p, "is_spa_shell", False):
                continue

            # Non-conversion pages are exempt
            if p.page_type in ("legal", "privacy", "terms", "search", "utility", "documentation", "article", "about"):
                continue

            if p.page_type in ("product_detail", "pricing", "service", "landing"):
                conversion_pages.append(p)
            elif p.page_type == "homepage":
                soup = BeautifulSoup(p.raw_html, "html.parser")
                # Search engine / utility homepage exemption (search bar is the primary action)
                is_search_utility = bool(
                    soup.find("input", attrs={"name": re.compile(r"^(q|query|search|k)$", re.I)}) or
                    soup.find("form", attrs={"role": "search"})
                )
                if is_search_utility or self.site_type in ("search_portal", "knowledge_base", "utility"):
                    continue

                # Filter out challenge/cookie error pages
                text_clean = (p.text_content or "").lower()
                if any(err in text_clean for err in ("cookies disabled", "please wait", "enable cookies")):
                    continue

                # Only require conversion CTA on homepages with explicit commercial/conversion intent
                # Exclude loose terms like "software" or "solution" which appear widely on documentation or open-source sites
                has_commercial_intent = any(kw in text_clean for kw in [
                    "pricing", "plans", "free trial", "request demo", "book demo",
                    "subscribe", "buy now", "enterprise tier", "annual billing"
                ])
                if has_commercial_intent or self.site_type in ("saas", "ecommerce"):
                    conversion_pages.append(p)

        pages_missing_cta = []
        page_evidence_details = []

        for p in conversion_pages:
            soup = BeautifulSoup(p.raw_html, "html.parser")

            # Check for terminal install command snippets on developer tool pages
            has_terminal_command = bool(
                soup.find(lambda el: el.name in ("code", "pre", "kbd") and re.search(
                    r"\b(?:brew\s+install|npm\s+(?:i|install)|pip\s+install|winget\s+install|cargo\s+install|docker\s+run|git\s+clone|curl\s+-sSL)\b",
                    el.get_text(),
                    re.I
                ))
            )

            # Collect clean interactive elements, filtering out noise (accessibility, breadcrumbs, banners, logos, footer utility)
            interactive_elements = []
            for tag in soup.find_all(["button", "a", "input", "form"]):
                if is_noisy_element(tag):
                    continue

                if tag.name == "input" and tag.get("type") in ("submit", "button", "image"):
                    interactive_elements.append(tag.get("value") or tag.get("aria-label") or "submit")
                elif tag.name == "form" and tag.get("action"):
                    action_attr = tag.get("action", "")
                    if any(k in action_attr for k in ("search", "signup", "register", "login", "checkout")):
                        interactive_elements.append(f"form:{action_attr}")
                elif tag.name in ("button", "a"):
                    text = tag.get_text(strip=True) or tag.get("aria-label") or tag.get("title") or ""
                    if text:
                        interactive_elements.append(text)

            # If homepage has minimal text (< 25 words), suppress to avoid false positives on shells/stubs
            wc = getattr(p, "word_count", 0) or len((p.text_content or "").split())
            if p.page_type == "homepage" and wc < 25 and not has_terminal_command:
                continue

            has_action_cta = has_terminal_command
            if not has_action_cta:
                for text in interactive_elements:
                    text_clean = text.lower().strip()
                    if any(re.search(pat, text_clean) for pat in ACTION_CTA_PATTERNS):
                        has_action_cta = True
                        break

            if not has_action_cta:
                pages_missing_cta.append(p.url)
                if interactive_elements:
                    sample_str = f"examined {len(interactive_elements)} interactive element(s): {', '.join(repr(b[:30]) for b in interactive_elements[:4])}"
                else:
                    sample_str = "no interactive buttons, forms, or conversion links found in DOM"
                page_evidence_details.append(f"{p.url} (intent: {p.page_type}; {sample_str})")

        if pages_missing_cta:
            evidence_text = (
                f"Evaluated {len(pages_missing_cta)} conversion page(s) with clear action intent: "
                f"{'; '.join(page_evidence_details[:3])}. "
                "None of the examined interactive elements present a clear, high-visibility conversion action "
                "(e.g., 'Get Started', 'Start Free Trial', 'Explore Opportunities', 'Register', 'Buy Now', 'Request Demo')."
            )
            # High severity requires strong evidence of commercial conversion page (e.g. pricing) with multiple elements inspected
            is_high_impact = any(p.page_type == "pricing" for p in conversion_pages if p.url in pages_missing_cta)
            findings.append({
                "issue_type": "missing_clear_cta",
                "severity": "high" if is_high_impact else "medium",
                "title": f"No clear primary Call-To-Action (CTA) on {len(pages_missing_cta)} conversion page(s)",
                "evidence": evidence_text,
                "action": "Add a prominent high-contrast CTA button above the fold guiding arriving visitors toward the primary conversion path.",
                "why_it_matters": "Without an unambiguous primary CTA, prospective customers and AI referrals face decision paralysis and bounce before converting.",
                "confidence": "high" if is_high_impact else "medium",
                "root_cause": "Missing or visually ambiguous primary conversion pathway on key marketing pages.",
                "affected_urls": pages_missing_cta
            })

        return findings
