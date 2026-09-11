"""
Standalone audit script for crawl-render-audit skill.
"""
from typing import List
import argparse
import json
import sys

from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from .robots_checker import RobotsChecker
from .render_comparator import RenderComparator
from .crawler import BoundedCrawler


def run_crawl_render_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    finding_counter = 1

    # 1. Robots.txt audit
    checker = RobotsChecker(crawl_summary.start_url, crawl_summary.robots_txt_content)
    raw_robots_issues = checker.audit_ai_access()
    for issue in raw_robots_issues:
        finding = AuditFinding(
            id=f"CRAWL-{finding_counter:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="crawlability",
            confidence=issue.get("confidence", "high"),
            why_it_matters=issue.get("why_it_matters"),
            root_cause=issue.get("root_cause"),
            affected_urls=issue.get("affected_urls", []),
            detection_method="robots.txt inspection",
            is_proactive=False
        )
        findings.append(finding)
        finding_counter += 1

    # 2. Render gaps and DOM vs HTML
    comparator = RenderComparator(crawl_summary.pages)
    render_issues = comparator.audit_render_gaps()
    for issue in render_issues:
        detection_method = "HTML DOM vs text extraction"
        if issue["issue_type"] == "meta_noindex_detected":
            detection_method = "HTML meta robots tag analysis"
        elif issue["issue_type"] == "missing_canonical_tags":
            detection_method = "Canonical tag and URL variant analysis"
        elif issue["issue_type"] == "js_render_gap":
            detection_method = "HTML source vs rendered content analysis"
        elif issue["issue_type"] == "facts_locked_in_images":
            detection_method = "Image alt attribute audit"
            
        finding = AuditFinding(
            id=f"CRAWL-{finding_counter:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="rendering" if "js" in issue["issue_type"] else "machine-readability",
            confidence=issue.get("confidence", "high"),
            why_it_matters=issue.get("why_it_matters"),
            root_cause=issue.get("root_cause"),
            affected_urls=issue.get("affected_urls", []),
            detection_method=detection_method,
            is_proactive=False
        )
        findings.append(finding)
        finding_counter += 1

    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit crawlability and rendering for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    crawler = BoundedCrawler(args.url, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_crawl_render_audit(summary)
    
    print(json.dumps([f.to_dict() for f in findings], indent=2))
