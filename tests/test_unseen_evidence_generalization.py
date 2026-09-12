"""
Test suite for Unseen Evidence Generalization and Global Evidence Gate Contract.

Verifies that the audit engine generalizes correctly to arbitrary unseen sites without site-specific rules:
1. Marketplace archetype with non-commercial actions ("Explore", "Register", "Find Opportunities") -> 0 CTA defects
2. SPA shell fallback -> preserves single root-cause rendering defect; suppresses false CTA, duplicate, and heading defects
3. Duplicate content gate: substantive identical text (>=80 words) flagged; short fallback/error strings suppressed
4. FAQPage proactive contract: requires genuine Q&A content; suppressed when no questions exist
5. Entity clarity: unambiguous branded presence without schema is not penalized with high-severity defects
6. Internal evidence debug mode trace completeness
"""
import pytest
from skills.common.models import PageData, CrawlSummary, AuditFinding, SuggestedAction
from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator
from skills.crawl_render_audit.scripts.robots_checker import RobotsChecker
from skills.structured_data_audit.scripts.schema_validator import SchemaValidator
from skills.entity_clarity_audit.scripts.disambiguation_rules import DisambiguationRules
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator, evaluate_finding_evidence_contract


def test_marketplace_platform_actions_zero_false_cta_defects():
    """
    Marketplace platforms have non-commercial conversion pathways (e.g. 'Explore Opportunities',
    'Participate', 'Register', 'Find Jobs') rather than 'Buy Now' / 'Pricing'.
    The auditor must recognize these as valid primary CTAs and produce 0 missing CTA defects.
    """
    marketplace_homepage = PageData(
        url="https://platform.talentmesh.example/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>TalentMesh - Opportunities, Challenges, and Hackathons</title></head>
        <body>
            <header>
                <nav>
                    <a href="/explore">Explore Opportunities</a>
                    <a href="/login">Login</a>
                </nav>
            </header>
            <main>
                <h1>Unlock Your Potential with Global Hackathons & Challenges</h1>
                <p>Compete, showcase your technical skills, and win awards with top industry partners.</p>
                <div class="actions">
                    <a class="btn-primary" href="/register">Register Now</a>
                    <a class="btn-secondary" href="/challenges">Participate in Challenges</a>
                </div>
            </main>
        </body>
        </html>
        """,
        text_content="TalentMesh Opportunities Challenges and Hackathons Explore Opportunities Login Unlock Your Potential with Global Hackathons Register Now Participate in Challenges",
        title="TalentMesh - Opportunities, Challenges, and Hackathons",
        page_type="homepage"
    )

    analyzer = EngagementAnalyzer([marketplace_homepage], site_type="marketplace")
    issues = analyzer.audit_value_proposition_and_ctas()
    cta_issues = [i for i in issues if i["issue_type"] == "missing_clear_cta"]
    assert len(cta_issues) == 0, f"Expected 0 CTA defects on marketplace with valid action buttons, got: {cta_issues}"


def test_spa_empty_shell_root_cause_dedup_and_evidence_gate():
    """
    When an unseen site returns an unrendered client-side SPA shell (<app-root> or <div id='root'>)
    with short cookie/JS fallback text across multiple URLs:
    - Exactly ONE root-cause rendering defect must be reported.
    - Zero downstream content defects (CTA, duplicate content, headings, page schema) must be reported.
    """
    shell_html = """<!DOCTYPE html>
    <html>
    <head><title>NovaPulse - Dynamic Platform</title></head>
    <body>
        <app-root></app-root>
        <noscript>
            <p>Please Wait Error: Cookies Disabled or JavaScript required. Your browser does not support JavaScript!</p>
            <a href="/legal/privacy-policy">Privacy Policy</a>
        </noscript>
        <script src="/runtime.js"></script>
        <script src="/main.js"></script>
    </body>
    </html>
    """
    p1 = PageData(
        url="https://novapulse.example/",
        status_code=200,
        raw_html=shell_html,
        text_content="Please Wait Error: Cookies Disabled or JavaScript required. Your browser does not support JavaScript! Privacy Policy",
        title="NovaPulse - Dynamic Platform",
        page_type="homepage",
        is_spa_shell=True,
        has_interstitial_challenge=True,
        word_count=16,
        interactive_elements_count=1
    )
    p2 = PageData(
        url="https://novapulse.example/legal/privacy-policy",
        status_code=200,
        raw_html=shell_html,
        text_content="Please Wait Error: Cookies Disabled or JavaScript required. Your browser does not support JavaScript! Privacy Policy",
        title="NovaPulse - Dynamic Platform",
        page_type="privacy",
        is_spa_shell=True,
        has_interstitial_challenge=True,
        word_count=16,
        interactive_elements_count=1
    )

    summary = CrawlSummary(
        target_domain="novapulse.example",
        start_url="https://novapulse.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[p1, p2],
        site_type="marketplace",
        robots_txt_found=True
    )

    orchestrator = AuditOrchestrator("https://novapulse.example/", debug=True)
    report = orchestrator.run_full_audit(preloaded_summary=summary)

    findings = report["findings"]
    # 1. Must report the root-cause rendering defect
    assert any("javascript" in f["title"].lower() or "empty" in f["title"].lower() or "spa" in f["title"].lower() for f in findings)
    # 2. Must NOT report false CTA defects
    assert not any("call-to-action" in f["title"].lower() or "cta" in f["title"].lower() for f in findings)
    # 3. Must NOT report false duplicate content defect on the fallback error text
    assert not any("duplicate" in f["title"].lower() or "identical" in f["title"].lower() for f in findings)
    # 4. Must NOT report false heading defects
    assert not any("h1" in f["title"].lower() or "multiple competing" in f["title"].lower() for f in findings)
    # 5. Must NOT report false proactive FAQPage schema
    assert not any("faqpage" in f["title"].lower() for f in findings)


def test_duplicate_content_evidence_gate_substantive_vs_fallback():
    """
    Duplicate Content Evidence Gate:
    - Substantive duplicate body (>= 80 words) across 2 distinct pages -> duplicate content defect detected.
    - Fallback error string / cookie warning (< 80 words) across 2 pages -> duplicate content defect suppressed.
    """
    substantive_text = (
        "Enterprise cloud computing infrastructure requires automated scaling, multi-region failover, "
        "and zero-trust network segmentation. Our platform orchestrates containerized workloads with "
        "millisecond latencies, continuous vulnerability monitoring, integrated compliance auditing, and "
        "distributed key-value caching. Engineered for mission-critical applications that demand five-nines "
        "availability and complete operational transparency across hybrid clouds. Learn how our unified "
        "telemetry dashboard delivers real-time observability and anomaly detection across all microservices, "
        "enabling engineering teams to diagnose performance bottlenecks and maintain optimal user experience "
        "at massive global scale with continuous deployment workflows."
    )
    substantive_p1 = PageData(
        url="https://infra.example/solutions/compute",
        status_code=200,
        raw_html=f"<html><body><h1>Compute</h1><p>{substantive_text}</p></body></html>",
        text_content=substantive_text,
        title="Enterprise Infrastructure Solutions",
        word_count=len(substantive_text.split()),
        is_spa_shell=False
    )
    substantive_p2 = PageData(
        url="https://infra.example/products/cloud-nodes",
        status_code=200,
        raw_html=f"<html><body><h1>Compute</h1><p>{substantive_text}</p></body></html>",
        text_content=substantive_text,
        title="Enterprise Infrastructure Solutions",
        word_count=len(substantive_text.split()),
        is_spa_shell=False
    )

    comparator = RenderComparator([substantive_p1, substantive_p2])
    dup_issues = [i for i in comparator.audit_render_gaps() if i.get("issue_type") == "unresolved_duplicate_content"]
    assert len(dup_issues) > 0, "Substantive duplicate content must be detected"

    # Now verify that evaluate_finding_evidence_contract accepts the substantive finding
    substantive_summary = CrawlSummary(
        target_domain="infra.example",
        start_url="https://infra.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[substantive_p1, substantive_p2]
    )
    finding = AuditFinding(
        id="F-001",
        title="Duplicate or near-identical body content across 2 page(s)",
        severity="medium",
        evidence="Observed identical text",
        suggested_action=SuggestedAction(summary="Consolidate", priority="medium"),
        affected_urls=[substantive_p1.url, substantive_p2.url]
    )
    assert evaluate_finding_evidence_contract(finding, substantive_summary) is True

    # Now test with unrendered SPA shell fallback text (< 80 words)
    fallback_p1 = PageData(
        url="https://app.example/",
        status_code=200,
        raw_html="<html><body><p>Cookies disabled. Please wait.</p></body></html>",
        text_content="Cookies disabled. Please wait.",
        word_count=4,
        is_spa_shell=True
    )
    fallback_p2 = PageData(
        url="https://app.example/privacy",
        status_code=200,
        raw_html="<html><body><p>Cookies disabled. Please wait.</p></body></html>",
        text_content="Cookies disabled. Please wait.",
        word_count=4,
        is_spa_shell=True
    )
    fallback_summary = CrawlSummary(
        target_domain="app.example",
        start_url="https://app.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[fallback_p1, fallback_p2]
    )
    fallback_finding = AuditFinding(
        id="F-002",
        title="Duplicate or near-identical body content across 2 page(s)",
        severity="medium",
        evidence="Fallback text",
        suggested_action=SuggestedAction(summary="Consolidate", priority="medium"),
        affected_urls=[fallback_p1.url, fallback_p2.url]
    )
    assert evaluate_finding_evidence_contract(fallback_finding, fallback_summary) is False


def test_proactive_faq_recommendation_contract():
    """
    Context-Aware FAQPage Proactive Recommendation:
    - If a site has genuine Q&A sections or questions in headings -> Proactive FAQPage recommendation emitted.
    - If a site does not have any Q&A sections -> Proactive FAQPage recommendation suppressed (never recommend absence as defect).
    """
    faq_html = """<!DOCTYPE html>
    <html>
    <head><title>Support FAQ | FlowStack</title></head>
    <body>
        <h1>Frequently Asked Questions</h1>
        <div class="faq-list">
            <h2>How do I export my data from FlowStack?</h2>
            <p>You can export your data anytime in JSON or CSV format from the settings dashboard.</p>
            <h2>What encryption protocols are supported?</h2>
            <p>All data is encrypted in transit using TLS 1.3 and at rest using AES-256 encryption.</p>
        </div>
    </body>
    </html>
    """
    p_faq = PageData(
        url="https://flowstack.example/faq",
        status_code=200,
        raw_html=faq_html,
        text_content="Frequently Asked Questions How do I export my data What encryption protocols are supported",
        title="Support FAQ | FlowStack",
        page_type="documentation"
    )
    faq_summary = CrawlSummary(
        target_domain="flowstack.example",
        start_url="https://flowstack.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[p_faq],
        site_type="documentation"
    )

    orch = AuditOrchestrator("https://flowstack.example/")
    report_faq = orch.run_full_audit(preloaded_summary=faq_summary)
    assert any("faqpage" in f["title"].lower() for f in report_faq["findings"]), "Should recommend FAQPage for detected Q&A content"

    # Now verify site without FAQ content receives ZERO FAQPage recommendations
    p_nofaq = PageData(
        url="https://flowstack.example/features",
        status_code=200,
        raw_html="<html><body><h1>Features</h1><p>Our features include fast data sync and secure storage.</p></body></html>",
        text_content="Features Our features include fast data sync and secure storage.",
        title="Features | FlowStack",
        page_type="landing"
    )
    nofaq_summary = CrawlSummary(
        target_domain="flowstack.example",
        start_url="https://flowstack.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[p_nofaq],
        site_type="saas"
    )
    report_nofaq = orch.run_full_audit(preloaded_summary=nofaq_summary)
    assert not any("faqpage" in f["title"].lower() for f in report_nofaq["findings"]), "Must not recommend FAQPage when no Q&A content exists"


def test_entity_clarity_unambiguous_brand_without_schema():
    """
    When an organization has clear, unambiguous brand identity in the title, headings, and body,
    missing schema.org/Organization must NOT be escalated to a Critical or High entity defect.
    """
    branded_homepage = PageData(
        url="https://zenithpay.example/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head>
            <title>ZenithPay - Global B2B Cross-Border Payment Infrastructure</title>
            <meta name="description" content="ZenithPay enables multi-currency settlements for international merchants.">
        </head>
        <body>
            <h1>ZenithPay Cross-Border Payments</h1>
            <p>Empowering financial institutions with compliant, real-time international payment processing.</p>
        </body>
        </html>
        """,
        text_content="ZenithPay - Global B2B Cross-Border Payment Infrastructure ZenithPay Cross-Border Payments",
        title="ZenithPay - Global B2B Cross-Border Payment Infrastructure",
        page_type="homepage"
    )
    validator = SchemaValidator([branded_homepage])
    issues = validator.audit_all_pages()
    org_issues = [i for i in issues if "organization" in i["title"].lower()]
    for issue in org_issues:
        assert issue["severity"] in ("medium", "low"), f"Organization schema defect must not be high on clearly branded entity: {issue}"


