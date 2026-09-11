"""
Test fixtures and HTML generators for deterministic offline testing.
"""

PERFECT_HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>AcmeCloud | Enterprise Cloud Management &amp; Analytics Platform</title>
    <meta name="description" content="AcmeCloud provides automated enterprise cloud management, analytics, and security for global organizations.">
    <link rel="canonical" href="https://acmecloud.io/">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Organization",
      "name": "AcmeCloud",
      "url": "https://acmecloud.io",
      "logo": "https://acmecloud.io/logo.png",
      "description": "Enterprise cloud management and infrastructure analytics.",
      "sameAs": [
        "https://www.wikidata.org/wiki/Q123456",
        "https://www.linkedin.com/company/acmecloud",
        "https://crunchbase.com/organization/acmecloud"
      ]
    }
    </script>
</head>
<body>
    <header>
        <nav aria-label="Main Navigation">
            <a href="/">Home</a>
            <a href="/products">Products</a>
            <a href="/pricing">Pricing</a>
            <a href="/about">About Us</a>
        </nav>
    </header>
    <main>
        <h1>Next-Generation Cloud Orchestration for High-Growth Engineering Teams</h1>
        <p>AcmeCloud automates multicloud infrastructure governance, cost optimization, and compliance monitoring across AWS, Azure, and Google Cloud.</p>
        <div class="actions">
            <a href="/pricing" class="btn btn-primary">Start Free Trial</a>
            <a href="/demo" class="btn btn-secondary">Request Demo</a>
        </div>
    </main>
    <footer>
        <p>&copy; 2026 AcmeCloud Technologies Inc. All rights reserved.</p>
        <a href="https://www.linkedin.com/company/acmecloud">LinkedIn</a>
    </footer>
</body>
</html>
"""

ECOMMERCE_PRODUCT_PAGE_NO_SCHEMA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Pro Running Shoes | SportCo Athletics</title>
    <link rel="canonical" href="https://sportco.example/products/running-shoes">
</head>
<body>
    <header>
        <a href="/">Home</a>
        <a href="/products">Products</a>
    </header>
    <main>
        <h1>Pro Running Shoes</h1>
        <p class="price">$129.99</p>
        <p class="desc">High-performance running shoes with breathable mesh and responsive cushioning.</p>
        <button>Buy Now</button>
    </main>
    <footer>
        <p>&copy; 2026 SportCo Inc.</p>
    </footer>
</body>
</html>
"""

ECOMMERCE_PRODUCT_PAGE_WITH_SCHEMA_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Pro Running Shoes | SportCo Athletics</title>
    <link rel="canonical" href="https://sportco.example/products/running-shoes">
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Pro Running Shoes",
      "description": "High-performance running shoes.",
      "image": "https://sportco.example/shoe.jpg",
      "offers": {
        "@type": "Offer",
        "price": "129.99",
        "priceCurrency": "USD",
        "availability": "https://schema.org/InStock"
      }
    }
    </script>
</head>
<body>
    <main>
        <h1>Pro Running Shoes</h1>
        <p>$129.99</p>
        <button>Buy Now</button>
    </main>
</body>
</html>
"""

STALE_CONFLICTING_HOMEPAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>LegacySoft Platform</title>
</head>
<body>
    <h1>LegacySoft Business Automation</h1>
    <p>Get started with our basic package. Plans starting at $19 per month.</p>
    <p>Roadmap 2022: We are launching our cloud edition in Q3 2022!</p>
    <a href="/pricing">View Pricing</a>
    <footer>
        <p>&copy; 2021 LegacySoft LLC.</p>
    </footer>
</body>
</html>
"""

STALE_CONFLICTING_PRICING_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Pricing Plans | LegacySoft Platform</title>
</head>
<body>
    <h1>Transparent Pricing</h1>
    <p>Plans from $49 per month for full platform access.</p>
    <footer>
        <p>&copy; 2021 LegacySoft LLC.</p>
    </footer>
</body>
</html>
"""

SPA_EMPTY_SHELL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Modern SPA Portal</title>
    <script src="/static/js/bundle.main.js" defer></script>
</head>
<body>
    <div id="root"></div>
</body>
</html>
"""

DEAD_END_DEEP_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Deep Article Insight</title>
</head>
<body>
    <h1>Comprehensive Guide to Database Sharding</h1>
    <p>Database sharding splits large datasets across multiple database nodes...</p>
    <!-- Zero internal navigation, no breadcrumbs, no links -->
</body>
</html>
"""

MALFORMED_JSONLD_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Syntax Error Page</title>
    <script type="application/ld+json">
    {
      "@context": "https://schema.org",
      "@type": "Product",
      "name": "Broken Product",
      "price": 99.99,
    }
    </script>
</head>
<body>
    <h1>Broken Page</h1>
</body>
</html>
"""

