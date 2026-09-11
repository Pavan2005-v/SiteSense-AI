"""
Extracts temporal markers, copyright years, publication dates, and roadmap timelines from web pages.
"""
from typing import List, Dict, Any, Optional, Tuple
import re
from datetime import datetime
from bs4 import BeautifulSoup


CURRENT_YEAR = datetime.now().year


class TemporalExtractor:
    def __init__(self, html: str, url: str = ""):
        self.html = html
        self.url = url
        self.soup = BeautifulSoup(html, "html.parser")

    def get_copyright_year(self) -> Optional[int]:
        text = self.soup.get_text()
        # Look for patterns like © 2022 or Copyright 2018-2021
        matches = re.findall(r"(?:©|copyright|\(c\))\s*(?:[12]\d{3}\s*[-–]\s*)?([12]\d{3})", text, re.I)
        if matches:
            years = [int(m) for m in matches if 1995 <= int(m) <= CURRENT_YEAR + 1]
            if years:
                return max(years)
        return None

    def get_roadmap_mentions(self) -> List[Dict[str, Any]]:
        """Detects references to past years framed as future roadmap/upcoming items."""
        stale_roadmaps = []
        text = self.soup.get_text()
        
        # Look for "Upcoming in 202X", "Roadmap 202X", "Expected Q3 202X"
        pattern = r"(?:roadmap|upcoming|coming\s+in|planned\s+for|launching\s+in|q[1-4]\s+)\s*([12]\d{3})"
        matches = re.finditer(pattern, text, re.I)
        for m in matches:
            year = int(m.group(1))
            if year < CURRENT_YEAR - 1:
                stale_roadmaps.append({
                    "phrase": m.group(0),
                    "year": year,
                    "url": self.url
                })
        return stale_roadmaps

    def get_published_and_modified_dates(self) -> Dict[str, Optional[str]]:
        res = {"datePublished": None, "dateModified": None}
        
        # Meta tags
        meta_pub = self.soup.find("meta", attrs={"property": re.compile(r"article:published_time|datePublished", re.I)})
        if meta_pub:
            res["datePublished"] = meta_pub.get("content")

        meta_mod = self.soup.find("meta", attrs={"property": re.compile(r"article:modified_time|dateModified", re.I)})
        if meta_mod:
            res["dateModified"] = meta_mod.get("content")

        # Time tags
        time_tag = self.soup.find("time")
        if time_tag and time_tag.get("datetime"):
            if not res["datePublished"]:
                res["datePublished"] = time_tag["datetime"]

        return res

