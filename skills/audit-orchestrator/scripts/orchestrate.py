"""
Main Entrypoint Orchestrator for Brand AI-Readiness and Engagement Audit.
Coordinates specialist skills, validates evidence integrity, executes root-cause deduplication,
applies confidence gating, injects site-appropriate proactive recommendations,
and generates the final Adobe Round 3 report.
"""
from typing import List, Dict, Any, Optional, Set
import argparse
import json
import re
import sys
from urllib.parse import urlparse

from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from skills.common.url_utils import normalize_url, dedupe_urls, urls_belong_to_domain
from skills.common.site_classifier import classify_site
from skills.crawl_render_audit.scripts.crawler import BoundedCrawler
from skills.crawl_render_audit.scripts.audit_crawl import run_crawl_render_audit
from skills.structured_data_audit.scripts.audit_schema import run_structured_data_audit
from skills.freshness_corroboration.scripts.audit_freshness import run_freshness_corroboration_audit
from skills.entity_clarity_audit.scripts.audit_entity import run_entity_clarity_audit
from skills.engagement_audit.scripts.audit_engagement import run_engagement_audit
from .report_builder import build_final_report, build_human_report, validate_report_schema
from skills.common.applicability_engine import is_rule_applicable

SEVERITY_ORDER = {"critical": 3, "high": 2, "medium": 1, "low": 0, "info": 0}


def sync_title_page_count(title: str, count: int) -> str:
    """
    Auto-synchronizes counts in finding titles (e.g. 'on 1 page(s)' or 'on 2 conversion page(s)')
    with the exact number of inspected affected URLs.
    """
    pattern = r'\b(\d+)\s+((?:[a-zA-Z_-]+\s+)?pages?(?:\(s\))?)'
    def repl(match):
        raw_qualifier = match.group(2)
        normalized_qualifier = re.sub(r'pages?(?:\(s\))?', 'page(s)', raw_qualifier, flags=re.IGNORECASE)
        return f"{count} {normalized_qualifier}"
    return re.sub(pattern, repl, title, flags=re.IGNORECASE)


def validate_and_clean_finding_urls(
    finding: AuditFinding,
    target_domain: str,
    crawl_summary: CrawlSummary
) -> bool:
    """
    Evidence Integrity & Hard URL Validation Layer:
    - Normalizes each URL
    - Derives exact inspected URLs from crawl_summary.pages
    - Also permits known site manifest endpoints on target_domain (e.g. /robots.txt, /sitemap.xml, /llms.txt)
    - Purges any uninspected or external URLs from affected_urls
    - If affected_urls becomes empty:
        - If site-level finding (proactive, or brand/organization/robots/sitemap), defaults to start_url
        - If page-specific defect (missing H1, CTA, missing title, etc.), returns False (discard finding)
    - Synchronizes any page count in finding title with len(finding.affected_urls)
    Returns True if finding is valid to keep, False if it should be discarded.
    """
    # 1. Build inspected set and manifest set
    inspected_urls: Set[str] = set()
    inspected_paths: Set[str] = set()

    for p in crawl_summary.pages:
        inspected_urls.add(p.url)
        inspected_urls.add(normalize_url(p.url))
        inspected_urls.add(p.url.rstrip('/'))
        inspected_urls.add(normalize_url(p.url).rstrip('/'))
        p_path = urlparse(p.url).path.rstrip('/') or '/'
        inspected_paths.add(p_path)

    base_domain = crawl_summary.target_domain.lower()
    start_parsed = urlparse(crawl_summary.start_url)
    scheme = start_parsed.scheme or "https"
    netloc = start_parsed.netloc or base_domain

    manifest_paths = {"/robots.txt", "/sitemap.xml", "/llms.txt", ""}
    for mp in manifest_paths:
        for host in {base_domain, netloc}:
            inspected_urls.add(f"{scheme}://{host}{mp}")
            inspected_urls.add(f"https://{host}{mp}")
            inspected_urls.add(f"http://{host}{mp}")
            inspected_urls.add(f"https://{host}{mp}/")
            inspected_urls.add(f"http://{host}{mp}/")

    # 2. Filter affected_urls to inspected & domain-matched
    cleaned: List[str] = []
    for u in finding.affected_urls:
        if not u:
            continue
        norm = normalize_url(u)
        parsed = urlparse(norm)
        norm_path = parsed.path.rstrip('/') or '/'

        # Must belong to target domain
        if not urls_belong_to_domain([norm], target_domain):
            continue

        # Must be in inspected URLs, inspected paths, or manifest paths
        is_inspected = (
            norm in inspected_urls
            or norm.rstrip('/') in inspected_urls
            or norm_path in inspected_paths
            or norm_path in manifest_paths
        )

        if is_inspected:
            cleaned.append(norm)

    deduped = dedupe_urls(cleaned)

    # 3. Handle empty affected_urls
    if deduped:
        finding.affected_urls = deduped
    else:
        # Determine if site-level finding that can fallback to start_url
        is_site_level = (
            finding.is_proactive
            or finding.category in ("entity-clarity", "structured-data")
            and any(k in finding.title.lower() for k in ("organization", "brand", "robots", "sitemap", "knowledge-graph"))
            or any(k in finding.title.lower() for k in ("robots.txt", "sitemap.xml", "llms.txt"))
        )
        if is_site_level:
            finding.affected_urls = [normalize_url(crawl_summary.start_url)]
        else:
            # Page-specific defect with no inspected affected page left -> discard
            return False

    # 4. Auto-synchronize count in title with len(finding.affected_urls)
    finding.title = sync_title_page_count(finding.title, len(finding.affected_urls))

    return True