def test_debug_mode_trace_completeness():
    """
    --debug mode must attach complete diagnostic metadata including:
    - requested_url, final_url, target_domain, site_type
    - pages_crawled, pages_discovered, pages_queued, skipped_urls, rejection_reasons, robots_blocked_urls
    - pages_inspected (with is_spa_shell, word_count, interactive_elements_count)
    - raw_findings_count, validated_findings_count, suppressed_findings, deduped_findings_count, proactive_recommendations_count
    """
    page = PageData(
        url="https://testaudit.example/",
        status_code=200,
        raw_html="<html><body><h1>Test Page</h1><p>Test Content</p></body></html>",
        text_content="Test Page Test Content",
        title="Test Page",
        page_type="homepage"
    )
    summary = CrawlSummary(
        target_domain="testaudit.example",
        start_url="https://testaudit.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[page],
        site_type="other"
    )

    orch = AuditOrchestrator("https://testaudit.example/", debug=True)
    report = orch.run_full_audit(preloaded_summary=summary)

    assert "audit_metadata" in report
    assert "debug" in report["audit_metadata"]
    debug = report["audit_metadata"]["debug"]

    required_keys = [
        "requested_url", "final_url", "target_domain", "site_type",
        "pages_crawled", "pages_discovered", "pages_queued", "skipped_urls",
        "rejection_reasons", "robots_blocked_urls", "pages_inspected",
        "raw_findings_count", "validated_findings_count", "suppressed_findings",
        "deduped_findings_count", "proactive_recommendations_count", "final_findings"
    ]
    for key in required_keys:
        assert key in debug, f"Debug dictionary missing key: {key}"


