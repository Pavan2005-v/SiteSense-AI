"""
Synthetic Generalization Test Suite for Unseen Site Archetypes.

Tests verify that the audit engine generalizes correctly to arbitrary, unseen websites:
1. Healthy vs broken e-commerce catalog (PDP schema & breadcrumbs)
2. Healthy vs JS-rendered empty SPA documentation (render gap heuristics)
3. Corporate site: clear entity info vs ambiguous dictionary name
4. News/publisher site: healthy hierarchy vs weak navigation & dead ends
5. SaaS landing page: clear conversion pathway vs missing CTA on commercial intent
6. Informative diagrams missing alt text vs decorative icons with presentation role
7. Unresolved duplicate content vs unique pages omitting canonical tags
"""
import pytest
from skills.common.models import PageData, CrawlSummary
from skills.structured_data_audit.scripts.schema_validator import SchemaValidator
from skills.entity_clarity_audit.scripts.disambiguation_rules import DisambiguationRules
from skills.engagement_audit.scripts.engagement_analyzer import EngagementAnalyzer
from skills.engagement_audit.scripts.navigation_graph import NavigationGraph
from skills.crawl_render_audit.scripts.render_comparator import RenderComparator
from skills.audit_orchestrator.scripts.orchestrate import AuditOrchestrator


def test_ecommerce_catalog_broken_vs_healthy():
    """
    E-Commerce Catalog Generalization:
    - Broken: PDP with price and buy intent, but zero Schema.org Product markup and missing breadcrumbs.
    - Healthy: PDP with valid Schema.org Product JSON-LD, Offer, and BreadcrumbList navigation.
    """
    broken_pdp = PageData(
        url="https://store.unseentech.example/shop/audio/wireless-headphones",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Acoustic Pro Wireless Headphones - Store</title></head>
        <body>
            <h1>Acoustic Pro Wireless Headphones</h1>
            <p class="price">$199.99</p>
            <p>Studio-grade active noise cancelling headphones with 40-hour battery life.</p>
            <button class="add-to-cart">Add to Cart</button>
            <a href="/">Home</a>
        </body>
        </html>
        """,
        text_content="Acoustic Pro Wireless Headphones $199.99 Studio-grade active noise cancelling headphones Add to Cart Home",
        title="Acoustic Pro Wireless Headphones - Store",
        page_type="product_detail",
        internal_links=["https://store.unseentech.example/"]
    )

    # 1. Broken PDP must be flagged for missing Product schema and missing breadcrumbs
    validator = SchemaValidator([broken_pdp])
    schema_issues = validator.audit_all_pages()
    assert any(i["issue_type"] == "missing_product_schema" for i in schema_issues)

    nav_graph = NavigationGraph([broken_pdp])
    nav_issues = nav_graph.audit_navigation_and_orientation()
    assert any(i["issue_type"] == "missing_deep_page_orientation" for i in nav_issues)

    # 2. Healthy PDP with complete JSON-LD and breadcrumbs
    healthy_pdp = PageData(
        url="https://store.unseentech.example/shop/audio/wireless-headphones",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head>
            <title>Acoustic Pro Wireless Headphones | UnseenTech Audio</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Product",
                "name": "Acoustic Pro Wireless Headphones",
                "description": "Studio-grade active noise cancelling headphones.",
                "offers": {
                    "@type": "Offer",
                    "price": "199.99",
                    "priceCurrency": "USD",
                    "availability": "https://schema.org/InStock"
                }
            }
            </script>
        </head>
        <body>
            <nav aria-label="breadcrumb">
                <ol itemscope itemtype="https://schema.org/BreadcrumbList">
                    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                        <a itemprop="item" href="/"><span itemprop="name">Home</span></a>
                        <meta itemprop="position" content="1" />
                    </li>
                    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                        <a itemprop="item" href="/shop/audio"><span itemprop="name">Audio</span></a>
                        <meta itemprop="position" content="2" />
                    </li>
                    <li itemprop="itemListElement" itemscope itemtype="https://schema.org/ListItem">
                        <span itemprop="name">Headphones</span>
                        <meta itemprop="position" content="3" />
                    </li>
                </ol>
            </nav>
            <h1>Acoustic Pro Wireless Headphones</h1>
            <p>$199.99</p>
            <button>Add to Cart</button>
        </body>
        </html>
        """,
        text_content="Home Audio Headphones Acoustic Pro Wireless Headphones $199.99 Add to Cart",
        title="Acoustic Pro Wireless Headphones | UnseenTech Audio",
        page_type="product_detail",
        internal_links=["https://store.unseentech.example/", "https://store.unseentech.example/shop/audio"]
    )

    validator_healthy = SchemaValidator([healthy_pdp])
    assert not any(i["issue_type"] == "missing_product_schema" for i in validator_healthy.audit_all_pages())

    nav_graph_healthy = NavigationGraph([healthy_pdp])
    assert not any(i["issue_type"] == "missing_deep_page_orientation" for i in nav_graph_healthy.audit_navigation_and_orientation())


