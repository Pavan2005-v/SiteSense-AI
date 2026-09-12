"""
Regression tests for semantic FAQ applicability detection (Phase 6).

Key invariants:
- Genuine FAQ pages (3+ verified Q&A pairs or 2+ pairs with explicit FAQ structure)
  qualify for a PROACTIVE FAQPage recommendation, never a defect.
- Article headlines, feedback widgets, support links, and isolated questions are
  rejected and produce NO recommendation.
- FAQPage JSON-LD is never required merely because question-shaped text exists.
"""
import pytest
from bs4 import BeautifulSoup
from skills.common.models import PageData, CrawlSummary
from skills.audit_orchestrator.scripts.orchestrate import (
    extract_verified_faq_pairs,
    generate_proactive_recommendations,
)
from tests.fixtures import FAQ_REAL_PAGE_HTML, ARTICLE_QUESTION_HEADLINE_HTML


def _pairs(html):
    return extract_verified_faq_pairs(BeautifulSoup(html, "html.parser"))


def _summary(pages, site_type="other"):
    return CrawlSummary(
        target_domain="example.com",
        start_url="https://example.com",
        crawled_at="2026-09-12T00:00:00Z",
        pages=pages,
        site_type=site_type,
    )


def test_real_faq_page_yields_proactive_recommendation():
    page = PageData(url="https://example.com/faq", status_code=200, raw_html=FAQ_REAL_PAGE_HTML, page_type="support")
    pairs = _pairs(FAQ_REAL_PAGE_HTML)
    assert len(pairs) >= 3
    proactive = generate_proactive_recommendations(_summary([page]))
    faq_recs = [f for f in proactive if "FAQPage" in f.title]
    assert len(faq_recs) == 1
    assert faq_recs[0].is_proactive
    assert "Proactive:" in faq_recs[0].title
    # Evidence must cite the actual page
    assert "https://example.com/faq" in ",".join(faq_recs[0].affected_urls)


def test_one_isolated_question_produces_no_recommendation():
    html = """<html><body><h1>Support</h1>
        <h2>How do I reset my password?</h2>
        <p>Open the login page and click Forgot password to receive a secure reset link by email within a few minutes.</p>
        <h2>Contact options</h2><p>Email, phone, and chat support are available 24/7.</p>
    </body></html>"""
    page = PageData(url="https://example.com/support", status_code=200, raw_html=html, page_type="support")
    assert not generate_proactive_recommendations(_summary([page]))


def test_article_question_headline_is_not_faq():
    page = PageData(url="https://example.com/blog/post", status_code=200, raw_html=ARTICLE_QUESTION_HEADLINE_HTML, page_type="article")
    assert _pairs(ARTICLE_QUESTION_HEADLINE_HTML) == []
    assert not generate_proactive_recommendations(_summary([page]))


def test_need_more_help_and_was_this_helpful_rejected():
    html = """<html><body>
        <h2>Need more help?</h2><p>If you run into playback area verification issues, need help signing in, or want to report a problem, our support desk can assist you today.</p>
        <h2>Was this helpful?</h2><p>Yes / No</p>
    </body></html>"""
    assert _pairs(html) == []


def test_interview_style_content_is_not_faq():
    html = """<html><body>
        <h2>Why did you start the company?</h2>
        <p>We started the company after a decade in logistics operations, watching teams lose hours every week to manual spreadsheet handoffs between warehouses.</p>
        <h2>What does a normal day look like?</h2>
        <p>Mornings are spent reviewing operational dashboards with the on-call engineers, and afternoons usually involve customer interviews or roadmap planning sessions.</p>
    </body></html>"""
    # Interview content with "you" pronouns may pair, but 2 loose pairs without strong
    # structure must NOT qualify for the FAQPage recommendation.
    page = PageData(url="https://example.com/interview", status_code=200, raw_html=html, page_type="article")
    assert not generate_proactive_recommendations(_summary([page]))


def test_support_page_genuine_faq_qualifies():
    html = """<html><body>
        <div class="faq-section">
            <h2>What is your refund policy?</h2>
            <p>We offer a full refund within 30 days of purchase for annual plans. Monthly subscriptions can be cancelled anytime and remain active until the end of the billing period.</p>
            <h2>Can I change my plan later?</h2>
            <p>Yes, you can upgrade or downgrade your plan at any time from your account settings page. Changes are prorated automatically on your next invoice.</p>
        </div>
    </body></html>"""
    page = PageData(url="https://example.com/help/faq", status_code=200, raw_html=html, page_type="support")
    assert len(_pairs(html)) >= 2
    recs = generate_proactive_recommendations(_summary([page]))
    faq_recs = [f for f in recs if "FAQPage" in f.title]
    assert len(faq_recs) == 1


def test_documentation_qa_loose_pairs_do_not_qualify():
    html = """<html><body>
        <h2>What is a transform?</h2>
        <p>A transform is a reusable mapping between source and destination schemas, defined once and applied to every sync run automatically.</p>
        <h2>What is a connector?</h2>
        <p>A connector packages authentication and schema discovery for one data source so pipelines can read from it without custom code.</p>
    </body></html>"""
    # Two loose heading pairs, no explicit FAQ structure -> does not qualify.
    page = PageData(url="https://example.com/docs/concepts", status_code=200, raw_html=html, page_type="documentation")
    assert not generate_proactive_recommendations(_summary([page]))


def test_ecommerce_faq_page_qualifies_with_details_structure():
    html = """<html><body>
        <section aria-label="FAQ">
            <details><summary>What is the return window?</summary>Returns are accepted within 60 days of delivery provided tags are attached and the item is unworn.</details>
            <details><summary>Do you ship internationally?</summary>We ship to 42 countries with duties calculated at checkout, and most orders arrive within seven business days.</details>
        </section>
    </body></html>"""
    page = PageData(url="https://example.com/store/faq", status_code=200, raw_html=html, page_type="support")
    assert len(_pairs(html)) >= 2
    recs = generate_proactive_recommendations(_summary([page]))
    assert any("FAQPage" in f.title for f in recs)


def test_existing_faq_schema_not_recommended_again():
    html = FAQ_REAL_PAGE_HTML.replace("</head>", "<script type='application/ld+json'>{\"@type\":\"FAQPage\"}</script></head>")
    page = PageData(url="https://example.com/faq", status_code=200, raw_html=html, page_type="support")
    assert not generate_proactive_recommendations(_summary([page]))