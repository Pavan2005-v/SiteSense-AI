"""
Test suite for structured-data-audit skill.
"""
import pytest
from skills.common.models import PageData
from skills.structured_data_audit.scripts.schema_extractor import SchemaExtractor
from skills.structured_data_audit.scripts.schema_validator import SchemaValidator
from tests.fixtures import (
    ECOMMERCE_PRODUCT_PAGE_NO_SCHEMA_HTML,
    ECOMMERCE_PRODUCT_PAGE_WITH_SCHEMA_HTML,
    MALFORMED_JSONLD_HTML,
    PERFECT_HOMEPAGE_HTML
)


def test_missing_product_schema_flagged_with_evidence():
    # Exactly matching Adobe PDF example
    page = PageData(
        url="https://sportco.example/products/running-shoes",
        status_code=200,
        raw_html=ECOMMERCE_PRODUCT_PAGE_NO_SCHEMA_HTML,
        text_content="Pro Running Shoes $129.99 High-performance running shoes Buy Now",
        page_type="product"
    )
    validator = SchemaValidator([page])
    issues = validator.audit_all_pages()

    assert any(i["issue_type"] == "missing_product_schema" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "missing_product_schema")
    assert issue["severity"] == "high"
    assert "Crawled 1 product pages; 1/1 contain no schema.org Product or Offer markup" in issue["evidence"]
    assert "Add valid schema.org Product and Offer JSON-LD" in issue["action"]


def test_valid_product_schema_passes_cleanly():
    page = PageData(
        url="https://sportco.example/products/running-shoes",
        status_code=200,
        raw_html=ECOMMERCE_PRODUCT_PAGE_WITH_SCHEMA_HTML,
        text_content="Pro Running Shoes $129.99 Buy Now",
        page_type="product"
    )
    validator = SchemaValidator([page])
    issues = validator.audit_all_pages()
    assert not any(i["issue_type"] == "missing_product_schema" for i in issues)


def test_jsonld_syntax_error_detected():
    extractor = SchemaExtractor(MALFORMED_JSONLD_HTML, "https://example.com/broken")
    assert len(extractor.syntax_errors) == 1
    assert "error" in extractor.syntax_errors[0]


def test_homepage_organization_schema_detection():
    # Perfect homepage has Organization schema
    page = PageData(
        url="https://acmecloud.io/",
        status_code=200,
        raw_html=PERFECT_HOMEPAGE_HTML,
        text_content="AcmeCloud Enterprise Cloud Management",
        page_type="homepage"
    )
    validator = SchemaValidator([page])
    issues = validator.audit_all_pages()
    assert not any(i["issue_type"] == "missing_org_schema" for i in issues)