def test_spa_documentation_broken_vs_healthy():
    """
    SPA vs SSR Documentation Generalization:
    - Broken: SPA with empty DOM container (#root) relying entirely on bundle.js.
    - Healthy: Pre-rendered documentation with static text, headings, and code blocks.
    """
    spa_empty = PageData(
        url="https://docs.unseenframework.io/guide/getting-started",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head>
            <title>UnseenFramework Docs</title>
            <script src="/static/js/main.b83fa1.js" defer></script>
            <script src="/static/js/vendor.77a23c.js" defer></script>
        </head>
        <body>
            <div id="root"></div>
            <noscript>You need to enable JavaScript to view documentation.</noscript>
        </body>
        </html>
        """,
        text_content="You need to enable JavaScript to view documentation.",
        page_type="documentation"
    )

    comparator = RenderComparator([spa_empty])
    issues = comparator.audit_render_gaps()
    assert any(i["issue_type"] == "js_render_gap" for i in issues)
    issue = next(i for i in issues if i["issue_type"] == "js_render_gap")
    # Corrected severity model (Phase 3): critical is reserved for demonstrated render
    # comparison; observed empty initial HTML yields high (primary entry pages) / medium.
    assert issue["severity"] in ("high", "medium")
    assert "initial HTTP response" in issue["evidence"].lower() or "javascript" in issue["evidence"].lower()

    # Pre-rendered documentation
    ssr_docs = PageData(
        url="https://docs.unseenframework.io/guide/getting-started",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Getting Started | UnseenFramework Docs</title></head>
        <body>
            <header><a href="/">Home</a><a href="/guide">Guide</a></header>
            <main>
                <h1>Getting Started with UnseenFramework</h1>
                <p>Install the CLI using npm or yarn to initialize your project.</p>
                <pre><code>npm install -g unseen-cli</code></pre>
                <h2>Configuration</h2>
                <p>Create a config file named unseen.config.json in the repository root.</p>
            </main>
        </body>
        </html>
        """,
        text_content="Home Guide Getting Started with UnseenFramework Install the CLI using npm or yarn. Configuration Create a config file.",
        page_type="documentation"
    )

    comparator_healthy = RenderComparator([ssr_docs])
    assert not any(i["issue_type"] == "spa_render_gap" for i in comparator_healthy.audit_render_gaps())


