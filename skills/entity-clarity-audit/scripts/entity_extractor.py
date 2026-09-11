"""
Extracts brand identity signals, authoritative entity anchors, and organizational descriptions.
"""
from typing import List, Dict, Any, Optional
import re
from urllib.parse import urlparse
from bs4 import BeautifulSoup

from skills.common.page_classifier import is_legal_page

AUTHORITY_DOMAINS = [
    "wikidata.org",
    "wikipedia.org",
    "linkedin.com",
    "crunchbase.com",
    "github.com",
    "twitter.com",
    "x.com"
]


class EntityExtractor:
    def __init__(self, pages: List[Any], target_domain: str):
        self.pages = pages
        self.target_domain = target_domain.lower().replace("www.", "")
        self.brand_candidates: List[str] = []
        self.authority_profiles: List[str] = []
        self.homepage_title = ""
        self.homepage_desc = ""
        self.homepage_text_content = ""
        self._extract()

    def _extract(self):
        # 1. Candidate brand from domain name
        domain_parts = self.target_domain.split(".")
        if domain_parts:
            self.brand_candidates.append(domain_parts[0].capitalize())

        for p in self.pages:
            soup = BeautifulSoup(p.raw_html, "html.parser")
            
            # OG site_name
            og_name = soup.find("meta", attrs={"property": "og:site_name"})
            if og_name and og_name.get("content"):
                self.brand_candidates.append(og_name.get("content").strip())

            # External links for authority profiles
            for link in p.external_links:
                parsed = urlparse(link)
                netloc = parsed.netloc.lower()
                if any(auth in netloc for auth in AUTHORITY_DOMAINS):
                    if link not in self.authority_profiles:
                        self.authority_profiles.append(link)

            # Check JSON-LD sameAs
            for raw_json in p.json_ld_raw:
                try:
                    import json
                    data = json.loads(raw_json)
                    same_as = data.get("sameAs", [])
                    if isinstance(same_as, str):
                        same_as = [same_as]
                    for s in same_as:
                        if s not in self.authority_profiles:
                            self.authority_profiles.append(s)
                except Exception:
                    pass

            if p.page_type == "homepage":
                self.homepage_title = p.title or ""
                self.homepage_desc = p.meta_description or ""
                self.homepage_text_content = p.text_content or ""
