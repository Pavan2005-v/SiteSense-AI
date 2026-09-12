"""
Regression tests for context-aware canonical URL analysis (Phase 5).

Key invariants:
- A canonical pointing to a DIFFERENT valid preferred URL is NOT a defect.
- True canonical defects require direct evidence: multiple conflicting tags on the
  same page, malformed canonical hrefs, or a demonstrated canonical cycle.
- Canonical chains (A -> B -> C) are valid and never reported.
- Trailing slashes, fragments, and query normalization are handled consistently.
"""
import pytest
from bs4 import BeautifulSoup
from skills.common.models import PageData
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator


def _page(url, canonical_href=None, body="Content", **kwargs):
    head = ""
    if canonical_href is not None:
        head = f"<link rel='canonical' href='{canonical_href}'>"
    html = f"<html><head>{head}</head><body><p>{body}</p></body></html>"
    text = BeautifulSoup(html, "html.parser").get_text(" ", strip=True)
    return PageData(url=url, status_code=200, raw_html=html, text_content=text, **kwargs)


def _no_conflicts(pages):
    issues = RenderComparator(pages).audit_render_gaps()
    return [i for i in issues if i["issue_type"] == "conflicting_canonical"]


def test_valid_different_canonical_url_not_a_defect():
    pages = [
        _page("https://example.com/a", canonical_href="https://example.com/preferred/a"),
        _page("https://example.com/b", canonical_href="https://example.com/preferred/b"),
    ]
    assert _no_conflicts(pages) == []


def test_same_page_canonical_not_a_defect():
    pages = [_page("https://example.com/page", canonical_href="https://example.com/page")]
    assert _no_conflicts(pages) == []


def test_two_canonical_tags_different_targets_is_defect():
    html = ("<html><head>"
            "<link rel='canonical' href='https://example.com/x'>"
            "<link rel='canonical' href='https://example.com/y'>"
            "</head><body><p>Content</p></body></html>")
    page = PageData(url="https://example.com/dup", status_code=200, raw_html=html, text_content="Content")
    conflicts = _no_conflicts([page])
    assert len(conflicts) == 1
    assert "Multiple canonical tags" in conflicts[0]["evidence"]


def test_canonical_cycle_a_to_b_to_a_is_defect():
    pages = [
        _page("https://example.com/a", canonical_href="https://example.com/b", body="A content that is long enough to be substantive for analysis."),
        _page("https://example.com/b", canonical_href="https://example.com/a", body="B content that is long enough to be substantive for analysis."),
    ]
    conflicts = _no_conflicts(pages)
    assert len(conflicts) == 1
    assert "circular" in conflicts[0]["evidence"].lower() or "cycle" in conflicts[0]["evidence"].lower()


def test_canonical_chain_a_to_b_to_c_is_not_a_defect():
    # A -> B -> C where C does not point back: a valid chain, NOT a cycle.
    pages = [
        _page("https://example.com/a", canonical_href="https://example.com/b", body="Alpha page content."),
        _page("https://example.com/b", canonical_href="https://example.com/c", body="Beta page content."),
        _page("https://example.com/c", canonical_href="https://example.com/c", body="Gamma page content."),
    ]
    assert _no_conflicts(pages) == []


def test_localized_master_canonical_not_a_defect():
    pages = [
        _page("https://example.com/howitworks/copyright", canonical_href="https://example.com/intl/ALL_in/howitworks/copyright/"),
    ]
    assert _no_conflicts(pages) == []


def test_trailing_slash_and_fragment_normalization():
    # Canonical to the same page with trailing slash/fragment differences: equivalent target
    pages = [
        _page("https://example.com/page", canonical_href="https://example.com/page/"),
    ]
    assert _no_conflicts(pages) == []


def test_relative_canonical_resolved_not_a_defect():
    pages = [
        _page("https://example.com/section/article", canonical_href="/section/article-canonical"),
    ]
    assert _no_conflicts(pages) == []


def test_malformed_canonical_href_is_defect():
    pages = [
        _page("https://example.com/broken", canonical_href="none"),
    ]
    conflicts = _no_conflicts(pages)
    assert len(conflicts) == 1
    assert "alformed" in conflicts[0]["evidence"]
