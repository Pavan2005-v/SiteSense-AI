"""
Analyzes above-the-fold value proposition, headline hierarchy, and call-to-action (CTA) clarity.
"""
from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from skills.common.page_classifier import is_conversion_page


ACTION_CTA_PATTERNS = [
    r"get\s+started",
    r"start\s+free\s+trial",
    r"try\s+for\s+free",
    r"sign\s+up",
    r"request\s+demo",
    r"book\s+a\s+demo",
    r"buy\s+now",
    r"contact\s+sales",
    r"download\s+now",
    r"explore\s+features",
    r"order\s+now",
    r"view\s+pricing"
]

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
        if homepage and self.site_type != "search_portal":
            soup = BeautifulSoup(homepage.raw_html, "html.parser")
            h1s = [h.get_text(strip=True) for h in soup.find_all("h1") if h.get_text(strip=True)]
            h2s = [h.get_text(strip=True) for h in soup.find_all("h2") if h.get_text(strip=True)]
            title = (homepage.title or "").strip()
            has_aria_label = bool(soup.find(attrs={"aria-label": True}) or soup.find(attrs={"role": True}))

            if not h1s:
                # Check for search utility interface (search bar conveys unmistakable purpose)
                is_search_utility = bool(
                    soup.find("input", attrs={"name": re.compile(r"^(q|query|search|k|wd)$", re.I)}) or
                    soup.find("form", attrs={"role": "search"})
                )

                # Purpose clarity evaluation
                has_clear_purpose = bool(
                    is_search_utility or
                    (h2s and any(len(h.split()) >= 3 for h in h2s)) or
                    (title and title.lower() not in ("home", "index", "welcome", "untitled") and len(title.split()) >= 2)
                )

                # Only emit finding if purpose is genuinely ambiguous and lacks semantic orientation
                if not has_clear_purpose:
                    findings.append({
                        "issue_type": "missing_h1_heading",
                        "severity": "high",
                        "title": "Homepage lacks orientation and purpose clarity (no H1 or clear semantic structure)",
                        "evidence": f"No <h1> element found on {homepage.url}, and no descriptive title or clear H2 tags provide context for arriving visitors or AI agents.",
                        "action": "Add a prominent <h1> headline explicitly stating what your product or service accomplishes within 3-8 words.",
                        "why_it_matters": "Without a clear primary headline or semantic structure, visitors and AI retrieval models struggle to immediately understand what the organization offers.",
                        "confidence": "medium",
                        "root_cause": "Visual design omitted semantic heading hierarchy and clear textual purpose statement.",
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

        # 2. CTA Verification on Key Conversion Pages
        conversion_pages = []
        for p in self.pages:
            if p.page_type in ("product_detail", "pricing", "service", "landing"):
                conversion_pages.append(p)
            elif p.page_type == "homepage":
                soup = BeautifulSoup(p.raw_html, "html.parser")
                # Search engine / utility homepage exemption (search bar is the primary action)
                is_search_utility = bool(
                    soup.find("input", attrs={"name": re.compile(r"^(q|query|search|k)$", re.I)}) or
                    soup.find("form", attrs={"role": "search"})
                )
                if is_search_utility or self.site_type == "search_portal":
                    continue

                # Only require conversion CTA on homepages with commercial/conversion intent
                text_lower = (p.text_content or "").lower()
                has_commercial_intent = any(kw in text_lower for kw in [
                    "pricing", "plans", "software", "platform", "solution", "services",
                    "demo", "trial", "subscribe", "buy", "features", "offering"
                ])
                if has_commercial_intent:
                    conversion_pages.append(p)

        pages_missing_cta = []
        page_evidence_details = []

        for p in conversion_pages:
            soup = BeautifulSoup(p.raw_html, "html.parser")
            # Collect button texts and anchor texts
            buttons = [b.get_text(strip=True) for b in soup.find_all(["button", "a"]) if b.get_text(strip=True)]
            # Filter out tiny or navigation generic words
            meaningful_buttons = [b for b in buttons if len(b.split()) <= 6][:6]
            
            has_action_cta = False
            for text in buttons:
                text_clean = text.lower()
                if any(re.search(pat, text_clean) for pat in ACTION_CTA_PATTERNS):
                    has_action_cta = True
                    break

            if not has_action_cta:
                pages_missing_cta.append(p.url)
                sample_str = f"examined buttons/links: {', '.join(repr(b) for b in meaningful_buttons[:4])}" if meaningful_buttons else "no interactive buttons found"
                page_evidence_details.append(f"{p.url} (intent: {p.page_type}; {sample_str})")

        if pages_missing_cta:
            evidence_text = (
                f"Evaluated {len(pages_missing_cta)} conversion page(s) with commercial intent: "
                f"{'; '.join(page_evidence_details[:3])}. "
                "None of the examined interactive elements present a clear, high-visibility conversion action "
                "(e.g., 'Get Started', 'Start Free Trial', 'Buy Now', 'Request Demo')."
            )
            findings.append({
                "issue_type": "missing_clear_cta",
                "severity": "high",
                "title": f"No clear primary Call-To-Action (CTA) on {len(pages_missing_cta)} conversion page(s)",
                "evidence": evidence_text,
                "action": "Add a prominent high-contrast CTA button above the fold guiding arriving visitors toward the primary conversion path.",
                "why_it_matters": "Without an unambiguous primary CTA, prospective customers and AI referrals face decision paralysis and bounce before converting.",
                "confidence": "high",
                "root_cause": "Missing or visually ambiguous primary conversion pathway on key marketing pages.",
                "affected_urls": pages_missing_cta
            })

        return findings