def test_csr_page_with_thin_initial_html_but_accessible_content_zero_critical_rendering_defects():
    """
    CSR page with thin initial HTML but substantive accessible content (paragraphs and headings)
    must NOT be reported as a critical or high rendering defect.
    """
    thin_html = """<!DOCTYPE html>
    <html>
    <head><title>Accessible Web App</title></head>
    <body>
        <div id="root">
            <header><h1>Welcome to Modern TaskFlow</h1></header>
            <main>
                <p>TaskFlow is a collaborative project management application designed for high-performance engineering teams worldwide.</p>
                <p>Organize your development roadmaps, track critical bug milestones, and synchronize git repositories seamlessly.</p>
            </main>
        </div>
        <script src="/bundle.js"></script>
    </body>
    </html>
    """
    page = PageData(
        url="https://taskflow.example/",
        status_code=200,
        raw_html=thin_html,
        text_content="Welcome to Modern TaskFlow TaskFlow is a collaborative project management application designed for high-performance engineering teams worldwide. Organize your development roadmaps, track critical bug milestones, and synchronize git repositories seamlessly.",
        title="Accessible Web App",
        page_type="homepage",
        word_count=35
    )
    comparator = RenderComparator([page])
    issues = comparator.audit_render_gaps()
    assert not any(i["issue_type"] == "js_render_gap" for i in issues), f"Expected 0 rendering defects on accessible HTML, got: {issues}"


