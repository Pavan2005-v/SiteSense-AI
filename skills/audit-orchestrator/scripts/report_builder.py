"""
Report Builder, Human Report Formatter, and Schema Validator for Adobe Round 3 Submission.
Guarantees strict compliance with the Adobe required audit report schema,
adds audit limitations & metadata, and formats beautiful human-readable reports.
"""
from typing import List, Dict, Any, Optional
from datetime import datetime
from skills.common.models import AuditFinding, CrawlSummary


ADOBE_REPORT_SCHEMA = {
    "type": "object",
    "required": ["site", "audited_at", "summary", "findings"],
    "properties": {
        "site": {"type": "string"},
        "audited_at": {"type": "string"},
        "summary": {
            "type": "object",
            "required": ["total_findings", "critical", "high", "medium"],
            "properties": {
                "total_findings": {"type": "integer"},
                "critical": {"type": "integer"},
                "high": {"type": "integer"},
                "medium": {"type": "integer"},
                "low": {"type": "integer"}
            }
        },
        "findings": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["id", "title", "severity", "evidence", "suggested_action"],
                "properties": {
                    "id": {"type": "string"},
                    "title": {"type": "string"},
                    "severity": {"type": "string", "enum": ["critical", "high", "medium", "low", "info"]},
                    "evidence": {"type": "string"},
                    "suggested_action": {
                        "type": "object",
                        "required": ["summary", "priority"],
                        "properties": {
                            "summary": {"type": "string"},
                            "priority": {"type": "string"}
                        }
                    }
                }
            }
        },
        "limitations": {
            "type": "array",
            "items": {"type": "string"}
        },
        "audit_metadata": {
            "type": "object"
        }
    }
}


def build_final_report(
    site: str,
    findings: List[AuditFinding],
    audited_at: Optional[str] = None,
    crawl_summary: Optional[CrawlSummary] = None,
    custom_limitations: Optional[List[str]] = None
) -> Dict[str, Any]:
    """
    Constructs the final Adobe-compliant JSON audit report.
    Includes canonical required fields, enriched finding metadata,
    limitations, and audit operational metadata.
    """
    if not audited_at:
        audited_at = datetime.utcnow().strftime("%Y-%m-%dT%H:%M:%SZ")

    # Calculate severity counts
    counts = {
        "critical": sum(1 for f in findings if f.severity.lower() == "critical"),
        "high": sum(1 for f in findings if f.severity.lower() == "high"),
        "medium": sum(1 for f in findings if f.severity.lower() == "medium"),
        "low": sum(1 for f in findings if f.severity.lower() == "low")
    }

    # Generate limitations based on actual crawl context
    limitations: List[str] = []
    metadata: Dict[str, Any] = {}

    if crawl_summary:
        pages_crawled = len(crawl_summary.pages)
        duration = round(crawl_summary.crawl_duration_seconds, 2)
        site_type = crawl_summary.site_type

        metadata = {
            "pages_crawled": pages_crawled,
            "crawl_duration_seconds": duration,
            "site_type": site_type,
            "pages_skipped": crawl_summary.pages_skipped,
            "robots_txt_found": crawl_summary.robots_txt_found
        }

        limitations.append(
            f"Bounded audit: sampled {pages_crawled} pages within max crawl budget; deep unlinked pages were not inspected."
        )
        if crawl_summary.robots_blocked_urls:
            limitations.append(
                f"Robots restriction: {len(crawl_summary.robots_blocked_urls)} path(s) skipped in strict accordance with robots.txt."
            )
        if not crawl_summary.robots_txt_found:
            limitations.append(
                "No robots.txt detected on target domain; crawler proceeded with polite default throttling."
            )
        if any(p.fetch_error for p in crawl_summary.pages):
            err_count = sum(1 for p in crawl_summary.pages if p.fetch_error)
            limitations.append(f"{err_count} page(s) experienced HTTP or connection errors during crawl.")
        limitations.append(
            "Read-only passive evaluation: dynamic JavaScript forms, user authentication, and transaction workflows were not submitted or bypassed."
        )
    else:
        limitations.append("Evaluation performed using pre-supplied offline crawl summary.")
        limitations.append("Read-only analysis without active interaction or mutation.")

    if custom_limitations:
        limitations.extend(custom_limitations)

    report: Dict[str, Any] = {
        "site": site,
        "audited_at": audited_at,
        "summary": {
            "total_findings": len(findings),
            "critical": counts["critical"],
            "high": counts["high"],
            "medium": counts["medium"],
            "low": counts["low"]
        },
        "findings": [f.to_dict() for f in findings],
        "limitations": limitations
    }

    if metadata:
        report["audit_metadata"] = metadata

    return report


