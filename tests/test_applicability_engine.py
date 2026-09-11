"""
Test suite for the Applicability Engine gating logic.
"""
import pytest
from skills.common.applicability_engine import is_rule_applicable, get_applicable_rules


def test_product_schema_rule_applicability():
    # Applicable on ecommerce product detail page
    assert is_rule_applicable("missing_product_schema", "product_detail", "ecommerce") is True
    # NOT applicable on corporate homepage
    assert is_rule_applicable("missing_product_schema", "homepage", "corporate") is False
    # NOT applicable on legal/privacy page
    assert is_rule_applicable("missing_product_schema", "legal", "ecommerce") is False
    # NOT applicable on a pure documentation site
    assert is_rule_applicable("missing_product_schema", "documentation", "documentation") is False


def test_cta_rule_applicability():
    # Applicable on conversion pages
    assert is_rule_applicable("missing_clear_cta", "homepage", "saas") is True
    assert is_rule_applicable("missing_clear_cta", "pricing", "saas") is True
    assert is_rule_applicable("missing_clear_cta", "product_detail", "ecommerce") is True
    # NOT applicable on legal or policy pages
    assert is_rule_applicable("missing_clear_cta", "legal", "ecommerce") is False
    assert is_rule_applicable("missing_clear_cta", "privacy", "saas") is False
    assert is_rule_applicable("missing_clear_cta", "documentation", "saas") is False


def test_dead_end_rule_exemptions():
    # Legal and privacy pages must be exempt from dead end checks
    assert is_rule_applicable("navigation_dead_ends", "legal", "corporate") is False
    assert is_rule_applicable("navigation_dead_ends", "privacy", "saas") is False
    assert is_rule_applicable("navigation_dead_ends", "terms", "ecommerce") is False
    # Core pages are checked
    assert is_rule_applicable("navigation_dead_ends", "homepage", "saas") is True
    assert is_rule_applicable("navigation_dead_ends", "product_detail", "ecommerce") is True


def test_get_applicable_rules_returns_curated_set():
    legal_rules = get_applicable_rules("legal", "corporate")
    assert "missing_product_schema" not in legal_rules
    assert "missing_clear_cta" not in legal_rules
    assert "navigation_dead_ends" not in legal_rules

    product_rules = get_applicable_rules("product_detail", "ecommerce")
    assert "missing_product_schema" in product_rules
    assert "missing_clear_cta" in product_rules

