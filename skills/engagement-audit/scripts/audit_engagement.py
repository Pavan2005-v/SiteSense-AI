"""
Standalone audit script for engagement-audit skill.
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
    from .engagement_analyzer import EngagementAnalyzer
    from .navigation_graph import NavigationGraph
except (ImportError, ValueError):
    from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
    from skills.engagement_audit.scripts.navigation_graph import NavigationGraph

from skills.crawl_render_audit.scripts.crawler import BoundedCrawler


def run_engagement_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    finding_counter = 1
    site_type = getattr(crawl_summary, "site_type", "other") or "other"

    # 1. Value prop & CTA audit
    analyzer = EngagementAnalyzer(crawl_summary.pages, site_type=site_type)
    for issue in analyzer.audit_value_proposition_and_ctas():
        findings.append(AuditFinding(
            id=f"ENGAGE-{finding_counter:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="engagement",
            affected_urls=issue.get("affected_urls", []),
            detection_method="Above-the-fold value prop and CTA pattern evaluation",
            confidence=issue.get("confidence", "medium"),
            why_it_matters=issue.get("why_it_matters", ""),
            root_cause=issue.get("root_cause", "")
        ))
        finding_counter += 1

    # 2. Navigation and orientation audit
    nav_graph = NavigationGraph(crawl_summary.pages, site_type=site_type)
    for issue in nav_graph.audit_navigation_and_orientation():
        findings.append(AuditFinding(
            id=f"ENGAGE-{finding_counter:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="engagement",
            affected_urls=issue.get("affected_urls", []),
            detection_method="Internal link graph and breadcrumb orientation analysis",
            confidence=issue.get("confidence", "medium"),
            why_it_matters=issue.get("why_it_matters", ""),
            root_cause=issue.get("root_cause", "")
        ))
        finding_counter += 1

    return findings


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Audit on-site visitor engagement for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    target = args.url.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    crawler = BoundedCrawler(target, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_engagement_audit(summary)

    print(json.dumps([f.to_dict() for f in findings], indent=2))
