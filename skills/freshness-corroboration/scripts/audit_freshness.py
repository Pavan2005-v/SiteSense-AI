"""
Standalone audit script for freshness-corroboration skill.
"""
from typing import List
import argparse
import json
import sys

from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from .corroboration_checker import CorroborationChecker
from skills.crawl_render_audit.scripts.crawler import BoundedCrawler


def run_freshness_corroboration_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    checker = CorroborationChecker(crawl_summary.pages)
    raw_issues = checker.audit_freshness_and_consistency()

    for idx, issue in enumerate(raw_issues, 1):
        severity = issue["severity"]
        confidence = issue.get("confidence", "low")
        evidence = issue["evidence"]
        
        if confidence == "low" and severity in ["high", "critical"]:
            severity = "medium"
            evidence += " Note: This is an advisory observation due to low confidence."
        elif confidence == "low":
            evidence += " Note: This is an advisory observation due to low confidence."

        findings.append(AuditFinding(
            id=f"FRESH-{idx:03d}",
            title=issue["title"],
            severity=severity,
            evidence=evidence,
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=severity
            ),
            category="freshness",
            affected_urls=issue.get("affected_urls", []),
            detection_method="Temporal extraction and cross-page factual consistency check",
            confidence=confidence,
            why_it_matters=issue.get("why_it_matters", ""),
            root_cause=issue.get("root_cause", "")
        ))

    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit freshness and corroboration for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    crawler = BoundedCrawler(args.url, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_freshness_corroboration_audit(summary)
    
    print(json.dumps([f.to_dict() for f in findings], indent=2))