def deduplicate_findings(raw_findings: List[AuditFinding]) -> List[AuditFinding]:
    """
    Root-Cause Deduplication Engine:
    Identifies overlapping findings that share an underlying root cause and merges them
    into coherent, high-leverage consolidated findings with combined evidence.
    """
    deduped: List[AuditFinding] = []
    consumed_titles: Set[str] = set()

    # 1. Cluster: Entity Anchoring & Knowledge Graph Disambiguation
    # Merges missing Organization schema + missing external authority links
    has_missing_org = any("organization" in f.title.lower() for f in raw_findings)
    has_missing_auth = any(
        "authoritative entity" in f.title.lower() or "sameas" in f.title.lower()
        for f in raw_findings
    )

    if has_missing_org and has_missing_auth:
        org_f = next(f for f in raw_findings if "organization" in f.title.lower())
        auth_f = next(
            f for f in raw_findings
            if "authoritative entity" in f.title.lower() or "sameas" in f.title.lower()
        )

        combined_evidence = (
            f"{org_f.evidence} Additionally: {auth_f.evidence} "
            "(Missing authoritative sameAs profiles such as Wikidata and LinkedIn; entity lacks both schema.org/Organization structured data and external knowledge anchors)."
        )
        merged_urls = dedupe_urls(org_f.affected_urls + auth_f.affected_urls)

        consolidated_entity = AuditFinding(
            id="",
            title="Missing Organization Knowledge-Graph schema and authoritative entity profiles",
            severity="high",
            confidence="high",
            evidence=combined_evidence,
            why_it_matters="AI search engines and knowledge retrieval agents require verified entity anchors (Wikidata, LinkedIn) and Organization schema to disambiguate brands from generic terms.",
            root_cause="Brand entity is not defined in machine-readable schema or linked to authoritative external knowledge graphs.",
            suggested_action=SuggestedAction(
                summary="Deploy schema.org/Organization JSON-LD on the homepage with verified sameAs profiles (Wikidata, LinkedIn) to anchor brand identity in LLM knowledge graphs.",
                priority="high",
                implementation_guide="Add <script type='application/ld+json'> with @type: Organization, name, url, logo, description, and sameAs array."
            ),
            category="entity-clarity",
            affected_urls=merged_urls,
            detection_method="Synthesized entity-clarity and structured-data audit"
        )
        deduped.append(consolidated_entity)
        consumed_titles.add(org_f.title.lower())
        consumed_titles.add(auth_f.title.lower())

    # 2. Cluster: Product Machine-Readability & Schema
    # Merges product schema absence with client-side SPA rendering on product pages
    has_prod_schema_gap = any("product" in f.title.lower() and "structured data" in f.title.lower() for f in raw_findings)
    has_spa_render_gap = any("javascript" in f.title.lower() or "spa" in f.title.lower() for f in raw_findings)

    if has_prod_schema_gap and has_spa_render_gap:
        prod_f = next(f for f in raw_findings if "product" in f.title.lower() and "structured data" in f.title.lower())
        spa_f = next(f for f in raw_findings if "javascript" in f.title.lower() or "spa" in f.title.lower())

        # If they affect the same or overlapping URLs
        overlapping_urls = set(prod_f.affected_urls).intersection(set(spa_f.affected_urls))
        if overlapping_urls or any("product" in u.lower() for u in spa_f.affected_urls):
            combined_evidence = (
                f"{prod_f.evidence} In addition, {spa_f.evidence} "
                "(Product information is rendered solely client-side without machine-readable SSR or schema)."
            )
            merged_urls = dedupe_urls(prod_f.affected_urls + spa_f.affected_urls)

            consolidated_prod = AuditFinding(
                id="",
                title="Product catalog details are not machine-readable in initial HTML",
                severity="high",
                confidence="high",
                evidence=combined_evidence,
                why_it_matters="AI shopping agents and web indexers cannot parse product prices, availability, or specifications if content is locked behind client-side rendering without schema.",
                root_cause="Product templates rely on dynamic client execution and omit static semantic markup.",
                suggested_action=SuggestedAction(
                    summary="Implement Server-Side Rendering (SSR) for product pages and embed schema.org/Product JSON-LD with valid offer pricing in the initial HTTP response.",
                    priority="high"
                ),
                category="structured-data",
                affected_urls=merged_urls,
                detection_method="Synthesized rendering and structured-data audit"
            )
            deduped.append(consolidated_prod)
            consumed_titles.add(prod_f.title.lower())
            consumed_titles.add(spa_f.title.lower())

    # 3. Process all other findings, deduplicating by title similarity and root-cause
    for f in raw_findings:
        if f.title.lower() in consumed_titles:
            continue

        # Check if already present by exact or near title
        already_present = False
        for existing in deduped:
            if f.title.lower() == existing.title.lower():
                already_present = True
                # Merge affected URLs if same title
                existing.affected_urls = dedupe_urls(existing.affected_urls + f.affected_urls)
                existing.title = sync_title_page_count(existing.title, len(existing.affected_urls))
                break
            # If same root cause and overlapping URLs, merge
            if (
                f.root_cause
                and existing.root_cause
                and f.root_cause.lower() == existing.root_cause.lower()
                and set(f.affected_urls).intersection(set(existing.affected_urls))
            ):
                already_present = True
                existing.affected_urls = dedupe_urls(existing.affected_urls + f.affected_urls)
                existing.evidence = f"{existing.evidence} Additionally: {f.evidence}"
                existing.title = sync_title_page_count(existing.title, len(existing.affected_urls))
                # Upgrade severity if higher
                if SEVERITY_ORDER.get(f.severity.lower(), 0) > SEVERITY_ORDER.get(existing.severity.lower(), 0):
                    existing.severity = f.severity
                break

        if not already_present:
            deduped.append(f)

    return deduped


