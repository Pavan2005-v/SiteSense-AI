"""
Robots.txt checker for AI Discoverability and Machine Readability.
Analyzes access rules for standard crawlers and dedicated AI user-agents.
Operates in strict read-only compliance with the robots exclusion protocol.
A missing or empty robots.txt is NOT treated as a defect.
"""
from typing import Dict, List, Any, Tuple
import re
from urllib.parse import urljoin, urlparse


AI_USER_AGENTS = [
    "GPTBot",
    "ChatGPT-User",
    "ClaudeBot",
    "anthropic-ai",
    "Google-Extended",
    "PerplexityBot",
    "Bytespider",
    "CCBot"
]


class RobotsChecker:
    def __init__(self, base_url: str, robots_text: str = ""):
        self.base_url = base_url.rstrip("/")
        self.robots_text = robots_text.lstrip("\ufeff") if robots_text else ""
        self.rules: Dict[str, List[Dict[str, str]]] = {}
        self.sitemaps: List[str] = []
        if self.robots_text:
            self._parse_robots(self.robots_text)

    def _parse_robots(self, text: str):
        text = text.lstrip("\ufeff")
        current_agents = []
        for line in text.splitlines():
            line = line.strip()
            if not line or line.startswith("#"):
                continue

            if ":" in line:
                directive, value = line.split(":", 1)
                directive = directive.strip().lower()
                value = value.strip()

                if directive == "user-agent":
                    current_agents = [value.lower()]
                elif directive == "sitemap":
                    self.sitemaps.append(value)
                elif directive in ("disallow", "allow"):
                    for agent in current_agents:
                        if agent not in self.rules:
                            self.rules[agent] = []
                        self.rules[agent].append({"type": directive, "path": value})

    def is_allowed(self, path: str, user_agent: str = "*") -> bool:
        if not self.rules:
            return True

        ua_lower = user_agent.lower()
        applicable_rules = self.rules.get(ua_lower) or self.rules.get("*", [])

        allowed = True
        for rule in applicable_rules:
            pattern = rule["path"]
            if not pattern:  # empty disallow means allow all
                allowed = True
                continue
            # Prefix / wildcard check
            regex_pattern = re.escape(pattern).replace(r"\*", ".*")
            if re.match(f"^{regex_pattern}", path):
                allowed = (rule["type"] == "allow")
        return allowed

    def audit_ai_access(self) -> List[Dict[str, Any]]:
        """
        Produces findings for any AI crawler blocks or general crawl restrictions.
        Returns empty list if robots.txt does not exist or does not impose restrictive rules.
        """
        findings = []
        if not self.robots_text:
            return findings

        robots_url = f"{self.base_url}/robots.txt"

        # Check wildcard block
        wildcard_blocks_all = not self.is_allowed("/", "*")
        if wildcard_blocks_all:
            findings.append({
                "issue_type": "all_crawlers_blocked",
                "severity": "critical",
                "title": "All crawlers completely blocked in robots.txt",
                "evidence": "robots.txt contains 'User-agent: * Disallow: /', blocking all search engines and AI assistants from machine ingestion.",
                "action": "Allow search and AI crawlers to access public brand pages by removing 'Disallow: /' for public directories.",
                "why_it_matters": "Blocking all crawlers completely hides your site from search engines and AI assistants, destroying discoverability.",
                "confidence": "high",
                "root_cause": "A wildcard block ('Disallow: /' for '*') is present in robots.txt.",
                "affected_urls": [robots_url]
            })

        # Check AI specific bots (only when not already subsumed by universal wildcard block)
        if not wildcard_blocks_all:
            blocked_ai_bots = []
            for bot in AI_USER_AGENTS:
                if not self.is_allowed("/", bot):
                    blocked_ai_bots.append(bot)

            if blocked_ai_bots:
                if len(blocked_ai_bots) == 1:
                    bot = blocked_ai_bots[0]
                    findings.append({
                        "issue_type": "ai_crawlers_blocked",
                        "severity": "medium",
                        "title": f"An AI crawler is explicitly blocked by robots.txt ({bot})",
                        "evidence": f"robots.txt contains a Disallow directive explicitly blocking the '{bot}' user-agent from crawling the site.",
                        "action": f"If intentional to manage crawler traffic or data scraping, no change is required. If you want '{bot}' to index your public content, remove or modify the Disallow directive in robots.txt.",
                        "why_it_matters": f"Blocking '{bot}' prevents that specific bot from crawling your domain, while other search engines and AI assistants remain permitted.",
                        "confidence": "high",
                        "root_cause": f"The '{bot}' user-agent is explicitly disallowed in robots.txt.",
                        "affected_urls": [robots_url]
                    })
                else:
                    major_retrieval_bots = {"gptbot", "chatgpt-user", "claudebot", "anthropic-ai", "google-extended", "perplexitybot"}
                    has_major_bot = any(b.lower() in major_retrieval_bots for b in blocked_ai_bots)
                    findings.append({
                        "issue_type": "ai_crawlers_blocked",
                        "severity": "high" if has_major_bot else "medium",
                        "title": f"AI assistants explicitly blocked in robots.txt ({len(blocked_ai_bots)} bots)",
                        "evidence": f"Disallow rules block the following AI search user-agents from reading the site: {', '.join(blocked_ai_bots)}.",
                        "action": "Allow AI search and retrieval agents (e.g., ChatGPT-User, PerplexityBot, Google-Extended) to read public product, documentation, and about pages.",
                        "why_it_matters": "Blocking AI bots prevents conversational assistants from answering questions about your brand and products using your own authoritative content.",
                        "confidence": "high",
                        "root_cause": "Specific AI user-agents are targeted with disallow directives in robots.txt.",
                        "affected_urls": [robots_url]
                    })

        # Check critical directory disallows
        critical_paths = ["/products", "/pricing", "/about", "/services", "/docs"]
        disallowed_crit = []
        for p in critical_paths:
            if not self.is_allowed(p, "*"):
                disallowed_crit.append(p)

        if disallowed_crit and self.is_allowed("/", "*"):
            findings.append({
                "issue_type": "key_sections_disallowed",
                "severity": "high",
                "title": f"Core brand directories blocked in robots.txt: {', '.join(disallowed_crit)}",
                "evidence": f"robots.txt prevents machines from reading essential sections: {', '.join(disallowed_crit)}.",
                "action": f"Remove disallow rules on public informational directories ({', '.join(disallowed_crit)}) so AI models can ground facts about your offerings.",
                "why_it_matters": "Core business directories must be readable by AI so they can find accurate facts about products, services, and pricing.",
                "confidence": "high",
                "root_cause": "Disallow directives matching core directory paths are configured in robots.txt.",
                "affected_urls": [robots_url]
            })

        return findings
