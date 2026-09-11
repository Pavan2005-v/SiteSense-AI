"""
Test suite for URL normalization and domain validation utilities.
"""
import pytest
from skills.common.url_utils import normalize_url, dedupe_urls, urls_belong_to_domain, extract_domain


def test_normalize_url_removes_fragments():
    url = "https://example.com/products/shoes#specifications"
    assert normalize_url(url) == "https://example.com/products/shoes"


def test_normalize_url_strips_trailing_slash_except_root():
    assert normalize_url("https://example.com/about/") == "https://example.com/about"
    assert normalize_url("https://example.com/") == "https://example.com/"
    assert normalize_url("https://example.com") == "https://example.com/"


def test_normalize_url_lowercases_scheme_and_domain():
    url = "HTTPS://WWW.EXAMPLE.COM/Path/To/Page"
    assert normalize_url(url) == "https://www.example.com/Path/To/Page"


def test_normalize_url_sorts_query_parameters():
    url1 = "https://example.com/search?b=2&a=1"
    url2 = "https://example.com/search?a=1&b=2"
    assert normalize_url(url1) == normalize_url(url2)


def test_dedupe_urls_preserves_order():
    urls = [
        "https://example.com/about",
        "https://example.com/about/",
        "https://example.com/about#team",
        "https://example.com/pricing",
        "https://example.com/pricing/"
    ]
    deduped = dedupe_urls(urls)
    assert len(deduped) == 2
    assert deduped == ["https://example.com/about", "https://example.com/pricing"]


def test_urls_belong_to_domain():
    urls = [
        "https://example.com/about",
        "https://sub.example.com/docs",
        "https://evil.com/phish",
        "https://otherdomain.org/"
    ]
    matched = urls_belong_to_domain(urls, "example.com")
    assert "https://example.com/about" in matched
    assert "https://sub.example.com/docs" in matched
    assert "https://evil.com/phish" not in matched
    assert "https://otherdomain.org/" not in matched