def test_corporate_entity_ambiguous_vs_clear():
    """
    Entity Disambiguation Generalization:
    - Ambiguous: Common dictionary word brand name without industry descriptor or Organization schema.
    - Clear: Unambiguous corporate identity with industry descriptor in title and structured Organization schema.
    """
    ambiguous_site = PageData(
        url="https://beacon.io/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Beacon</title></head>
        <body>
            <h1>Welcome to Beacon</h1>
            <p>We build tools for tomorrow.</p>
        </body>
        </html>
        """,
        title="Beacon",
        text_content="Welcome to Beacon We build tools for tomorrow.",
        page_type="homepage"
    )

    rules = DisambiguationRules([ambiguous_site], "beacon.io")
    issues = rules.audit_entity_clarity()
    # Must flag dictionary collision risk or unbranded title
    assert any(i["issue_type"] in ("brand_entity_collision_risk", "unbranded_page_titles") for i in issues)

    # Clear corporate identity
    clear_site = PageData(
        url="https://beacon-telecom.io/",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head>
            <title>Beacon Telecom — Maritime Satellite Communications &amp; Fleet IoT</title>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "Organization",
                "name": "Beacon Telecom",
                "url": "https://beacon-telecom.io",
                "description": "Provider of maritime satellite communications and offshore IoT connectivity."
            }
            </script>
        </head>
        <body>
            <header>
                <a href="/">Home</a>
                <a href="/about">About Us</a>
                <a href="/solutions">Solutions</a>
            </header>
            <main>
                <h1>Offshore Maritime Satellite Infrastructure</h1>
                <p>Beacon Telecom provides high-bandwidth L-band and Ka-band communication solutions.</p>
            </main>
            <footer>
                <p>&copy; 2026 Beacon Telecom Marine Services Ltd.</p>
            </footer>
        </body>
        </html>
        """,
        title="Beacon Telecom — Maritime Satellite Communications & Fleet IoT",
        text_content="Home About Us Solutions Offshore Maritime Satellite Infrastructure Beacon Telecom provides high-bandwidth solutions. 2026 Beacon Telecom Marine Services Ltd.",
        page_type="homepage",
        internal_links=["https://beacon-telecom.io/about", "https://beacon-telecom.io/solutions"]
    )

    rules_clear = DisambiguationRules([clear_site], "beacon-telecom.io", site_type="corporate")
    clear_issues = rules_clear.audit_entity_clarity()
    assert not any(i["issue_type"] in ("brand_entity_collision_risk", "unbranded_page_titles", "missing_authority_links") for i in clear_issues)


def test_news_publisher_navigation_weak_vs_healthy():
    """
    Publisher/Editorial Generalization:
    - Weak: Deep article page with 0 outgoing internal links (dead end) and no breadcrumbs.
    - Healthy: Deep article with breadcrumb hierarchy and contextual links to related topics.
    """
    dead_end_article = PageData(
        url="https://dailychronicle.example/2026/09/investigations/renewable-energy-transition",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Renewable Energy Transition Report | Daily Chronicle</title></head>
        <body>
            <h1>The Global Renewable Energy Transition</h1>
            <p>Investment in solar and offshore wind reached record highs this quarter...</p>
        </body>
        </html>
        """,
        text_content="The Global Renewable Energy Transition Investment in solar and offshore wind reached record highs.",
        title="Renewable Energy Transition Report | Daily Chronicle",
        page_type="article",
        internal_links=[]  # Zero outgoing internal navigation
    )

    nav = NavigationGraph([dead_end_article])
    issues = nav.audit_navigation_and_orientation()
    assert any(i["issue_type"] == "navigation_dead_ends" for i in issues)
    assert any(i["issue_type"] == "missing_deep_page_orientation" for i in issues)

    # Healthy article with breadcrumb and related links
    healthy_article = PageData(
        url="https://dailychronicle.example/2026/09/investigations/renewable-energy-transition",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Renewable Energy Transition Report | Daily Chronicle</title></head>
        <body>
            <nav aria-label="breadcrumb">
                <a href="/">Home</a> &gt; <a href="/investigations">Investigations</a> &gt; <span>Energy</span>
            </nav>
            <main>
                <h1>The Global Renewable Energy Transition</h1>
                <p>Investment in solar and offshore wind reached record highs this quarter...</p>
            </main>
            <aside>
                <h3>Related Coverage</h3>
                <ul>
                    <li><a href="/investigations/grid-modernization">Grid Modernization Challenges</a></li>
                    <li><a href="/investigations/battery-storage">Battery Storage Breakthroughs</a></li>
                </ul>
            </aside>
        </body>
        </html>
        """,
        text_content="Home Investigations Energy The Global Renewable Energy Transition Related Coverage Grid Modernization Battery Storage",
        title="Renewable Energy Transition Report | Daily Chronicle",
        page_type="article",
        internal_links=[
            "https://dailychronicle.example/",
            "https://dailychronicle.example/investigations",
            "https://dailychronicle.example/investigations/grid-modernization",
            "https://dailychronicle.example/investigations/battery-storage"
        ]
    )

    nav_healthy = NavigationGraph([healthy_article])
    healthy_issues = nav_healthy.audit_navigation_and_orientation()
    assert not any(i["issue_type"] in ("navigation_dead_ends", "missing_deep_page_orientation") for i in healthy_issues)


