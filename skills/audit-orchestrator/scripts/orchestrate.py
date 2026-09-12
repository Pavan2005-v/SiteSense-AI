"""
Main Entrypoint Orchestrator for Brand AI-Readiness and Engagement Audit.
Coordinates specialist skills, validates evidence integrity, executes root-cause deduplication,
applies confidence gating, injects site-appropriate proactive recommendations,
tracks dual-objective coverage, and generates the final Adobe Round 3 report.
"""
from pathlib import Path
from typing import List, Dict, Any, Optional, Set, Tuple
import argparse
import json
import re
import sys
from urllib.parse import urlparse
from bs4 import BeautifulSoup

# Ensure project root is in sys.path when executed directly as a script
_PROJECT_ROOT = str(Path(__file__).resolve().parents[3])
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)

import skills
from skills.common.models import AuditFinding, SuggestedAction, CrawlSummary
from skills.common.url_utils import normalize_url, dedupe_urls, urls_belong_to_domain
from skills.common.site_classifier import classify_site
from skills.crawl_render_audit.scripts.crawler import BoundedCrawler
from skills.crawl_render_audit.scripts.audit_crawl import run_crawl_render_audit
from skills.structured_data_audit.scripts.audit_schema import run_structured_data_audit
from skills.freshness_corroboration.scripts.audit_freshness import run_freshness_corroboration_audit
from skills.entity_clarity_audit.scripts.audit_entity import run_entity_clarity_audit
from skills.engagement_audit.scripts.audit_engagement import run_engagement_audit

try:
    from .report_builder import build_final_report, build_human_report, validate_report_schema
except (ImportError, ValueError):
    from skills.audit_orchestrator.scripts.report_builder import build_final_report, build_human_report, validate_report_schema


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
    Evidence Integrity & URL Validation Layer:
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

    cleaned: List[str] = []
    for u in finding.affected_urls:
        if not u:
            continue
        norm = normalize_url(u)
        parsed = urlparse(norm)
        norm_path = parsed.path.rstrip('/') or '/'

        # Must belong to target domain or its subdomains
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

    if deduped:
        finding.affected_urls = deduped
    else:
        is_site_level = (
            finding.is_proactive
            or finding.category in ("entity-clarity", "structured-data")
            and any(k in finding.title.lower() for k in ("organization", "brand", "robots", "sitemap", "knowledge-graph"))
            or any(k in finding.title.lower() for k in ("robots.txt", "sitemap.xml", "llms.txt"))
        )
        if is_site_level:
            finding.affected_urls = [normalize_url(crawl_summary.start_url)]
        else:
            return False

    finding.title = sync_title_page_count(finding.title, len(finding.affected_urls))
    return True


