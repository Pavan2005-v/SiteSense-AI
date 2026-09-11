"""
Applicability Engine.
Determines whether each audit rule is appropriate for a given page/site
BEFORE the rule is evaluated or promoted to a finding.

Architecture position:
    crawl → site classification → page classification → APPLICABILITY ENGINE → specialist skills

This prevents false positives from rules applied to inappropriate contexts.
"""
from typing import Dict, Set


# Rule → set of applicable page types
# If a rule is not listed here, it applies to all page types.
RULE_PAGE_APPLICABILITY: Dict[str, Set[str]] = {
    # Product schema is only relevant on product detail pages (supports both 'product_detail' and legacy 'product')
    "missing_product_schema": {"product_detail", "product"},
    "incomplete_offer_schema": {"product_detail", "product"},
    "price_schema_mismatch": {"product_detail", "product", "pricing"},

    # CTA checks only on conversion-oriented pages
    "missing_clear_cta": {"homepage", "product_detail", "product", "pricing", "service", "landing"},

    # Noindex should only be flagged as defect on pages intended for public discovery
    "meta_noindex_detected": {"homepage", "product_detail", "product", "pricing", "service", "about", "article", "landing", "general"},

    # H1/value prop checks on pages where orientation matters
    "missing_h1_heading": {"homepage", "product_detail", "product", "pricing", "service", "landing",
                           "about", "article", "category"},
    "vague_buzzword_value_prop": {"homepage", "landing", "service"},

    # Navigation checks — exempt legal/privacy/terms/documentation
    "navigation_dead_ends": {"homepage", "product_detail", "product", "product_listing", "pricing",
                             "service", "about", "article", "landing", "category", "general"},

    # Breadcrumb checks — only on deep pages that are NOT legal/terms
    "missing_deep_page_orientation": {"product_detail", "product", "product_listing", "article",
                                      "documentation", "service", "category", "general"},

    # Entity clarity checks
    "unbranded_page_titles": {"homepage", "product_detail", "product", "pricing", "service",
                              "about", "landing", "category"},
    "brand_entity_collision_risk": {"homepage"},
    "homepage_lacks_substantive_entity_description": {"homepage"},

    # Freshness/corroboration applies broadly
    "stale_copyright": {"homepage", "product_detail", "product", "pricing", "service", "about",
                        "landing", "category", "general"},
    "stale_roadmap": {"homepage", "product_detail", "product", "pricing", "service", "about",
                      "landing", "article"},
    "conflicting_pricing_claims": {"homepage", "pricing", "product_detail", "product", "service"},
}

# Rule → set of applicable site types (if restricted)
RULE_SITE_APPLICABILITY: Dict[str, Set[str]] = {
    "missing_product_schema": {"ecommerce", "marketplace"},
    "incomplete_offer_schema": {"ecommerce", "marketplace"},
    "price_schema_mismatch": {"ecommerce", "marketplace", "saas"},
    "conflicting_pricing_claims": {"ecommerce", "saas", "marketplace"},
}


def is_rule_applicable(rule_id: str, page_type: str, site_type: str) -> bool:
    """
    Determines if a specific audit rule should be applied to this page/site combination.

    Returns True if the rule is applicable (should be evaluated).
    Returns False if the rule should be skipped for this context.
    """
    # Check page-type applicability
    if rule_id in RULE_PAGE_APPLICABILITY:
        if page_type not in RULE_PAGE_APPLICABILITY[rule_id]:
            return False

    # Check site-type applicability
    if rule_id in RULE_SITE_APPLICABILITY:
        if site_type not in RULE_SITE_APPLICABILITY[rule_id]:
            # If site_type is 'other' or unspecified, allow rule if page is explicitly product/product_detail
            if not (site_type in ("other", "", None) and page_type in ("product", "product_detail")):
                return False

    return True


def get_applicable_rules(page_type: str, site_type: str) -> Set[str]:
    """Returns the set of rule IDs that are applicable for this page/site combination."""
    all_rules = set(RULE_PAGE_APPLICABILITY.keys())
    return {r for r in all_rules if is_rule_applicable(r, page_type, site_type)}