def test_saas_commercial_page_missing_cta_vs_healthy():
    """
    SaaS Commercial Generalization:
    - Missing CTA: High-intent pricing page listing subscription fees ($49/mo, $149/mo) with NO clickable call-to-action.
    - Healthy: High-intent pricing page with clear conversion buttons ('Start Free Trial', 'Subscribe').
    """
    missing_cta_pricing = PageData(
        url="https://cloudmetric.example/pricing",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Pricing Plans | CloudMetric</title></head>
        <body>
            <h1>Simple, Transparent Pricing</h1>
            <div class="tier">
                <h2>Starter</h2>
                <p>$49 / month</p>
                <p>Includes up to 5 team members.</p>
            </div>
            <div class="tier">
                <h2>Enterprise</h2>
                <p>$199 / month</p>
                <p>Unlimited data ingestion and dedicated SLA.</p>
            </div>
        </body>
        </html>
        """,
        text_content="Simple Transparent Pricing Starter $49 / month Enterprise $199 / month",
        title="Pricing Plans | CloudMetric",
        page_type="pricing"
    )

    analyzer = EngagementAnalyzer([missing_cta_pricing])
    issues = analyzer.audit_value_proposition_and_ctas()
    assert any(i["issue_type"] == "missing_clear_cta" for i in issues)
    cta_issue = next(i for i in issues if i["issue_type"] == "missing_clear_cta")
    assert cta_issue["severity"] == "high"

    # Healthy pricing page with prominent CTA
    healthy_pricing = PageData(
        url="https://cloudmetric.example/pricing",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Pricing Plans | CloudMetric</title></head>
        <body>
            <h1>Simple, Transparent Pricing</h1>
            <div class="tier">
                <h2>Starter</h2>
                <p>$49 / month</p>
                <a href="/checkout?plan=starter" class="btn btn-primary">Start 14-Day Free Trial</a>
            </div>
            <div class="tier">
                <h2>Enterprise</h2>
                <p>$199 / month</p>
                <a href="/contact-sales" class="btn btn-secondary">Contact Sales</a>
            </div>
        </body>
        </html>
        """,
        text_content="Simple Transparent Pricing Starter $49 / month Start 14-Day Free Trial Enterprise $199 / month Contact Sales",
        title="Pricing Plans | CloudMetric",
        page_type="pricing",
        internal_links=["https://cloudmetric.example/checkout?plan=starter", "https://cloudmetric.example/contact-sales"]
    )

    analyzer_healthy = EngagementAnalyzer([healthy_pricing])
    assert not any(i["issue_type"] == "missing_clear_cta" for i in analyzer_healthy.audit_value_proposition_and_ctas())