def evaluate_finding_evidence_contract(
    finding: AuditFinding,
    crawl_summary: CrawlSummary
) -> bool:
    """
    Global Evidence Gate:
    Enforces 'No evidence = No finding' and ensures that absence of tags/features
    on unrendered shells or challenge pages is never flagged as downstream content defects.
    """
    # 1. No evidence -> No finding
    if not finding.evidence or not finding.evidence.strip():
        return False

    # Lookup map for page data
    page_map = {p.url: p for p in crawl_summary.pages}
    norm_page_map = {normalize_url(p.url): p for p in crawl_summary.pages}

    affected_pages = []
    for u in finding.affected_urls:
        p = page_map.get(u) or norm_page_map.get(normalize_url(u))
        if p:
            affected_pages.append(p)

    title_lower = finding.title.lower()
    is_render_gap_finding = any(k in title_lower for k in ("javascript", "spa", "rendering gap", "client-side"))

    # If all affected pages are unrendered SPA shells or challenge pages:
    # Downstream content defects (headings, CTA, duplicate content, schema) cannot be
    # reliably evaluated on empty JS shells. Suppress downstream finding in favor of the single root-cause render gap finding.
    if affected_pages and not is_render_gap_finding:
        all_spa_or_challenge = all(
            getattr(p, "is_spa_shell", False) or getattr(p, "has_interstitial_challenge", False)
            for p in affected_pages
        )
        if all_spa_or_challenge:
            return False

    # 2. Duplicate Content Evidence Gate:
    # Requires substantive content (word count >= 50) and non-shell pages
    if "duplicate" in title_lower or "identical" in title_lower:
        for p in affected_pages:
            if getattr(p, "is_spa_shell", False) or getattr(p, "has_interstitial_challenge", False):
                return False
            wc = getattr(p, "word_count", 0) or len((p.text_content or "").split())
            if wc < 50:
                return False

    # 3. Call-To-Action (CTA) Evidence Gate:
    if "call-to-action" in title_lower or "cta" in title_lower:
        for p in affected_pages:
            if getattr(p, "is_spa_shell", False):
                return False
            if p.page_type in ("legal", "privacy", "terms", "utility", "search", "documentation"):
                return False

    # 4. Heading Hierarchy Evidence Gate:
    if "h1" in title_lower or "heading" in title_lower:
        for p in affected_pages:
            if getattr(p, "is_spa_shell", False) or getattr(p, "has_interstitial_challenge", False):
                return False

    return True


def deduplicate_findings(raw_findings: List[AuditFinding]) -> List[AuditFinding]:
    """
    Root-Cause Deduplication Engine:
    Identifies overlapping findings that share an underlying root cause and merges them
    into coherent, high-leverage consolidated findings with combined evidence.
    """
    deduped: List[AuditFinding] = []
    consumed_titles: Set[str] = set()

    # 0. Cluster: Wildcard Crawl Block Subsumption
    has_all_crawlers = any("all crawlers completely blocked" in f.title.lower() for f in raw_findings)
    ai_blocked_finding = next(
        (f for f in raw_findings if any(k in f.title.lower() for k in ("ai assistants explicitly blocked", "ai crawler is explicitly blocked", "ai crawlers explicitly blocked"))),
        None
    )
    if has_all_crawlers and ai_blocked_finding:
        all_f = next(f for f in raw_findings if "all crawlers completely blocked" in f.title.lower())
        all_f.evidence = f"{all_f.evidence} (Subsumes AI user-agent restrictions: {ai_blocked_finding.evidence})"
        consumed_titles.add(ai_blocked_finding.title.lower())

    # 1. Cluster: Entity Anchoring & Knowledge Graph Disambiguation
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
    has_prod_schema_gap = any("product" in f.title.lower() and "structured data" in f.title.lower() for f in raw_findings)
    has_spa_render_gap = any("javascript" in f.title.lower() or "spa" in f.title.lower() for f in raw_findings)

    if has_prod_schema_gap and has_spa_render_gap:
        prod_f = next(f for f in raw_findings if "product" in f.title.lower() and "structured data" in f.title.lower())
        spa_f = next(f for f in raw_findings if "javascript" in f.title.lower() or "spa" in f.title.lower())

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

        already_present = False
        for existing in deduped:
            if f.title.lower() == existing.title.lower():
                already_present = True
                existing.affected_urls = dedupe_urls(existing.affected_urls + f.affected_urls)
                existing.title = sync_title_page_count(existing.title, len(existing.affected_urls))
                break
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
                if SEVERITY_ORDER.get(f.severity.lower(), 0) > SEVERITY_ORDER.get(existing.severity.lower(), 0):
                    existing.severity = f.severity
                break

        if not already_present:
            deduped.append(f)

    return deduped


