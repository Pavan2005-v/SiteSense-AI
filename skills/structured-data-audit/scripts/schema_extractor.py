"""
Extracts and parses JSON-LD and Microdata structured data from HTML documents.
Detects malformed JSON syntax and extracts all embedded schema objects.
"""
from typing import List, Dict, Any, Tuple
import json
import re
from bs4 import BeautifulSoup


class SchemaExtractor:
    def __init__(self, html: str, url: str = ""):
        self.html = html
        self.url = url
        self.raw_blocks: List[str] = []
        self.parsed_schemas: List[Dict[str, Any]] = []
        self.syntax_errors: List[Dict[str, str]] = []
        self._extract()

    def _extract(self):
        soup = BeautifulSoup(self.html, "html.parser")
        script_tags = soup.find_all("script", type="application/ld+json")
        for tag in script_tags:
            raw_text = tag.string or tag.get_text() or ""
            raw_text = raw_text.strip()
            if not raw_text:
                continue
            self.raw_blocks.append(raw_text)

            try:
                data = json.loads(raw_text)
                self._collect_objects(data)
            except Exception as e:
                # Capture exact syntax error
                snippet = raw_text[:120] + ("..." if len(raw_text) > 120 else "")
                self.syntax_errors.append({
                    "url": self.url,
                    "error": str(e),
                    "snippet": snippet
                })

    def _collect_objects(self, data: Any):
        if isinstance(data, list):
            for item in data:
                self._collect_objects(item)
        elif isinstance(data, dict):
            # Check for @graph
            if "@graph" in data and isinstance(data["@graph"], list):
                for item in data["@graph"]:
                    self._collect_objects(item)
            else:
                self.parsed_schemas.append(data)

    def get_schemas_by_type(self, schema_type: str) -> List[Dict[str, Any]]:
        target = schema_type.lower()
        results = []
        for s in self.parsed_schemas:
            t = s.get("@type", "")
            if isinstance(t, list):
                types = [str(x).lower() for x in t]
            else:
                types = [str(t).lower()]
            if any(target == item or target in item for item in types):
                results.append(s)
        return results

