"""
Standalone audit script for entity-clarity-audit skill.
"""
from pathlib import Path
from typing import List
import argparse
import json
import sys

# Ensure project root is in sys.path when executed directly as a script
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import skills
from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary

try:
    from .disambiguation_rules import DisambiguationRules
except (ImportError, ValueError):
    from skills.entity_clarity_audit.scripts.disambiguation_rules import DisambiguationRules

from skills.crawl_render_audit.scripts.crawler import BoundedCrawler


def run_entity_clarity_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    checker = DisambiguationRules(
        crawl_summary.pages,
        crawl_summary.target_domain,
        site_type=getattr(crawl_summary, "site_type", "other")
    )
    raw_issues = checker.audit_entity_clarity()

    for idx, issue in enumerate(raw_issues, 1):
        findings.append(AuditFinding(
            id=f"ENTITY-{idx:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="entity-clarity",
            affected_urls=issue.get("affected_urls", []),
            detection_method="Brand disambiguation and knowledge-graph anchor heuristic analysis",
            confidence=issue.get("confidence", "medium"),
            why_it_matters=issue.get("why_it_matters", ""),
            root_cause=issue.get("root_cause", "")
        ))

    return findings


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Audit entity clarity and brand disambiguation for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    target = args.url.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    crawler = BoundedCrawler(target, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_entity_clarity_audit(summary)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