def generate_proactive_recommendations(
    crawl_summary: CrawlSummary,
    allow_unknown_site_type: bool = False
) -> List[AuditFinding]:
    """
    Generates high-value proactive improvements that strengthen discoverability or engagement
    even where no explicit defect was found, adhering to Part 21 & Adobe guidelines.
    Proactive items are clearly marked and never framed as defects.
    """
    proactive: List[AuditFinding] = []
    domain = crawl_summary.target_domain

    # 1. Proactive llms.txt discovery manifest
    # Only recommend if site does NOT already have an /llms.txt manifest
    site_type = getattr(crawl_summary, "site_type", None)
    
    has_llms_txt = getattr(crawl_summary, "llms_txt_found", False)
    llms_relevant_types = {
        "corporate",
        "saas",
        "ecommerce",
        "marketplace",
        "publisher",
        "documentation",
        "local_business",
        "nonprofit",
    }
    if not has_llms_txt and (
        site_type in llms_relevant_types
        or (
            allow_unknown_site_type
            and site_type == "other"
        )
    ):
        proactive.append(AuditFinding(
            id="",
            title="Proactive: Consider deploying an /llms.txt discovery manifest",
            severity="low",
            confidence="high",
            evidence=f"No /llms.txt manifest was observed on {domain}. /llms.txt is an optional emerging convention for providing AI-oriented summaries and resource links.",
            why_it_matters="AI search agents and LLM crawlers can leverage an optional /llms.txt file to quickly index canonical brand summaries and links to primary documentation.",
            root_cause="Site has not yet deployed an optional /llms.txt markdown manifest.",
            suggested_action=SuggestedAction(
                summary="/llms.txt is an optional emerging convention for providing AI-oriented summaries and resource links.",
                priority="low",
                implementation_guide="Create an optional static markdown file at /llms.txt containing: # Brand Name, an introductory summary, and clean links to primary resources."
            ),
            category="discoverability",
            affected_urls=[f"{crawl_summary.start_url.rstrip('/')}/llms.txt"],
            is_proactive=True,
            detection_method="Proactive Best-Practice Engine"
        ))

    # 2. Proactive FAQPage Schema for Conversational AI
    has_faq_schema = any("faqpage" in (p.raw_html or "").lower() for p in crawl_summary.pages)
        # Only recommend FAQPage when actual FAQ/question-answer content exists.
    # Absence of FAQ schema alone is NOT evidence of a problem.
    faq_content_detected = any(
        re.search(
            r"\b(frequently asked questions|faq|common questions|questions and answers)\b",
            (p.raw_html or "")[:200000],
            re.IGNORECASE
        )
        for p in crawl_summary.pages
    )

    if not has_faq_schema and faq_content_detected:
        conversion_urls = [
            p.url for p in crawl_summary.pages
            if p.page_type in ("homepage", "pricing", "product_detail", "service")
        ]
        target_urls = conversion_urls[:2] if conversion_urls else [crawl_summary.start_url]

        proactive.append(AuditFinding(
            id="",
            title="Proactive: Deploy FAQPage schema to capture conversational AI search queries",
            severity="medium",
            confidence="high",
            evidence="No FAQPage structured data was found across crawled conversion pages. Structured Q&A pairs assist conversational AI engines in citing authoritative answers.",
            why_it_matters="Conversational search engines prioritize Q&A structured data when surfacing direct answers in AI Overviews and answer cards.",
            root_cause="Key customer questions are not semantically indexed as FAQPage schema.",
            suggested_action=SuggestedAction(
                summary="Add FAQPage JSON-LD schema with 3-5 verified customer question-and-answer pairs on your product and pricing pages.",
                priority="medium",
                implementation_guide="Embed <script type='application/ld+json'> with @type: FAQPage and mainEntity array containing Question and Answer objects."
            ),
            category="structured-data",
            affected_urls=target_urls,
            is_proactive=True,
            detection_method="Proactive Best-Practice Engine"
        ))

    return proactive


