from playwright.async_api import async_playwright

async def scrap_domain(domain: str) -> dict:
    if not domain.startswith("http"):
        domain = f"http://{domain}"
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(domain, timeout=10000)
            seo = await get_seo_stats(page) if response else None
            status_code = response.status if response else None
            return {
                "domain": domain,
                "status_code": status_code,
                "seo": seo,
                "success": response is not None,
                "error": None if response else "No response received",
            }
    except Exception as e:
        return {"domain": domain, "error": str(e), "success": False}
    finally:
        if browser:
            try:
                await browser.close()
            except Exception:
                pass

async def get_seo_stats(page) -> dict:
    """Extract basic SEO statistics from the current page.

    Returns a dictionary with common SEO signals.
    """
    try:
        # Use a single evaluate to minimize round-trips
        data = await page.evaluate(
            """
            () => {
              const bySel = (sel) => document.querySelector(sel);
              const bySelAll = (sel) => Array.from(document.querySelectorAll(sel));

              const title = document.title || null;
              const metaDescEl = bySel('meta[name="description"], meta[name="Description"]');
              const metaDescription = metaDescEl ? metaDescEl.getAttribute('content') || null : null;
              const h1Count = bySelAll('h1').length;
              const canonicalEl = bySel('link[rel="canonical"]');
              const canonical = canonicalEl ? canonicalEl.getAttribute('href') || null : null;
              const robotsEl = bySel('meta[name="robots"], meta[name="Robots"]');
              const robots = robotsEl ? robotsEl.getAttribute('content') || null : null;

              const textContent = document.body ? document.body.innerText || '' : '';
              const words = textContent.trim().split(/\s+/).filter(Boolean);
              const wordCount = words.length;

              const aTags = bySelAll('a[href]');
              let internalLinks = 0, externalLinks = 0, nofollowLinks = 0;
              try {
                const pageHost = location.host;
                aTags.forEach(a => {
                  const rel = (a.getAttribute('rel') || '').toLowerCase();
                  if (rel.includes('nofollow')) nofollowLinks++;
                  try {
                    const url = new URL(a.href, location.origin);
                    if (url.host === pageHost) internalLinks++; else externalLinks++;
                  } catch {}
                });
              } catch {}

              const images = bySelAll('img');
              const imagesWithoutAlt = images.filter(img => !img.getAttribute('alt') || img.getAttribute('alt').trim() === '').length;

              return {
                title,
                metaDescription,
                h1Count,
                canonical,
                robots,
                wordCount,
                links: { total: aTags.length, internal: internalLinks, external: externalLinks, nofollow: nofollowLinks },
                images: { total: images.length, withoutAlt: imagesWithoutAlt },
              };
            }
            """
        )
        # Additionally get HTTP status text if available via response is already handled; here only DOM-based.
        return data
    except Exception:
        return {}