def test_genuinely_empty_js_shell_flags_rendering_finding_with_contract_evidence():
    """
    Genuinely empty JS shell (<div id='root'></div> with fallback message and no content)
    must produce a high or critical js_render_gap finding with exact measurements in evidence.
    """
    empty_html = """<!DOCTYPE html>
    <html>
    <head><title>Empty React Portal</title></head>
    <body>
        <div id="root"></div>
        <noscript>JavaScript is required to run this application.</noscript>
        <script src="/app.js"></script>
    </body>
    </html>
    """
    page = PageData(
        url="https://emptyportal.example/",
        status_code=200,
        raw_html=empty_html,
        text_content="JavaScript is required to run this application.",
        title="Empty React Portal",
        page_type="homepage",
        word_count=7
    )
    comparator = RenderComparator([page])
    issues = comparator.audit_render_gaps()
    render_issues = [i for i in issues if i["issue_type"] == "js_render_gap"]
    assert len(render_issues) == 1
    issue = render_issues[0]
    # Corrected severity model (Phase 3): never critical without a demonstrated render comparison.
    assert issue["severity"] in ("high", "medium")
    assert "words" in issue["evidence"]
    assert "initial HTTP response" in issue["evidence"]


def test_commercial_page_with_valid_cta_no_missing_cta():
    """
    Commercial SaaS homepage with explicit CTAs ("Start Free Trial", "Schedule Demo")
    must produce ZERO missing CTA findings.
    """
    page = PageData(
        url="https://saascloud.example/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>SaaSCloud Platform - Pricing and Plans</title></head>
        <body>
            <h1>Accelerate Cloud Deployments</h1>
            <p>Enterprise subscription pricing plans and automated infrastructure governance.</p>
            <div class="actions">
                <a class="btn-primary" href="/signup">Start Free Trial</a>
                <a class="btn-secondary" href="/demo">Schedule Demo</a>
            </div>
        </body>
        </html>
        """,
        text_content="SaaSCloud Platform Pricing and Plans Accelerate Cloud Deployments Enterprise subscription pricing plans Start Free Trial Schedule Demo",
        title="SaaSCloud Platform - Pricing and Plans",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([page], site_type="saas")
    issues = analyzer.audit_value_proposition_and_ctas()
    cta_issues = [i for i in issues if i["issue_type"] == "missing_clear_cta"]
    assert len(cta_issues) == 0, f"Expected 0 CTA defects on page with valid CTA, got: {cta_issues}"


def test_commercial_page_with_no_meaningful_next_action_flags_missing_cta():
    """
    Commercial homepage with commercial intent (pricing, plans) but where interactive elements
    are only noisy links (skip-to-content, announcement banner, logo) must flag missing_clear_cta.
    """
    page = PageData(
        url="https://paycloud.example/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>PayCloud - Enterprise Pricing Plans</title></head>
        <body>
            <a class="skip-to-content" href="#main">Skip to content</a>
            <div class="banner"><a href="/security">PGP signing key rotation advisory notice</a></div>
            <a class="logo" href="/"><img src="/logo.png" alt="PayCloud Logo"></a>
            <main id="main">
                <h1>Enterprise Payment Infrastructure</h1>
                <p>Compare our annual pricing plans, enterprise subscriptions, and volume fee discounts.</p>
            </main>
            <footer>
                <a href="/privacy">Privacy</a>
                <a href="/terms">Terms</a>
            </footer>
        </body>
        </html>
        """,
        text_content="PayCloud Enterprise Pricing Plans Skip to content PGP signing key rotation advisory notice Enterprise Payment Infrastructure Compare our annual pricing plans, enterprise subscriptions, and volume fee discounts. Privacy Terms",
        title="PayCloud - Enterprise Pricing Plans",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([page], site_type="saas")
    issues = analyzer.audit_value_proposition_and_ctas()
    cta_issues = [i for i in issues if i["issue_type"] == "missing_clear_cta"]
    assert len(cta_issues) == 1, f"Expected 1 CTA defect on commercial page without actions, got: {cta_issues}"
    assert "PGP" not in cta_issues[0]["evidence"], "Noisy announcement banner must not be reported as examined CTA button"
    assert "Skip to content" not in cta_issues[0]["evidence"], "Accessibility skip link must not be reported as examined CTA button"


def test_documentation_legal_developer_tool_page_exempt_from_commercial_cta():
    """
    Developer tool pages with CLI install commands (brew install gh) or documentation pages
    must NEVER be flagged for missing commercial conversion CTAs.
    """
    tool_page = PageData(
        url="https://cli.devtools.example/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>DevTools CLI - The command line for developers</title></head>
        <body>
            <h1>DevTools CLI</h1>
            <p>Take the power of DevTools to your terminal window.</p>
            <pre><code>brew install devtools</code></pre>
            <a href="/manual">Documentation</a>
            <a href="https://github.com/devtools/cli">View on GitHub</a>
        </body>
        </html>
        """,
        text_content="DevTools CLI - The command line for developers Take the power of DevTools to your terminal. brew install devtools Documentation View on GitHub",
        title="DevTools CLI - The command line for developers",
        page_type="homepage"
    )
    analyzer = EngagementAnalyzer([tool_page], site_type="other")
    issues = analyzer.audit_value_proposition_and_ctas()
    cta_issues = [i for i in issues if i["issue_type"] == "missing_clear_cta"]
    assert len(cta_issues) == 0, f"Developer tool pages with install commands must not have CTA defects: {cta_issues}"


def test_feedback_survey_widgets_not_flagged_as_faq():
    """
    Pages with feedback survey prompts ("Was this Doc helpful? Yes / No") without substantive answers
    must NOT trigger proactive FAQPage structured data recommendations.
    """
    doc_page = PageData(
        url="https://docs.framework.example/setup",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Getting Started Guide</title></head>
        <body>
            <h1>Getting Started</h1>
            <p>Instructions on installing and configuring the software development kit.</p>
            <div class="feedback-widget">
                <h3>Was this Doc helpful?</h3>
                <button>Yes</button>
                <button>No</button>
            </div>
            <div class="survey-prompt">
                <h4>Have feedback on this article?</h4>
                <button>Send Feedback</button>
            </div>
        </body>
        </html>
        """,
        text_content="Getting Started Guide Instructions on installing and configuring the software development kit. Was this Doc helpful? Yes No Have feedback on this article? Send Feedback",
        title="Getting Started Guide",
        page_type="documentation"
    )
    summary = CrawlSummary(
        target_domain="docs.framework.example",
        start_url="https://docs.framework.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[doc_page],
        site_type="documentation"
    )
    orch = AuditOrchestrator("https://docs.framework.example/")
    report = orch.run_full_audit(preloaded_summary=summary)
    faq_findings = [f for f in report["findings"] if "faqpage" in f["title"].lower()]
    assert len(faq_findings) == 0, f"Feedback surveys must not trigger FAQPage recommendations: {faq_findings}"


def test_genuine_faq_qa_pairs_produce_contextual_proactive_recommendation():
    """
    Pages with genuine Q&A pairs (question heading + substantive answer > 12 words)
    must produce a proactive FAQPage recommendation that quotes both question and answer snippets.
    """
    faq_page = PageData(
        url="https://platform.learn.example/faq",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Frequently Asked Questions</title></head>
        <body>
            <h1>Frequently Asked Questions</h1>
            <div class="faq-list">
                <h2>What is LearnPlatform and how does it work?</h2>
                <p>LearnPlatform is an open collaborative learning environment providing interactive sandbox environments, automated grading rubrics, and industry-certified curriculum modules.</p>
                <h2>How can students participate in international competitions?</h2>
                <p>Students can register their institutional credentials, join accredited student teams, and submit project repositories before the published submission deadlines.</p>
            </div>
        </body>
        </html>
        """,
        text_content="Frequently Asked Questions What is LearnPlatform and how does it work? LearnPlatform is an open collaborative learning environment providing interactive sandbox environments. How can students participate in international competitions? Students can register their institutional credentials.",
        title="Frequently Asked Questions",
        page_type="documentation"
    )
    summary = CrawlSummary(
        target_domain="platform.learn.example",
        start_url="https://platform.learn.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[faq_page],
        site_type="documentation"
    )
    orch = AuditOrchestrator("https://platform.learn.example/")
    report = orch.run_full_audit(preloaded_summary=summary)
    faq_findings = [f for f in report["findings"] if "faqpage" in f["title"].lower()]
    assert len(faq_findings) == 1, f"Expected 1 proactive FAQ finding for genuine Q&A pairs, got: {faq_findings}"
    assert "verified Q&A pairs:" in faq_findings[0]["evidence"]


def test_missing_llms_txt_on_ordinary_or_unknown_site_no_recommendation():
    """
    On an ordinary or unknown site without extensive documentation/SaaS architecture,
    missing /llms.txt must NOT be recommended.
    """
    page = PageData(
        url="https://localcafe.example/",
        status_code=200,
        raw_html="<html><body><h1>Artisan Coffee Roasters</h1><p>Freshly brewed espresso and pastries daily.</p></body></html>",
        text_content="Artisan Coffee Roasters Freshly brewed espresso and pastries daily.",
        title="Artisan Coffee Roasters",
        page_type="homepage"
    )
    summary = CrawlSummary(
        target_domain="localcafe.example",
        start_url="https://localcafe.example/",
        crawled_at="2026-09-12T12:00:00Z",
        pages=[page],
        site_type="unknown"
    )
    orch = AuditOrchestrator("https://localcafe.example/")
    report = orch.run_full_audit(preloaded_summary=summary)
    llms_findings = [f for f in report["findings"] if "/llms.txt" in f.get("title", "").lower()]
    assert len(llms_findings) == 0, f"Expected 0 /llms.txt recommendations on unknown site, got: {llms_findings}"


def test_one_ai_crawler_blocked_produces_specific_robots_finding():
    """
    When exactly one AI crawler is disallowed in robots.txt (e.g. Bytespider),
    the finding must specify that crawler by name in the title and use neutral advisory language,
    rather than claiming that all AI assistants are blocked.
    """
    robots_text = """User-agent: Bytespider
Disallow: /

User-agent: *
Allow: /
"""
    checker = RobotsChecker("https://example.com", robots_text)
    issues = checker.audit_ai_access()
    ai_issues = [i for i in issues if i["issue_type"] == "ai_crawlers_blocked"]
    assert len(ai_issues) == 1
    issue = ai_issues[0]
    assert issue["title"] == "An AI crawler is explicitly blocked by robots.txt (Bytespider)"
    assert "Bytespider" in issue["evidence"]
    assert issue["severity"] == "medium"
    assert "If intentional" in issue["action"]

