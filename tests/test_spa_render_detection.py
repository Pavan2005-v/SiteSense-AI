"""
Regression tests for JavaScript / SPA rendering detection (Phase 3).

Key invariants:
- A genuine empty shell is reported, but NEVER critical without a demonstrated
  initial-vs-rendered comparison (no browser rendering exists in this audit).
- Meaningful SPA HTML, partial JS enhancement, SSR+JS pages, and non-homepage
  pages with thin initial HTML are NOT classified as empty shells.
- Rendering unavailability is stated as a limitation, never inferred as a defect
  against rendered content.
"""
import pytest
from bs4 import BeautifulSoup
from skills.common.models import PageData
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator
from tests.fixtures import (
    SPA_EMPTY_SHELL_HTML,
    SPA_MEANINGFUL_HTML,
    SPA_PARTIAL_ENHANCEMENT_HTML,
    PERFECT_HOMEPAGE_HTML,
)


def _page(html, url="https://example.com/", page_type="homepage", **kwargs):
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return PageData(url=url, status_code=200, raw_html=html, text_content=text, page_type=page_type, **kwargs)


def test_genuine_empty_shell_is_reported_never_critical():
    page = _page(SPA_EMPTY_SHELL_HTML, page_type="homepage")
    issues = RenderComparator([page]).audit_render_gaps()
    gap = next((i for i in issues if i["issue_type"] == "js_render_gap"), None)
    gap = next((i for i in issues if i["issue_type"] == "js_render_gap"), None)
    assert gap is not None
    assert gap["severity"] == "high"  # homepage affected, no rendering comparison
    assert "cannot read" not in gap["evidence"].lower()


def test_meaningful_spa_html_is_not_a_defect():
    page = _page(SPA_MEANINGFUL_HTML, page_type="homepage")
    page.internal_links = [f"https://example.com/{i}" for i in range(10)]
    issues = RenderComparator([page]).audit_render_gaps()
    assert not any(i["issue_type"] == "js_render_gap" for i in issues)


def test_partial_js_enhancement_is_not_a_defect():
    # Thin page but meaningful: descriptive title, meta description, nav, heading, prose.
    page = _page(SPA_PARTIAL_ENHANCEMENT_HTML, page_type="general")
    page.meta_description = "PixelForge Studio designs brand identities, packaging, and digital experiences for independent coffee roasters."
    issues = RenderComparator([page]).audit_render_gaps()
    assert not any(i["issue_type"] == "js_render_gap" for i in issues)


def test_ssr_with_js_is_not_a_defect():
    page = _page(PERFECT_HOMEPAGE_HTML, page_type="homepage")
    issues = RenderComparator([page]).audit_render_gaps()
    assert not any(i["issue_type"] == "js_render_gap" for i in issues)


def test_non_homepage_shell_is_medium():
    page = _page(SPA_EMPTY_SHELL_HTML, url="https://example.com/app/dashboard", page_type="general")
    issues = RenderComparator([page]).audit_render_gaps()
    gap = next((i for i in issues if i["issue_type"] == "js_render_gap"), None)
    assert gap is not None
    assert gap["severity"] == "medium"


def test_rendering_unavailability_is_declared_as_limitation():
    page = _page(SPA_EMPTY_SHELL_HTML, page_type="homepage")
    issues = RenderComparator([page]).audit_render_gaps()
    gap = next(i for i in issues if i["issue_type"] == "js_render_gap")
    assert "limitations" in gap
    assert "rendering" in gap["limitations"].lower()
    # Confidence must not be high: we cannot compare rendered vs initial content
    assert gap["confidence"] != "high"
