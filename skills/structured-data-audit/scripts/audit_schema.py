"""
Standalone audit script for structured-data-audit skill.
"""
from typing import List
import argparse
import json
import sys

from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from .schema_validator import SchemaValidator
from skills.crawl_render_audit.scripts.crawler import BoundedCrawler


def run_structured_data_audit(crawl_summary: CrawlSummary) -> List[AuditFinding]:
    findings: List[AuditFinding] = []
    validator = SchemaValidator(crawl_summary.pages, site_type=getattr(crawl_summary, 'site_type', 'other'))
    raw_issues = validator.audit_all_pages()

    for idx, issue in enumerate(raw_issues, 1):
        findings.append(AuditFinding(
            id=f"SCHEMA-{idx:03d}",
            title=issue["title"],
            severity=issue["severity"],
            evidence=issue["evidence"],
            suggested_action=SuggestedAction(
                summary=issue["action"],
                priority=issue["severity"]
            ),
            category="structured-data",
            affected_urls=issue.get("affected_urls", []),
            detection_method="JSON-LD & Microdata syntax/schema verification",
            confidence=issue.get("confidence", "low"),
            why_it_matters=issue.get("why_it_matters", ""),
            root_cause=issue.get("root_cause", "")
        ))

    return findings


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Audit structured data and Schema.org for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    crawler = BoundedCrawler(args.url, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_structured_data_audit(summary)
    
    print(json.dumps([f.to_dict() for f in findings], indent=2))