def test_image_alt_substantive_diagrams_vs_decorative_icons():
    """
    Visual Accessibility & Content Locking Generalization:
    - Substantive missing: Informative system architecture diagrams and charts missing alt attributes.
    - Decorative: Icons and decorative glyphs marked with role="presentation" or aria-hidden="true" are exempt.
    """
    page_missing_alts = PageData(
        url="https://techdocs.example/architecture",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>System Architecture | TechDocs</title></head>
        <body>
            <h1>System Architecture</h1>
            <img src="/img/database-cluster-topology.png" />
            <img src="/img/network-flow-diagram.svg" />
            <img src="/img/auth-handshake-sequence.png" />
            <img src="/img/failover-state-machine.png" />
        </body>
        </html>
        """,
        page_type="documentation"
    )

    comparator = RenderComparator([page_missing_alts])
    issues = comparator.audit_render_gaps()
    assert any(i["issue_type"] == "facts_locked_in_images" for i in issues)
    img_issue = next(i for i in issues if i["issue_type"] == "facts_locked_in_images")
    assert "alt" in img_issue["evidence"].lower()

    # Decorative icons must NOT trigger defect
    page_decorative_icons = PageData(
        url="https://techdocs.example/features",
        status_code=200,
        raw_html="""<!DOCTYPE html>
        <html>
        <head><title>Platform Features | TechDocs</title></head>
        <body>
            <h1>Platform Features</h1>
            <ul>
                <li><img src="/assets/icons/check-bullet.svg" role="presentation" /> Fast deployment</li>
                <li><img src="/assets/icons/star-bullet.svg" aria-hidden="true" /> Enterprise security</li>
                <li><img src="/assets/icons/arrow-right.png" role="presentation" /> Scalable database</li>
                <li><img src="/assets/icons/shield.svg" aria-hidden="true" /> 99.99% SLA guarantee</li>
            </ul>
        </body>
        </html>
        """,
        page_type="content"
    )

    comparator_decor = RenderComparator([page_decorative_icons])
    assert not any(i["issue_type"] == "facts_locked_in_images" for i in comparator_decor.audit_render_gaps())


def test_canonical_unresolved_duplicate_vs_unique_standalone():
    """
    Canonical Resolution Generalization:
    - Unresolved duplicate: Duplicate tracking parameter URLs without canonical tag create indexing ambiguity.
    - Unique standalone: Distinct unique pages with unique content omitting canonical are NOT penalized.
    """
    # 1. Unresolved duplicate content
    body = "Ultra-low latency edge gateway processing 10 million transactions per second."
    p1 = PageData(
        url="https://edgenet.example/products/gateway",
        status_code=200,
        raw_html=f"<html><body><h1>Edge Gateway</h1><p>{body}</p></body></html>",
        text_content=body,
        canonical_url=None
    )
    p2 = PageData(
        url="https://edgenet.example/items/gateway?utm_source=partner&utm_medium=cpc",
        status_code=200,
        raw_html=f"<html><body><h1>Edge Gateway</h1><p>{body}</p></body></html>",
        text_content=body,
        canonical_url=None
    )

    comp_dup = RenderComparator([p1, p2])
    dup_issues = comp_dup.audit_render_gaps()
    assert any(i["issue_type"] == "unresolved_duplicate_content" for i in dup_issues)

    # 2. Distinct unique pages omitting canonical must NOT produce a defect
    u1 = PageData(
        url="https://edgenet.example/about-us",
        status_code=200,
        raw_html="<html><body><h1>About EdgeNet</h1><p>Founded in 2024 to build distributed compute.</p></body></html>",
        text_content="About EdgeNet Founded in 2024 to build distributed compute.",
        canonical_url=None
    )
    u2 = PageData(
        url="https://edgenet.example/security",
        status_code=200,
        raw_html="<html><body><h1>Security Practices</h1><p>SOC-2 Type II certified and encrypted at rest.</p></body></html>",
        text_content="Security Practices SOC-2 Type II certified and encrypted at rest.",
        canonical_url=None
    )

    comp_unique = RenderComparator([u1, u2])
    unique_issues = comp_unique.audit_render_gaps()
    assert not any(i["issue_type"] in ("unresolved_duplicate_content", "missing_canonical_tags") for i in unique_issues)