class AuditOrchestrator:
    def __init__(self, target_url: str, max_pages: int = 12):
        self.target_url = target_url
        self.max_pages = max_pages

    def run_full_audit(self, preloaded_summary: Optional[CrawlSummary] = None) -> Dict[str, Any]:
        """
        Runs bounded crawl, classifies site and pages, invokes specialist skills,
        enforces confidence gating and evidence integrity, deduplicates by root cause,
        injects proactive recommendations, and emits the final report.
        """
        if preloaded_summary:
            crawl_summary = preloaded_summary

            site_type_was_missing = not getattr(
                crawl_summary,
                "site_type",
                None
            )

            if site_type_was_missing:
                crawl_summary.site_type = classify_site(
                    crawl_summary.pages,
                    crawl_summary.target_domain
                )
        else:
            site_type_was_missing = False
            crawler = BoundedCrawler(
                self.target_url,
                max_pages=self.max_pages
            )
            crawl_summary = crawler.crawl()

        raw_findings: List[AuditFinding] = []

        # 1. Execute Specialist Skills
        raw_findings.extend(run_crawl_render_audit(crawl_summary))
        raw_findings.extend(run_structured_data_audit(crawl_summary))
        raw_findings.extend(run_freshness_corroboration_audit(crawl_summary))
        raw_findings.extend(run_entity_clarity_audit(crawl_summary))
        raw_findings.extend(run_engagement_audit(crawl_summary))

        # 2. Evidence Integrity & URL Validation (Part 1, 18, 23)
        target_domain = crawl_summary.target_domain
        validated_findings: List[AuditFinding] = []

        for finding in raw_findings:
            # Clean and validate URLs against inspected pages
            valid = validate_and_clean_finding_urls(finding, target_domain, crawl_summary)
            if not valid:
                continue

            # Confidence Gating (Part 2, 15):
            # If finding is low-confidence, do not emit as critical/high confirmed defect.
            if finding.confidence == "low":
                if finding.severity in ("critical", "high"):
                    finding.severity = "medium"
                # If evidence is empty, discard finding
                if not finding.evidence.strip():
                    continue

            validated_findings.append(finding)

        # 3. Root-Cause Deduplication (Part 17)
        deduped = deduplicate_findings(validated_findings)
        for f in deduped:
            f.title = sync_title_page_count(f.title, len(f.affected_urls))

        # 4. Proactive Recommendations (Part 21)
        proactive = generate_proactive_recommendations(
            crawl_summary,
            allow_unknown_site_type=site_type_was_missing
        )
        for p in proactive:
            validate_and_clean_finding_urls(p, target_domain, crawl_summary)

        all_findings = deduped + proactive

        # 5. Sort Deterministically: Severity (Critical > High > Medium), then Proactive last
        all_findings.sort(
            key=lambda f: (
                0 if f.is_proactive else 1,
                SEVERITY_ORDER.get(f.severity.lower(), 0)
            ),
            reverse=True
        )

        # 6. Assign Standardized Sequential IDs
        for idx, finding in enumerate(all_findings, 1):
            finding.id = f"F-{idx:03d}"

        # 7. Build and Validate Final Report
        parsed = urlparse(crawl_summary.start_url)
        site_name = parsed.netloc or crawl_summary.target_domain

        report = build_final_report(
            site=site_name,
            findings=all_findings,
            audited_at=crawl_summary.crawled_at,
            crawl_summary=crawl_summary
        )
        validate_report_schema(report)
        return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Adobe Brand AI-Readiness and Engagement Audit Entrypoint")
    parser.add_argument("--url", required=True, help="Target website URL or domain")
    parser.add_argument("--max-pages", type=int, default=12, help="Max pages to crawl (default 12)")
    parser.add_argument("--output", help="Optional output report file path")
    parser.add_argument("--format", choices=["json", "report"], default="json", help="Output format: json (default) or report (human-readable)")
    args = parser.parse_args()

    orchestrator = AuditOrchestrator(args.url, max_pages=args.max_pages)
    report = orchestrator.run_full_audit()

    if args.format == "report":
        formatted_output = build_human_report(report)
    else:
        formatted_output = json.dumps(report, indent=2)

    if args.output:
        with open(args.output, "w", encoding="utf-8") as f:
            f.write(formatted_output)
        print(f"Audit report saved to {args.output}")
    else:
        print(formatted_output)
