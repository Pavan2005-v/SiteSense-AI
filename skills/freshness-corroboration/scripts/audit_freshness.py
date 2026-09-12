"""
Standalone audit script for freshness-corroboration skill.
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
    from .corroboration_checker import CorroborationChecker
except (ImportError, ValueError):
    from skills.freshness_corroboration.scripts.corroboration_checker import CorroborationChecker

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
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Audit freshness and corroboration for a website")
    parser.add_argument("--url", required=True, help="Target URL or domain")
    parser.add_argument("--max-pages", type=int, default=10, help="Max pages to crawl")
    args = parser.parse_args()

    target = args.url.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    crawler = BoundedCrawler(target, max_pages=args.max_pages)
    summary = crawler.crawl()
    findings = run_freshness_corroboration_audit(summary)
    
    print(json.dumps([f.to_dict() for f in findings], indent=2))
