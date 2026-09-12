#!/usr/bin/env python3
"""
Root CLI entrypoint for Brand AI-Readiness and Engagement Audit.
Invokes the audit-orchestrator entrypoint skill.
"""
import sys
import os
import argparse
import json

# Force UTF-8 stdout on platforms like Windows to prevent charmap encoding errors
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

# Ensure marketplace root is on python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import skills
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator
from skills.common.url_utils import is_safe_url


def main():
    parser = argparse.ArgumentParser(
        description="Adobe University Hackathon 2026 - Brand AI-Readiness & Engagement Audit Marketplace"
    )
    parser.add_argument("--url", required=True, help="Target website URL or domain (e.g., https://example.com)")
    parser.add_argument("--max-pages", type=int, default=12, help="Maximum pages to crawl (default: 12)")
    parser.add_argument("--format", choices=["json", "report"], default="json", help="Output format: json (default) or report (human-readable)")
    parser.add_argument("--output", "-o", help="Path to save output report file")
    parser.add_argument("--pretty", action="store_true", default=True, help="Pretty-print JSON output")
    parser.add_argument("--debug", action="store_true", help="Enable internal evidence debug mode and diagnostic trace")

    args = parser.parse_args()

    target = args.url.strip()
    if not target.startswith("http://") and not target.startswith("https://"):
        target = "https://" + target

    if not is_safe_url(target):
        sys.stderr.write(f"Error: Invalid or restricted target URL: {args.url}\n")
        sys.exit(1)

    try:
        orchestrator = AuditOrchestrator(target, max_pages=args.max_pages, debug=args.debug)
        report = orchestrator.run_full_audit()

        if args.format == "report":
            from skills.audit_orchestrator.scripts.report_builder import build_human_report
            output_content = build_human_report(report)
        else:
            indent = 2 if args.pretty else None
            output_content = json.dumps(report, indent=indent, ensure_ascii=False)

        if args.output:
            with open(args.output, "w", encoding="utf-8") as f:
                f.write(output_content)
            print(f"Audit complete. Report saved to: {args.output}")
        else:
            print(output_content)

    except Exception as e:
        sys.stderr.write(f"Audit failed with error: {str(e)}\n")
        sys.exit(1)


if __name__ == "__main__":
    main()
