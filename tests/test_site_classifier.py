"""
Test suite for site-type classification across ecommerce, SaaS, corporate, etc.
"""
import pytest
from skills.common.models import PageData
from skills.common.site_classifier import classify_site


def test_classify_ecommerce_site():
    pages = [
        PageData(url="https://shop.example/", status_code=200, page_type="homepage"),
        PageData(
            url="https://shop.example/products/shoe",
            status_code=200,
            page_type="product_detail",
            json_ld_raw=['{"@type": "Product", "name": "Shoe"}']
        ),
        PageData(
            url="https://shop.example/products/shirt",
            status_code=200,
            page_type="product_detail",
            json_ld_raw=['{"@type": "Product", "name": "Shirt"}']
        )
    ]
    site_type = classify_site(pages, "shop.example")
    assert site_type == "ecommerce"


def test_classify_saas_site():
    pages = [
        PageData(
            url="https://saas.example/",
            status_code=200,
            page_type="homepage",
            title="Cloud Platform SaaS | Automation App",
            text_content="Start free trial. Get started today. API and integrations for automated cloud workflows."
        ),
        PageData(
            url="https://saas.example/pricing",
            status_code=200,
            page_type="pricing",
            text_content="Tiered monthly plans. Free trial available."
        )
    ]
    site_type = classify_site(pages, "saas.example")
    assert site_type == "saas"


def test_classify_corporate_site():
    pages = [
        PageData(url="https://corp.example/", status_code=200, page_type="homepage"),
        PageData(
            url="https://corp.example/about",
            status_code=200,
            page_type="about",
            text_content="Our company was founded in 2010. Our team and leadership headquarters."
        ),
        PageData(
            url="https://corp.example/contact",
            status_code=200,
            page_type="contact",
            text_content="Contact our global headquarters."
        )
    ]
    site_type = classify_site(pages, "corp.example")
    assert site_type == "corporate"

