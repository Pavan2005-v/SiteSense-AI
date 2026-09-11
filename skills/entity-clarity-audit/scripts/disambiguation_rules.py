"""
Evaluates brand ambiguity, entity linking anchors, and organizational clarity.
"""
from typing import List, Dict, Any, Optional
import re
from bs4 import BeautifulSoup
from .entity_extractor import EntityExtractor


COMMON_DICTIONARY_WORDS = {
    "canvas", "focus", "apex", "echo", "flow", "pulse", "beacon", "stride",
    "shift", "spark", "prime", "nexus", "prism", "swift", "nova", "craft"
}


class DisambiguationRules:
    def __init__(self, pages: List[Any], target_domain: str):
        self.pages = pages
        self.target_domain = target_domain
        self.extractor = EntityExtractor(pages, target_domain)

    def audit_entity_clarity(self) -> List[Dict[str, Any]]:
        findings = []
        brand = self.extractor.brand_candidates[0] if self.extractor.brand_candidates else self.target_domain

        # 1. Missing Brand Name in Page Titles
        unbranded_titles = []
        for p in self.pages:
            title = (p.title or "").strip()
            if not title:
                unbranded_titles.append(p.url)
            elif brand.lower() not in title.lower() and len(title.split()) <= 2:
                unbranded_titles.append(p.url)

        if len(unbranded_titles) > len(self.pages) * 0.4 and len(self.pages) >= 2:
            findings.append({
                "issue_type": "unbranded_page_titles",
                "severity": "medium",
                "title": f"Generic or unbranded page titles across {len(unbranded_titles)} page(s)",
                "evidence": f"Pages lack brand name anchors in <title>, causing entity attribution loss in AI search snippets.",
                "action": f"Append the brand name (e.g. '| {brand}') to all page titles to ensure AI context windows correctly associate page facts with the brand entity.",
                "why_it_matters": "LLMs rely heavily on page titles for entity attribution. Generic titles can cause them to incorrectly attribute content to generic concepts instead of your brand.",
                "confidence": "medium",
                "root_cause": "Missing brand identifier in page title templates.",
                "affected_urls": unbranded_titles
            })

        # 2. Missing Authoritative Entity Links (sameAs Profiles)
        if not self.extractor.authority_profiles:
            findings.append({
                "issue_type": "missing_authority_links",
                "severity": "medium",
                "title": "No authoritative entity profile links (Wikidata, LinkedIn, Crunchbase)",
                "evidence": f"No verified external organization profile links found in structured data or header/footer across {self.target_domain}.",
                "action": "Link your official Wikidata, LinkedIn, and Crunchbase profiles in an Organization 'sameAs' array to anchor your entity in LLM knowledge graphs.",
                "why_it_matters": "Authoritative profiles help LLMs definitively map a brand to a real-world entity, reducing hallucination risk.",
                "confidence": "medium",
                "root_cause": "Omission of structured knowledge-graph linking or social profile links.",
                "affected_urls": [self.target_domain]
            })

        # 3. High Risk of Entity Collision (Common Word Brand without explicit industry qualifying tag)
        brand_clean = brand.lower().replace("-", "").replace("_", "")
        if brand_clean in COMMON_DICTIONARY_WORDS:
            # Check if homepage title contains sector context
            hp_title = self.extractor.homepage_title.lower()
            hp_desc = self.extractor.homepage_desc.lower()
            industry_kws = ["software", "platform", "agency", "logistics", "ai", "consulting", "app", "service", "tools", "technology", "solutions"]
            
            has_context = False
            if len(hp_title.split()) > 3 and any(kw in hp_title for kw in industry_kws):
                has_context = True
            elif any(kw in hp_desc for kw in industry_kws):
                has_context = True
                
            if not has_context:
                findings.append({
                    "issue_type": "brand_entity_collision_risk",
                    "severity": "medium",
                    "title": f"Entity collision risk for brand name '{brand}'",
                    "evidence": f"The brand name '{brand}' is a common dictionary term, and page titles/meta descriptions do not include explicit categorical descriptors to differentiate it from the generic term.",
                    "action": f"Disambiguate the brand by appending sector descriptors across primary titles and metadata (e.g., '{brand} - Enterprise Workflow Platform').",
                    "why_it_matters": "When a brand name is a common noun, LLMs may conflate the brand with the dictionary definition unless strong contextual signals are present.",
                    "confidence": "medium",
                    "root_cause": "Use of common dictionary word for brand name without contextual disambiguation in core metadata.",
                    "affected_urls": [p.url for p in self.pages if p.page_type == "homepage"]
                })

        # 4. Unclear Entity Value / Mission on Homepage
        homepage = next((p for p in self.pages if p.page_type == "homepage"), None)
        if homepage:
            soup = BeautifulSoup(homepage.raw_html or "", "html.parser")
            title_text = (homepage.title or "").strip()
            desc_text = (homepage.meta_description or "").strip()
            
            headings = soup.find_all(["h1", "h2"])
            heading_text = " ".join([h.get_text(separator=" ", strip=True) for h in headings])
            
            body_text = (self.extractor.homepage_text_content or "").strip()
            
            # Check if all are essentially empty or non-descriptive
            has_title_desc = len(title_text.split()) > 3 or len(desc_text.split()) > 5
            has_headings = len(heading_text.split()) > 5
            has_body = len(body_text.split()) >= 30
            
            if not has_title_desc and not has_headings and not has_body:
                findings.append({
                    "issue_type": "homepage_lacks_substantive_entity_description",
                    "severity": "high",
                    "title": "Homepage lacks clear machine-extractable entity description",
                    "evidence": "Homepage lacks a descriptive title, meta description, meaningful H1/H2 tags, and sufficient body text to explain the organization's purpose.",
                    "action": "Add an explicit introductory summary (1-2 sentences) clearly declaring what your company does and who it serves using standard headings and text.",
                    "why_it_matters": "Without explicit, parsable text explaining your value proposition, AI agents cannot reliably understand or summarize your organization's core purpose.",
                    "confidence": "high",
                    "root_cause": "Homepage relies too heavily on images, client-side rendering without fallback, or simply lacks descriptive copy.",
                    "affected_urls": [homepage.url]
                })

        return findings