def extract_verified_faq_pairs(soup: BeautifulSoup) -> List[Tuple[str, str]]:
    """
    Semantic FAQ applicability detector (Phase 6).
    Extracts verified Question + Substantive Text Answer pairs from HTML.
    A heading/label shaped like a question is NOT automatically an FAQ item.
    Candidates are rejected when evidence indicates they are NOT intended as
    visitor-facing Q&A content:
    1. Feedback/support widgets ("Was this helpful?", "Need more help?", "Contact support").
    2. Editorial headlines / blog titles: interrogative-looking statements longer
       than ~6 words with no "?" and no second/first-person pronouns
       (e.g. "Why millions of viewers tune into...").
    3. Over-long headings (> 110 chars) and navigation/search labels.
    Requires a genuine Question + Substantive Text Answer (>= 12 words, prose).
    Returns list of (question_text, answer_snippet) tuples.
    """
    feedback_pattern = re.compile(
        r"\b(?:was\s+this|is\s+this|did\s+this|helpful|rate\s+this|feedback|survey|thumbs)\b",
        re.I
    )
    # Support / navigation / generic-CTA labels that are NOT FAQ questions
    non_faq_pattern = re.compile(
        r"\b(?:need\s+(?:more\s+)?help|still\s+need\s+help|get\s+help|help\s+center|"
        r"contact\s+(?:us|support|sales)|support\s+team|customer\s+support|"
        r"related\s+(?:articles|questions|topics|posts)|see\s+also|quick\s+links|"
        r"learn\s+more|read\s+more|sign\s+in|log\s+in|search|subscribe|"
        r"join\s+(?:the\s+)?(?:discussion|community)|leave\s+a\s+(?:comment|reply)|"
        r"post\s+a\s+comment|share\s+this|follow\s+us|about\s+us|privacy\s+policy)\b",
        re.I
    )
    question_prefix_pattern = re.compile(
        r"^(?:what|how|why|when|where|who|can\s+i|do\s+you|is\s+there|how\s+do\s+i|how\s+to|what\s+is|what\s+are|frequently\s+asked)\b",
        re.I
    )
    # Second/first-person markers typical of genuine visitor-facing questions
    audience_pronoun_pattern = re.compile(
        r"\b(?:you|your|yours|my|me|i|we|our|us)\b",
        re.I
    )

    def is_genuine_faq_question(q_text: str) -> bool:
        """Applies semantic FAQ-applicability heuristics to a question-shaped heading."""
        q_text = q_text.strip()
        if not q_text:
            return False
        if feedback_pattern.search(q_text) or non_faq_pattern.search(q_text):
            return False
        # Navigation/search labels and over-long editorial headlines
        if len(q_text) > 110:
            return False
        word_count = len(q_text.split())
        if word_count < 3:
            return False
        is_interrogative = bool(question_prefix_pattern.search(q_text)) or q_text.endswith("?")
        if not is_interrogative:
            return False
        # Editorial headline discriminator: interrogative-looking declarative statements
        # (no "?", no audience pronouns, >= 6 words) are headlines, not FAQ questions.
        if not q_text.endswith("?") and not audience_pronoun_pattern.search(q_text) and word_count >= 6:
            return False
        return True

    pairs = []

    # 1. Strong structure: definition lists (<dt> <dd>)
    for dt in soup.find_all("dt"):
        q_text = dt.get_text(strip=True)
        if not is_genuine_faq_question(q_text):
            continue
        dd = dt.find_next_sibling("dd")
        if dd:
            a_text = dd.get_text(strip=True)
            if len(a_text.split()) >= 12 and not feedback_pattern.search(a_text):
                pairs.append((q_text, a_text[:120]))

    # 2. Strong structure: <details> <summary>
    for details in soup.find_all("details"):
        summary = details.find("summary")
        if not summary:
            continue
        q_text = summary.get_text(strip=True)
        if not is_genuine_faq_question(q_text):
            continue
        clone = BeautifulSoup(str(details), "html.parser").find("details")
        if clone and clone.find("summary"):
            clone.find("summary").decompose()
        a_text = clone.get_text(strip=True) if clone else ""
        if len(a_text.split()) >= 12 and not feedback_pattern.search(a_text):
            pairs.append((q_text, a_text[:120]))

    # 3. Weak structure: headings (h2, h3, h4) with substantive PROSE sibling paragraphs.
    # Requires an actual <p> paragraph in the answer (not only lists/divs/links),
    # so "Need more help?" -> [contact links] style blocks do not qualify.
    for h in soup.find_all(["h2", "h3", "h4"]):
        q_text = h.get_text(strip=True)
        if not is_genuine_faq_question(q_text):
            continue

        ans_parts = []
        has_prose = False
        curr = h.find_next_sibling()
        while curr and curr.name not in ("h1", "h2", "h3", "h4"):
            if curr.name in ("p", "div", "ul", "ol", "section"):
                part_text = curr.get_text(strip=True)
                if part_text:
                    ans_parts.append(part_text)
                    if curr.name == "p" and len(part_text.split()) >= 12:
                        has_prose = True
            curr = curr.find_next_sibling()

        a_text = " ".join(ans_parts)
        if has_prose and len(a_text.split()) >= 12 and not feedback_pattern.search(a_text) and not non_faq_pattern.search(a_text):
            pairs.append((q_text, a_text[:120]))

    seen_q = set()
    unique_pairs = []
    for q, a in pairs:
        q_key = q.lower().strip()
        if q_key not in seen_q:
            seen_q.add(q_key)
            unique_pairs.append((q, a))

    return unique_pairs