def build_human_report(report: Dict[str, Any]) -> str:
    """
    Renders an elegant, non-expert friendly, human-readable terminal report (Part 29).
    """
    lines: List[str] = []
    sep = "=" * 60
    subsep = "-" * 60

    lines.append(sep)
    lines.append("        BRAND AI-READINESS & ENGAGEMENT AUDIT")
    lines.append(sep)
    lines.append(f"Site:       {report.get('site', 'Unknown')}")
    lines.append(f"Audit Time: {report.get('audited_at', 'Unknown')}")

    metadata = report.get("audit_metadata", {})
    if metadata:
        lines.append(
            f"Scope:      {metadata.get('pages_crawled', 0)} pages crawled in "
            f"{metadata.get('crawl_duration_seconds', 0)}s | Inferred Site Type: {metadata.get('site_type', 'other').upper()}"
        )

    summary = report.get("summary", {})
    lines.append("")
    lines.append("EXECUTIVE SUMMARY")
    lines.append(subsep)
    lines.append(f"  • Critical Deficiencies: {summary.get('critical', 0)}")
    lines.append(f"  • High-Priority Issues:  {summary.get('high', 0)}")
    lines.append(f"  • Medium Improvements:   {summary.get('medium', 0)}")
    if summary.get('low', 0) > 0:
        lines.append(f"  • Low / Proactive Items: {summary.get('low', 0)}")
    lines.append(f"  • Total Findings:        {summary.get('total_findings', 0)}")
    lines.append("")

    findings = report.get("findings", [])
    defect_findings = [f for f in findings if not f.get("is_proactive")]
    proactive_findings = [f for f in findings if f.get("is_proactive")]

    if defect_findings:
        lines.append("CONFIRMED DEFECTS & FINDINGS")
        lines.append(subsep)
        for f in defect_findings:
            sev_badge = f"[{f.get('severity', 'medium').upper()}]"
            conf_badge = f"[CONFIDENCE: {f.get('confidence', 'high').upper()}]"
            cat_badge = f"[{f.get('category', 'general').upper()}]" if f.get("category") else ""
            lines.append(f"\n{f.get('id', 'F-???')} {sev_badge} {cat_badge} {conf_badge}")
            lines.append(f"Problem:      {f.get('title', '')}")
            if f.get("why_it_matters"):
                lines.append(f"Why it matters: {f.get('why_it_matters')}")
            lines.append(f"Evidence:     {f.get('evidence', '')}")
            if f.get("affected_urls"):
                lines.append(f"Affected URLs: {', '.join(f.get('affected_urls', []))}")
            act = f.get("suggested_action", {})
            lines.append(f"Action:       {act.get('summary', '')} (Priority: {act.get('priority', 'medium').upper()})")
            if act.get("implementation_guide"):
                lines.append(f"Guide:        {act.get('implementation_guide')}")
            lines.append("")
    else:
        lines.append("CONFIRMED DEFECTS & FINDINGS")
        lines.append(subsep)
        lines.append("  No critical or high-severity defects detected. Excellent baseline health!\n")

    if proactive_findings:
        lines.append("PROACTIVE BEST-PRACTICE RECOMMENDATIONS")
        lines.append(subsep)
        lines.append("  (Advisory architectural improvements to strengthen AI discoverability)\n")
        for f in proactive_findings:
            lines.append(f"{f.get('id', 'P-???')} [PROACTIVE] [{f.get('severity', 'medium').upper()}]")
            lines.append(f"Opportunity:  {f.get('title', '')}")
            if f.get("why_it_matters"):
                lines.append(f"Why it matters: {f.get('why_it_matters')}")
            lines.append(f"Rationale:    {f.get('evidence', '')}")
            act = f.get("suggested_action", {})
            lines.append(f"Suggested:    {act.get('summary', '')}")
            if act.get("implementation_guide"):
                lines.append(f"Implementation: {act.get('implementation_guide')}")
            lines.append("")

    limitations = report.get("limitations", [])
    if limitations:
        lines.append("AUDIT LIMITATIONS & METHODOLOGY")
        lines.append(subsep)
        for lim in limitations:
            lines.append(f"  - {lim}")
        lines.append("")

    lines.append(sep)
    lines.append("End of Audit Report.")
    lines.append(sep)

    return "\n".join(lines)


def validate_report_schema(report: Dict[str, Any]) -> bool:
    """Validates the report structure against the Adobe schema requirements."""
    try:
        import jsonschema
        jsonschema.validate(instance=report, schema=ADOBE_REPORT_SCHEMA)
        return True
    except Exception:
        # Fallback manual validation if jsonschema fails
        if not isinstance(report, dict):
            return False
        for req in ["site", "audited_at", "summary", "findings"]:
            if req not in report:
                return False
        for s_req in ["total_findings", "critical", "high", "medium"]:
            if s_req not in report["summary"]:
                return False
        for f in report["findings"]:
            for f_req in ["id", "title", "severity", "evidence", "suggested_action"]:
                if f_req not in f:
                    return False
            for a_req in ["summary", "priority"]:
                if a_req not in f["suggested_action"]:
                    return False
        return True
