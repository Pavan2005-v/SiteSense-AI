"""
Analyzes cross-page factual consistency, stale temporal claims, and claim fragility.
"""
from typing import List, Dict, Any, Optional
import re
from datetime import datetime
from .temporal_extractor import TemporalExtractor, CURRENT_YEAR


class CorroborationChecker:
    def __init__(self, pages: List[Any]):
        self.pages = pages

    def audit_freshness_and_consistency(self) -> List[Dict[str, Any]]:
        findings = []

        # 1. Stale Copyright Check
        copyright_years = {}
        for p in self.pages:
            extractor = TemporalExtractor(p.raw_html, p.url)
            year = extractor.get_copyright_year()
            if year:
                copyright_years[p.url] = year

        if copyright_years:
            max_year = max(copyright_years.values())
            # If the newest copyright year on the site is 2 or more years behind current year
            if max_year <= CURRENT_YEAR - 2:
                sample_urls = [f"{u} (shows {yr})" for u, yr in list(copyright_years.items())[:3]]
                urls = list(copyright_years.keys())
                findings.append({
                    "issue_type": "stale_copyright",
                    "severity": "medium",
                    "title": f"Stale copyright notice ({max_year}) indicates outdated site maintenance",
                    "evidence": f"Copyright notices across sampled pages display {max_year} (current year: {CURRENT_YEAR}). Sample pages: {'; '.join(sample_urls)}.",
                    "action": f"Update the site-wide footer copyright to {CURRENT_YEAR} (or use dynamic server-side current year) to signal active maintenance to AI web crawlers.",
                    "affected_urls": urls,
                    "confidence": "medium",
                    "why_it_matters": "A stale copyright year can lead AI crawlers to believe the entire domain's content is unmaintained.",
                    "root_cause": "Hardcoded copyright year in the global footer template."
                })

        # 2. Stale Roadmap / Historical Future Offerings
        all_stale_roadmaps = []
        for p in self.pages:
            extractor = TemporalExtractor(p.raw_html, p.url)
            items = extractor.get_roadmap_mentions()
            all_stale_roadmaps.extend(items)

        if all_stale_roadmaps:
            sample = all_stale_roadmaps[0]
            urls = list(set([item["url"] for item in all_stale_roadmaps]))
            findings.append({
                "issue_type": "stale_roadmap",
                "severity": "high",
                "title": f"Expired temporal commitments / roadmap claims ({sample['phrase']})",
                "evidence": f"Found references to past years presented as upcoming roadmap commitments on {sample['url']}: '{sample['phrase']}'.",
                "action": "Audit and update product roadmap and feature release announcements to reflect current product milestones.",
                "affected_urls": urls,
                "confidence": "high",
                "why_it_matters": "Promising old features as 'upcoming' degrades user trust and leads AI assistants to output incorrect timelines.",
                "root_cause": "Abandoned or unmaintained product roadmap/update pages."
            })

        # 3. Cross-Page Pricing Consistency
        # Extract dollar pricing claims from homepage vs pricing/product pages
        pricing_by_page = {}
        for p in self.pages:
            text = p.text_content or ""
            # Look for starting at $X or plans starting at $X
            matches = re.findall(r"(?:starting\s+at|plans\s+from|from|as\s+low\s+as)\s*\$\s*(\d+)", text, re.I)
            if matches:
                pricing_by_page[p.url] = set(int(m) for m in matches)

        if len(pricing_by_page) >= 2:
            all_claimed_starts = set()
            for urls_group, prices in pricing_by_page.items():
                all_claimed_starts.update(prices)
            # If multiple divergent starting prices exist
            if len(all_claimed_starts) > 1 and max(all_claimed_starts) > min(all_claimed_starts) * 1.3:
                details = [f"{u}: ${min(p)}" for u, p in pricing_by_page.items()]
                urls = list(pricing_by_page.keys())
                findings.append({
                    "issue_type": "conflicting_pricing_claims",
                    "severity": "high",
                    "title": "Inconsistent pricing claims across internal pages",
                    "evidence": f"Detected contradictory starting price figures across pages: {'; '.join(details)}.",
                    "action": "Standardize pricing references across the homepage, pricing table, and promotional banners to prevent AI agents from quoting conflicting prices.",
                    "affected_urls": urls,
                    "confidence": "high",
                    "why_it_matters": "Conflicting price numbers confuse AI agents and lead them to hallucinate or present incorrect pricing to the user.",
                    "root_cause": "Disjointed updates to pricing text across multiple promotional pages."
                })

        # 4. Fragile Uncorroborated Superlative Claims
        fragile_claims = []
        for p in self.pages:
            text = p.text_content or ""
            matches = re.findall(r"(?:the\s+)?#1\s+[\w\s]{3,25}|(?:voted|rated)\s+(?:best|#1)[\w\s]{0,20}|(?:trusted\s+by\s+over\s+\d+[\w\s]{0,15})", text, re.I)
            for m in matches:
                # Check if there is an accompanying citation or external link nearby
                if not any(ext in p.external_links for ext in ["g2.com", "capterra.com", "trustpilot.com", "gartner.com", "forrester.com"]):
                    fragile_claims.append((p.url, m.strip()))

        if fragile_claims:
            sample_claim = fragile_claims[0]
            urls = list(set([u for u, c in fragile_claims]))
            findings.append({
                "issue_type": "uncorroborated_superlative_claim",
                "severity": "medium",
                "title": f"Uncorroborated brand claim without third-party citation ('{sample_claim[1][:40]}')",
                "evidence": f"Claim '{sample_claim[1]}' appears on {sample_claim[0]} without verifiable third-party citation, audit link, or methodology.",
                "action": "Add explicit third-party citation links, survey dates, or audit source references to substantiate superlative marketing claims for AI citation.",
                "affected_urls": urls,
                "confidence": "low",
                "why_it_matters": "AI assistants often discount or caveat superlative claims unless they are backed by verifiable third-party sources.",
                "root_cause": "Marketing copy lacks external citations or references."
            })

        return findings
