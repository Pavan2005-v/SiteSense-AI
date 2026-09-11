#!/usr/bin/env python3
"""
Root CLI entrypoint for Brand AI-Readiness and Engagement Audit.
Invokes the audit-orchestrator entrypoint skill.
"""
import sys
import os
import argparse
import json

# Ensure marketplace root is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skills
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator


def main():
    parser = argparse.ArgumentParser(
        description="Adobe University Hackathon 2026 - Brand AI-Readiness & Engagement Audit Marketplace"
    )
    parser.add_argument("--url", required=True, help="Target website URL or domain (e.g., https://example.com)")
    parser.add_argument("--max-pages", type=int, default=12, help="Maximum pages to crawl (default: 12)")
    parser.add_argument("--format", choices=["json", "report"], default="json", help="Output format: json (default) or report (human-readable)")
    parser.add_argument("--output", "-o", help="Path to save output report file")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON output")

    args = parser.parse_args()

    orchestrator = AuditOrchestrator(args.url, max_pages=args.max_pages)
    report = orchestrator.run_full_audit()

    if args.format == "report":
        from skills.audit_orchestrator.scripts.report_builder import build_human_report
        output_content = build_human_report(report)
    else:
        indent = 2 if args.pretty else None
        output_content = json.dumps(report, indent=indent)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(output_content)
        print(f"Audit complete. Report saved to: {args.output}")
    else:
        print(output_content)


if __name__ == "__main__":
    main()

