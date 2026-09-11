"""
Validates structured data against Schema.org specifications and page-type expectations.
"""
from typing import List, Dict, Any, Optional
import re
from .schema_extractor import SchemaExtractor
from skills.common.applicability_engine import is_rule_applicable


class SchemaValidator:
    def __init__(self, pages: List[Any], site_type: str = 'other'):
        self.pages = pages
        self.site_type = site_type

    def audit_all_pages(self) -> List[Dict[str, Any]]:
        findings = []

        product_pages = []
        product_pages_without_schema = []
        product_schemas_with_missing_offers = []
        syntax_error_items = []
        homepage_missing_org = False
        homepage_url = ""

        for p in self.pages:
            extractor = SchemaExtractor(p.raw_html, p.url)
            
            # 1. Check for Syntax Errors
            for err in extractor.syntax_errors:
                syntax_error_items.append(err)

            # 2. Check Homepage Schemas
            if p.page_type == "homepage":
                homepage_url = p.url
                org_schemas = extractor.get_schemas_by_type("Organization") + extractor.get_schemas_by_type("Corporation") + extractor.get_schemas_by_type("LocalBusiness")
                if not org_schemas:
                    homepage_missing_org = True

            # 3. Check Product Pages
            if p.page_type in ("product_detail", "product"):
                if is_rule_applicable("missing_product_schema", p.page_type, self.site_type):
                    product_pages.append(p)
                    products = extractor.get_schemas_by_type("Product")
                    if not products:
                        product_pages_without_schema.append(p.url)
                    else:
                        for prod in products:
                            offers = prod.get("offers")
                            if not offers:
                                product_schemas_with_missing_offers.append((p.url, prod.get("name", "Unnamed Product")))
                            else:
                                # Verify offer has price
                                if isinstance(offers, dict):
                                    if "price" not in offers and "priceSpecification" not in offers:
                                        product_schemas_with_missing_offers.append((p.url, prod.get("name", "Unnamed Product")))

            # 4. Consistency check: price in schema vs page visible text
            if is_rule_applicable("price_schema_mismatch", p.page_type, self.site_type):
                products = extractor.get_schemas_by_type("Product")
                for prod in products:
                    offers = prod.get("offers")
                    if isinstance(offers, dict) and "price" in offers:
                        schema_price = str(offers["price"]).strip()
                        # Check if schema price exists somewhere in visible text
                        # If page contains explicit numbers like $99 but schema says 19, flag potential discrepancy
                        if schema_price and schema_price not in p.text_content:
                            # Only flag if there are obvious dollar amounts on page
                            dollar_matches = re.findall(r"\$\s*(\d+(?:\.\d{2})?)", p.text_content)
                            if dollar_matches and schema_price not in dollar_matches:
                                findings.append({
                                    "issue_type": "price_schema_mismatch",
                                    "severity": "high",
                                    "title": f"Structured data price mismatch on {p.url}",
                                    "evidence": f"Product schema specifies price '{schema_price}', but page text displays visible prices: {', '.join(dollar_matches[:3])}.",
                                    "action": "Synchronize JSON-LD Product 'offers.price' with the rendered text price on the detail page to prevent AI hallucination or distrust.",
                                    "why_it_matters": "Mismatched prices can cause AI agents to hallucinate the wrong price or lower trust in the site.",
                                    "confidence": "medium",
                                    "root_cause": "JSON-LD and visible text are out of sync.",
                                    "affected_urls": [p.url]
                                })

        # Process syntax errors
        if syntax_error_items:
            sample_errors = [f"{e['url']}: {e['error']}" for e in syntax_error_items[:2]]
            urls = list(set([e['url'] for e in syntax_error_items]))
            findings.append({
                "issue_type": "jsonld_syntax_error",
                "severity": "high",
                "title": f"Malformed JSON-LD syntax on {len(urls)} page(s)",
                "evidence": f"JSON-LD parser encountered syntax errors on {len(syntax_error_items)} block(s). Examples: {'; '.join(sample_errors)}.",
                "action": "Fix JSON syntax errors (e.g. remove trailing commas, escape special characters, ensure valid JSON syntax) so search parsers can extract the markup.",
                "why_it_matters": "Syntax errors prevent AI crawlers from parsing the JSON-LD payload entirely.",
                "confidence": "high",
                "root_cause": "Improper escaping, trailing commas, or invalid structure in JSON-LD injection.",
                "affected_urls": urls
            })

        # Process missing Product schema on product pages
        if product_pages and product_pages_without_schema:
            ratio = f"{len(product_pages_without_schema)}/{len(product_pages)}"
            sample_urls = product_pages_without_schema[:3]
            findings.append({
                "issue_type": "missing_product_schema",
                "severity": "high",
                "title": f"No JSON-LD structured data on product pages ({ratio} missing)",
                "evidence": f"Crawled {len(product_pages)} product pages; {ratio} contain no schema.org Product or Offer markup. Sample affected pages: {', '.join(sample_urls)}.",
                "action": "Add valid schema.org Product and Offer JSON-LD to every product page, including name, description, image, price, priceCurrency, and availability.",
                "why_it_matters": "Product structured data is essential for AI agents and search engines to understand product offerings.",
                "confidence": "high",
                "root_cause": "Missing or improperly configured schema generation on product detail templates.",
                "affected_urls": product_pages_without_schema
            })

        # Process products with missing Offer
        if product_schemas_with_missing_offers:
            sample_names = [f"{name} ({url})" for url, name in product_schemas_with_missing_offers[:3]]
            urls = list(set([url for url, name in product_schemas_with_missing_offers]))
            findings.append({
                "issue_type": "incomplete_offer_schema",
                "severity": "medium",
                "title": f"Product schema missing 'offers' pricing on {len(urls)} item(s)",
                "evidence": f"Product JSON-LD found but lacks pricing/availability offers on: {'; '.join(sample_names)}.",
                "action": "Embed an 'offers' object within each Product schema with valid 'price', 'priceCurrency', and 'availability'.",
                "why_it_matters": "Without Offer data, pricing and availability cannot be definitively extracted by AI clients.",
                "confidence": "high",
                "root_cause": "Product schema generated without corresponding Offer details.",
                "affected_urls": urls
            })

        # Process missing Organization on homepage
        if homepage_missing_org:
            findings.append({
                "issue_type": "missing_org_schema",
                "severity": "medium",
                "title": "Homepage lacks Organization structured data",
                "evidence": f"Homepage ({homepage_url or 'root'}) does not declare schema.org/Organization or LocalBusiness markup.",
                "action": "Add an Organization JSON-LD script to the homepage with name, url, logo, description, and authoritative sameAs profiles (Wikidata, LinkedIn).",
                "why_it_matters": "Organization schema establishes the core entity identity, which builds AI agent trust.",
                "confidence": "medium",
                "root_cause": "Homepage template is missing the Organization JSON-LD script.",
                "affected_urls": [homepage_url] if homepage_url else []
            })

        return findings