def count_strong_faq_structures(soup: BeautifulSoup) -> int:
    """
    Counts explicitly FAQ-structured containers on the page: <dl> question/answer groups,
    <details>/<summary> blocks, and elements explicitly marked as FAQ sections
    (class/id/aria-label containing 'faq'). These are strong structural evidence of
    genuine FAQ content, unlike loosely paired question-shaped headings.
    """
    strong = 0
    strong += len(soup.find_all("dl"))
    strong += len(soup.find_all("details"))
    strong += len(soup.find_all(attrs={
        "class": lambda x: x and any("faq" in str(c).lower() for c in (x if isinstance(x, list) else [x]))
    }))
    strong += len(soup.find_all(attrs={
        "id": lambda x: x and "faq" in str(x).lower()
    }))
    strong += len(soup.find_all(attrs={
        "aria-label": lambda x: x and "faq" in str(x).lower()
    }))
    return strong


def generate_proactive_recommendations(
    crawl_summary: CrawlSummary
) -> List[AuditFinding]:
    """
    Generates high-value proactive improvements that strengthen discoverability or engagement
    even where no explicit defect was found. Proactive items are clearly marked and never framed as defects.
    """
    proactive: List[AuditFinding] = []
    domain = crawl_summary.target_domain

    # 1. Proactive llms.txt discovery manifest
    # Only recommend when:
    # a) The site does NOT already serve an /llms.txt file
    # b) Site context is confirmed (NOT unknown, other, search portal, knowledge base, or utility)
    # c) Site operates a confirmed documentation or SaaS architecture (>= 3 pages)
    # d) The site has substantive technical or product content
    has_llms_txt = any("/llms.txt" in p.url.lower() for p in crawl_summary.pages)
    site_type = getattr(crawl_summary, "site_type", "other") or "other"
    total_pages = len(crawl_summary.pages)
    has_technical_or_product_content = any(
        p.page_type in ("documentation", "product_detail", "service", "article")
        for p in crawl_summary.pages
    )

    is_llms_txt_appropriate = (
        not has_llms_txt and
        site_type not in ("unknown", "other", "search_portal", "knowledge_base", "utility") and
        site_type in ("documentation", "saas", "developer_platform") and
        total_pages >= 3 and
        has_technical_or_product_content
    )

    if is_llms_txt_appropriate:
        proactive.append(AuditFinding(
            id="",
            title="Proactive: Consider deploying an /llms.txt discovery manifest",
            severity="low",
            confidence="high",
            evidence=f"Site operates a multi-page {site_type.replace('_', ' ')} architecture ({total_pages} pages crawled) without an /llms.txt manifest. For content-rich platforms, /llms.txt is an optional emerging convention that allows AI assistants to cleanly parse core offerings and primary documentation links.",
            why_it_matters="AI search agents and LLM crawlers can leverage an optional /llms.txt file to quickly index canonical brand summaries and links to primary documentation.",
            root_cause="Site has not yet deployed an optional /llms.txt markdown manifest.",
            suggested_action=SuggestedAction(
                summary="Consider publishing an optional /llms.txt markdown file at the root domain summarizing your brand, core capabilities, and primary documentation links.",
                priority="low",
                implementation_guide="Create an optional static markdown file at /llms.txt containing: # Brand Name, an introductory summary, and clean links to primary resources."
            ),
            category="discoverability",
            affected_urls=[f"{crawl_summary.start_url.rstrip('/')}/llms.txt"],
            is_proactive=True,
            recommendation_type="proactive",
            detection_method="Proactive Best-Practice Engine"
        ))

    # 2. Proactive FAQPage Schema for Existing Q&A Content
    # Context-aware (Phase 6): FAQPage is NOT automatically required whenever
    # question-shaped text exists. Only recommend when the page demonstrates genuine
    # FAQ structure: >= 3 verified Q&A pairs, OR >= 2 pairs supported by explicit
    # FAQ-structural containers (dl/details/faq-marked sections). Proactive only,
    # lower priority, never framed as a defect.
    has_faq_schema = any("faqpage" in (p.raw_html or "").lower() for p in crawl_summary.pages)
    if not has_faq_schema and len(crawl_summary.pages) > 0:
        faq_sections_detected = []   # (url, pairs, strong_structure_count)
        for p in crawl_summary.pages:
            soup = BeautifulSoup(p.raw_html or "", "html.parser")
            verified_pairs = extract_verified_faq_pairs(soup)
            strong_structures = count_strong_faq_structures(soup)
            qualifies = (
                len(verified_pairs) >= 3 or
                (len(verified_pairs) >= 2 and strong_structures >= 1)
            )
            if qualifies:
                faq_sections_detected.append((p.url, verified_pairs, strong_structures))

        if faq_sections_detected:
            target_urls = [u for u, _, _ in faq_sections_detected[:3]]
            sample_snippets = []
            total_pairs = 0
            strong_evidence = False
            for _, pairs, strong_cnt in faq_sections_detected[:2]:
                total_pairs += len(pairs)
                if strong_cnt >= 1:
                    strong_evidence = True
                for q, a in pairs[:2]:
                    sample_snippets.append(f"'{q}' -> '{a[:60]}...'")
            snippet_str = f" (verified Q&A pairs: {'; '.join(sample_snippets[:2])})" if sample_snippets else ""
            # Priority follows evidence strength: explicit FAQ containers with several
            # pairs justify medium; loose heading pairs are only a low-priority opportunity.
            rec_severity = "medium" if strong_evidence and total_pairs >= 4 else "low"
            proactive.append(AuditFinding(
                id="",
                title="Proactive: Structure detected question-and-answer sections as FAQPage schema",
                severity=rec_severity,
                confidence="medium" if strong_evidence else "low",
                evidence=f"Observed {total_pairs} substantive question-and-answer pair(s) on {len(target_urls)} page(s) with{'out' if not strong_evidence else ''} explicit FAQ structure{snippet_str}. Converting these sections into schema.org FAQPage structured data enables machine crawlers to extract definitive answers directly without lossy heuristic parsing.",
                why_it_matters="Machine readers and search crawlers parse explicit schema.org Q&A pairs reliably, ensuring customer questions are attributed to authoritative brand answers.",
                root_cause="Existing FAQ content is delivered solely as unstructured visual HTML without corresponding JSON-LD schema.",
                suggested_action=SuggestedAction(
                    summary=f"Embed FAQPage JSON-LD schema on pages with detected Q&A sections ({', '.join(target_urls[:2])}).",
                    priority=rec_severity,
                    implementation_guide="Embed <script type='application/ld+json'> with @type: FAQPage and mainEntity array containing Question and Answer objects for existing FAQs."
                ),
                category="structured-data",
                affected_urls=target_urls,
                is_proactive=True,
                recommendation_type="proactive",
                detection_method="Proactive Best-Practice Engine"
            ))

    return proactive


