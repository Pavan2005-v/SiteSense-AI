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

# ---------------------------------------------------------------------------
# Phase 28 generalization fixtures: healthy cases that look superficially
# similar to defects, and genuinely defective cases.
# ---------------------------------------------------------------------------

# A JS-enhanced page whose initial HTML is a MEANINGFUL SPA page (SSR content) — NOT a defect.
SPA_MEANINGFUL_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>NimbusNotes | Collaborative Note-Taking for Teams</title>
    <meta name="description" content="NimbusNotes lets teams capture, organize, and share project notes in real time across web and mobile devices.">
    <script src="/static/js/app.bundle.js" defer></script>
</head>
<body>
    <div id="root">
        <header>
            <nav aria-label="Main">
                <a href="/">Home</a>
                <a href="/features">Features</a>
                <a href="/pricing">Pricing</a>
                <a href="/blog">Blog</a>
            </nav>
        </header>
        <main>
            <h1>Collaborative note-taking for distributed teams</h1>
            <p>NimbusNotes keeps your team's project knowledge organized with shared workspaces, instant search, and offline sync across every device you use.</p>
            <p>Teams at more than 4,000 companies use NimbusNotes to document decisions, capture meeting notes, and onboard new engineers faster.</p>
            <a class="btn-primary" href="/signup">Start Free Trial</a>
        </main>
        <footer><p>&copy; 2026 NimbusNotes Inc.</p></footer>
    </div>
</body>
</html>
"""

# A thin-but-meaningful JS-enhanced landing page (partial JS enhancement) — NOT a defect.
SPA_PARTIAL_ENHANCEMENT_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>PixelForge Studio | Design Portfolio</title>
    <meta name="description" content="PixelForge Studio designs brand identities, packaging, and digital experiences for independent coffee roasters.">
    <script src="/static/js/interactions.js" defer></script>
</head>
<body>
    <div id="app">
        <header>
            <nav>
                <a href="/work">Work</a>
                <a href="/about">About</a>
                <a href="/contact">Contact</a>
            </nav>
        </header>
        <main>
            <h1>Brand identity for independent coffee roasters</h1>
            <p>PixelForge Studio partners with roasters to design labels, packaging, and e-commerce experiences that convert.</p>
            <a href="/contact">Contact Us</a>
        </main>
    </div>
</body>
</html>
"""

# A genuine FAQ page with structured Q&A (dl + heading pairs) — qualifies for proactive FAQPage schema.
FAQ_REAL_PAGE_HTML = """<!DOCTYPE html>
<html lang="en">
<head><title>Frequently Asked Questions | HelpZone Support</title></head>
<body>
    <header><nav><a href="/">Home</a><a href="/contact">Contact</a></nav></header>
    <main>
        <h1>Frequently Asked Questions</h1>
        <dl>
            <dt>What is your refund policy?</dt>
            <dd>We offer a full refund within 30 days of purchase for annual plans. Monthly subscriptions can be cancelled anytime and remain active until the end of the billing period.</dd>
            <dt>Can I change my plan later?</dt>
            <dd>Yes, you can upgrade or downgrade your plan at any time from your account settings page. Changes are prorated automatically on your next invoice.</dd>
        </dl>
        <h2>How do I invite my team members?</h2>
        <p>To invite teammates, open your workspace settings, click Members, and enter their email addresses. Each invitee receives a personalized onboarding email with a secure join link.</p>
        <h3>Do you offer discounts for students?</h3>
        <p>Students and educators with a verified institutional email address receive 50 percent off any paid plan. Verification takes less than a day through our partner portal.</p>
    </main>
</body>
</html>
"""

# A blog article with an editorial question headline and feedback widgets — NOT an FAQ.
ARTICLE_QUESTION_HEADLINE_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>Why millions of viewers tune into bento box meal prep on YouTube | The Daily Plate</title>
    <meta name="description" content="An editorial deep-dive into the bento box meal prep trend and the creators behind it.">
</head>
<body>
    <header><nav><a href="/">Home</a><a href="/food">Food</a><a href="/culture">Culture</a></nav></header>
    <article>
        <h1>Why millions of viewers tune into bento box meal prep videos</h1>
        <p>The quiet rhythm of slicing vegetables and portioning rice has become an unlikely centerpiece of the platform's most-watched cooking channels, drawing audiences who treat the videos as both instruction and relaxation.</p>
        <p>Creators report that viewers follow the format for its meditative pacing as much as for the recipes themselves, with comment sections filled with requests for regional variations.</p>
    </article>
    <aside class="related">
        <h2>Need more help?</h2>
        <p>Visit our subscriber services desk.</p>
        <h2>Was this article helpful?</h2>
        <button>Yes</button><button>No</button>
    </aside>
</body>
</html>
"""

# Homepage with NO H1 but excellent orientation (video/content platform style) — NOT a defect.
HOMEPAGE_NO_H1_EXCELLENT_ORIENTATION_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <title>StreamDeck - Watch trailers, clips, and full episodes</title>
    <meta name="description" content="StreamDeck is a video streaming platform with thousands of movies, series, and creator clips. Browse trending trailers, build playlists, and subscribe to channels you love.">
</head>
<body>
    <header>
        <form role="search" action="/results">
            <input type="search" name="search_query" placeholder="Search videos" aria-label="Search">
        </form>
        <nav aria-label="Main">
            <a href="/trending">Trending</a>
            <a href="/movies">Movies</a>
            <a href="/series">Series</a>
            <a href="/signin">Sign in</a>
        </nav>
    </header>
    <main role="main" aria-label="Featured content">
        <h2>Trending trailers this week</h2>
        <p>StreamDeck brings you official trailers, creator clips, and full episodes from thousands of channels, with new releases added daily across every genre.</p>
        <h2>Build playlists and subscribe to channels</h2>
        <p>Save videos to playlists, follow your favorite creators, and get recommendations tuned to what you watch.</p>
    </main>
    <footer><p>&copy; 2026 StreamDeck Media</p></footer>
</body>
</html>
"""

