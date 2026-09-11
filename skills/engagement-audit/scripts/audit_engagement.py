"""
Standalone audit script for engagement-audit skill.
"""
from typing import List
import argparse
import json
import sys

from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from .engagement_analyzer import EngagementAnalyzer
from .navigation_graph import NavigationGraph
from skills.crawl_render_audit.scripts.crawler import BoundedCrawler


def run_engagement_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    finding_counter = 1

    # 1. Value prop & CTA audit
    analyzer = EngagementAnalyzer(crawl_summary.pages, site_type=getattr(crawl_summary, "site_type", "other") or "other")
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
    nav_graph = NavigationGraph(crawl_summary.pages)
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
    parser = argparse.ArgumentParser(description="Audit on-site visitor engagement for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    crawler = BoundedCrawler(args.url, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_engagement_audit(summary)
    
    print(json.dumps([f.to_dict() for f in findings], indent=2))
