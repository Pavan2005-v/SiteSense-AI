"""
Test suite for multi-signal page-type classification and helper functions.
"""
import pytest
from skills.common.page_classifier import (
    classify_page,
    is_conversion_page,
    is_legal_page,
    is_content_page
)


def test_classify_homepage():
    assert classify_page("https://example.com/") == "homepage"
    assert classify_page("https://example.com/index.html") == "homepage"
    assert classify_page("https://example.com") == "homepage"


def test_classify_legal_and_privacy_pages():
    assert classify_page("https://example.com/privacy-policy") in ("legal", "privacy")
    assert classify_page("https://example.com/terms-of-service") in ("legal", "terms")
    assert classify_page("https://example.com/legal/disclaimer") == "legal"
    assert is_legal_page(classify_page("https://example.com/intl/en/policies/privacy/")) is True


def test_classify_product_detail_via_content_signals():
    text = "Pro Running Shoe. In stock now. Add to cart. Quantity: 1. SKU: 12345. Price: $99.99."
    p_type = classify_page(
        url="https://example.com/items/shoe-01",
        title="Pro Running Shoe",
        text_content=text
    )
    assert p_type == "product_detail"
    assert is_conversion_page(p_type) is True


def test_classify_product_listing_via_signals():
    text = "Showing results 1 to 24 of 150 items found. Sort by price. Filter by brand. Browse all."
    links = [f"https://example.com/product/{i}" for i in range(20)]
    p_type = classify_page(
        url="https://example.com/catalog/footwear",
        title="All Footwear",
        text_content=text,
        internal_links=links
    )
    assert p_type in ("product_listing", "category")


def test_classify_documentation_via_schema():
    raw_json = ['{"@context": "https://schema.org", "@type": "FAQPage", "mainEntity": []}']
    p_type = classify_page(
        url="https://example.com/support/questions",
        title="Frequently Asked Questions",
        json_ld_raw=raw_json
    )
    assert p_type == "documentation"
    assert is_conversion_page(p_type) is False
    assert is_content_page(p_type) is True


def test_is_conversion_page_logic():
    assert is_conversion_page("homepage") is True
    assert is_conversion_page("pricing") is True
    assert is_conversion_page("product_detail") is True
    assert is_conversion_page("privacy") is False
    assert is_conversion_page("legal") is False
    assert is_conversion_page("documentation") is False