class AuditOrchestrator:
    def __init__(self, target_url: str, max_pages: int = 12, debug: bool = False):
        self.target_url = target_url
        self.max_pages = max_pages
        self.debug = debug
        self.debug_log: Dict[str, Any] = {}

    def run_full_audit(self, preloaded_summary: Optional[CrawlSummary] = None) -> Dict[str, Any]:
        """
        Runs bounded crawl, classifies site and pages, invokes specialist skills,
        enforces confidence gating and evidence integrity, deduplicates by root cause,
        tracks dual-objective coverage, injects proactive recommendations, and emits the final report.
        """
        if preloaded_summary:
            crawl_summary = preloaded_summary
            if not getattr(crawl_summary, "site_type", None) or crawl_summary.site_type == "other":
                crawl_summary.site_type = classify_site(crawl_summary.pages, crawl_summary.target_domain)
        else:
            crawler = BoundedCrawler(self.target_url, max_pages=self.max_pages)
            crawl_summary = crawler.crawl()

        # 1. Execute Specialist Skills
        disc_findings: List[AuditFinding] = []
        engage_findings: List[AuditFinding] = []

        # Discoverability Skills
        disc_findings.extend(run_crawl_render_audit(crawl_summary))
        disc_findings.extend(run_structured_data_audit(crawl_summary))
        disc_findings.extend(run_freshness_corroboration_audit(crawl_summary))
        disc_findings.extend(run_entity_clarity_audit(crawl_summary))

        # Engagement Skill
        engage_findings.extend(run_engagement_audit(crawl_summary))

        raw_findings = disc_findings + engage_findings

        # 2. Evidence Integrity, URL Validation & Global Evidence Gate
        target_domain = crawl_summary.target_domain
        validated_findings: List[AuditFinding] = []
        suppressed_findings: List[Dict[str, Any]] = []

        for finding in raw_findings:
            valid = validate_and_clean_finding_urls(finding, target_domain, crawl_summary)
            if not valid:
                suppressed_findings.append({
                    "title": finding.title,
                    "reason": "invalid_or_uninspected_affected_urls",
                    "affected_urls": finding.affected_urls
                })
                continue

            # Confidence Gating: Low-confidence findings are never critical or high
            if finding.confidence == "low":
                if finding.severity in ("critical", "high"):
                    finding.severity = "medium"
                if not finding.evidence.strip():
                    suppressed_findings.append({
                        "title": finding.title,
                        "reason": "low_confidence_empty_evidence",
                        "affected_urls": finding.affected_urls
                    })
                    continue

            # Global Evidence Gate: enforce contract
            if not evaluate_finding_evidence_contract(finding, crawl_summary):
                suppressed_findings.append({
                    "title": finding.title,
                    "reason": "failed_evidence_gate_contract",
                    "affected_urls": finding.affected_urls
                })
                continue

            validated_findings.append(finding)

        # 3. Root-Cause Deduplication
        deduped = deduplicate_findings(validated_findings)
        for f in deduped:
            f.title = sync_title_page_count(f.title, len(f.affected_urls))

        # 4. Proactive Recommendations
        proactive = generate_proactive_recommendations(crawl_summary)
        for p in proactive:
            validate_and_clean_finding_urls(p, target_domain, crawl_summary)

        all_findings = deduped + proactive

        # 5. Sort Deterministically: Non-proactive first, then Severity (Critical > High > Medium > Low)
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

        # 7. Coverage Accounting
        total_eng_defects = sum(1 for f in deduped if f.category == "engagement")
        total_disc_defects = sum(1 for f in deduped if f.category != "engagement")

        if len(crawl_summary.pages) == 0:
            coverage_metrics = {
                "discoverability": {
                    "checks_run": 1,  # Only robots.txt inspection could be performed
                    "findings": total_disc_defects
                },
                "engagement": {
                    "checks_run": 0,  # No pages could be inspected
                    "findings": 0
                }
            }
        else:
            coverage_metrics = {
                "discoverability": {
                    "checks_run": 16,
                    "findings": total_disc_defects
                },
                "engagement": {
                    "checks_run": 7,
                    "findings": total_eng_defects
                }
            }

        # 8. Diagnostics / Debug Trace
        if self.debug:
            self.debug_log = {
                "requested_url": self.target_url,
                "final_url": crawl_summary.start_url,
                "target_domain": crawl_summary.target_domain,
                "site_type": getattr(crawl_summary, "site_type", "unknown"),
                "pages_crawled": len(crawl_summary.pages),
                "pages_discovered": getattr(crawl_summary, "pages_discovered", len(crawl_summary.pages)),
                "pages_queued": getattr(crawl_summary, "pages_queued", 0),
                "skipped_urls": getattr(crawl_summary, "skipped_urls", {}),
                "rejection_reasons": getattr(crawl_summary, "rejection_reasons", {}),
                "robots_blocked_urls": getattr(crawl_summary, "robots_blocked_urls", []),
                "pages_inspected": [
                    {
                        "url": p.url,
                        "status_code": p.status_code,
                        "page_type": p.page_type,
                        "is_spa_shell": getattr(p, "is_spa_shell", False),
                        "has_interstitial_challenge": getattr(p, "has_interstitial_challenge", False),
                        "word_count": getattr(p, "word_count", 0) or len((p.text_content or "").split()),
                        "interactive_elements_count": getattr(p, "interactive_elements_count", 0)
                    }
                    for p in crawl_summary.pages
                ],
                "raw_findings_count": len(raw_findings),
                "validated_findings_count": len(validated_findings),
                "suppressed_findings": suppressed_findings,
                "deduped_findings_count": len(deduped),
                "proactive_recommendations_count": len(proactive),
                "final_findings": [
                    {
                        "id": f.id,
                        "title": f.title,
                        "severity": f.severity,
                        "confidence": f.confidence,
                        "is_proactive": f.is_proactive
                    }
                    for f in all_findings
                ]
            }

        # 9. Build and Validate Final Report
        parsed = urlparse(crawl_summary.start_url)
        site_name = parsed.netloc or crawl_summary.target_domain

        custom_metadata = {"debug": self.debug_log} if self.debug else None

        report = build_final_report(
            site=site_name,
            findings=all_findings,
            audited_at=crawl_summary.crawled_at,
            crawl_summary=crawl_summary,
            coverage=coverage_metrics,
            custom_metadata=custom_metadata
        )
        validate_report_schema(report)
        return report


if __name__ == "__main__":
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Adobe Brand AI-Readiness and Engagement Audit Entrypoint")
    parser.add_argument("--url", required=True, help="Target website URL or domain")
    parser.add_argument("--max-pages", type=int, default=12, help="Max pages to crawl (default 12)")
    parser.add_argument("--output", help="Optional output report file path")
    parser.add_argument("--format", choices=["json", "report"], default="json", help="Output format: json (default) or report (human-readable)")
    parser.add_argument("--debug", action="store_true", help="Enable internal evidence debug mode")
    args = parser.parse_args()

    orchestrator = AuditOrchestrator(args.url, max_pages=args.max_pages, debug=args.debug)
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
