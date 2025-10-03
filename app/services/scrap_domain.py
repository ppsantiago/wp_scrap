# scrap_domain.py
from typing import Dict, Any, List, Set
import re
from urllib.parse import urlparse, urljoin
from playwright.async_api import async_playwright

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d{1,3}[\s.-]?)?(?:\(?\d{2,4}\)?[\s.-]?)?\d{3,5}[\s.-]?\d{3,5}", re.I)
SOCIAL_HOSTS = {"facebook.com":"facebook","instagram.com":"instagram","x.com":"x","twitter.com":"x","linkedin.com":"linkedin","youtube.com":"youtube","tiktok.com":"tiktok","wa.me":"whatsapp","api.whatsapp.com":"whatsapp"}

def _same_site(u:str, base:str)->bool:
    up, bp = urlparse(u), urlparse(base)
    return up.scheme in ("http","https") and up.netloc == bp.netloc

def _norm(href:str, base:str)->str|None:
    if not href: return None
    if href.startswith(("javascript:","data:")): return None
    return urljoin(base, href)

def _is_asset(u:str)->bool:
    return re.search(r"\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|rar|7z|docx?|xlsx?|pptx?)($|\?)", u, re.I) is not None

async def scrap_domain(domain: str, max_pages:int=60, timeout:int=10000) -> dict:
    if not domain.startswith("http"):
        domain = f"http://{domain}"

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()
            response = await page.goto(domain, timeout=timeout, wait_until="domcontentloaded")

            seo = await get_seo_stats(page) if response else None  # (tu función actual)
            status_code = response.status if response else None

            # 1) descubrir URLs semilla
            seeds = await _discover_seeds(context, domain, timeout)
            # 2) crawl interno limitado
            site_summary, pages_data = await _crawl_site(context, domain, seeds, max_pages=max_pages, timeout=timeout)

            await context.close()
            return {
                "domain": domain,
                "status_code": status_code,
                "seo": seo,
                "site": site_summary,   # NUEVO: agregado
                "pages": pages_data,    # NUEVO: agregado (muestra por página)
                "success": response is not None,
                "error": None if response else "No response received",
            }
    except Exception as e:
        return {"domain": domain, "error": str(e), "success": False}
    finally:
        if browser:
            try: await browser.close()
            except: pass


async def _discover_seeds(context, base_url:str, timeout:int)->List[str]:
    seeds: Set[str] = set()
    seeds.add(base_url.rstrip("/") + "/")

    # hints clásicos
    hints = ["contacto","contact","about","nosotros","quienes-somos","privacy-policy","politica-de-privacidad","aviso-legal","terminos","blog"]
    for h in hints:
        seeds.add(urljoin(base_url, f"/{h.strip('/')}"))

    # wp-sitemap.xml / sitemap.xml / robots.txt
    for path in ["/wp-sitemap.xml", "/sitemap.xml", "/robots.txt"]:
        try:
            p = await context.new_page()
            r = await p.goto(urljoin(base_url, path), timeout=timeout, wait_until="domcontentloaded")
            if r and r.ok:
                html = await p.content()
                # sitemaps muy simple: extrae <loc>...</loc>
                locs = re.findall(r"<loc>(.*?)</loc>", html)
                for u in locs:
                    if _same_site(u, base_url) and not _is_asset(u):
                        seeds.add(u)
                # robots: busca 'Sitemap: '
                if path.endswith("robots.txt"):
                    for m in re.finditer(r"(?i)Sitemap:\s*(\S+)", html):
                        seeds.add(m.group(1))
            await p.close()
        except: pass

    return list(seeds)

async def _crawl_site(context, base_url:str, seeds:List[str], max_pages:int, timeout:int):
    visited: Set[str] = set()
    queue: List[str] = [u for u in seeds if _same_site(u, base_url)]
    pages_data: List[Dict[str,Any]] = []
    contact_emails, phones, whatsapps = set(), set(), set()
    socials: dict[str,set] = {k:set() for k in ["facebook","instagram","x","linkedin","youtube","tiktok","whatsapp"]}
    legal_pages, forms, analytics, pixels = set(), [], set(), set()
    wp_signals = {"theme": None, "plugins": set(), "rest_api": False}

    while queue and len(visited) < max_pages:
        url = queue.pop(0)
        if url in visited or _is_asset(url): continue
        visited.add(url)

        p = await context.new_page()
        try:
            resp = await p.goto(url, timeout=timeout, wait_until="domcontentloaded")
            if not resp or not resp.ok:
                await p.close(); continue

            # extrae HTML + texto + headers
            html = await p.content()
            text = await p.evaluate("document.body ? document.body.innerText : ''")

            # emails/phones/whatsapp (regex)
            for e in EMAIL_RE.findall(text): contact_emails.add(e.lower())
            for ph in PHONE_RE.findall(text): phones.add(ph.strip())
            # whatsapp por enlaces
            for a in await p.locator("a[href]").evaluate_all("els => els.map(e => e.href)"):
                if "wa.me" in a or "api.whatsapp.com" in a: whatsapps.add(a)
                # sociales
                host = urlparse(a).netloc.lower()
                for dom, key in SOCIAL_HOSTS.items():
                    if dom in host: socials[key].add(a)

            # formularios
            page_forms = await p.evaluate("""
              () => Array.from(document.querySelectorAll('form')).map(f => ({
                action: f.getAttribute('action') || null,
                method: (f.getAttribute('method')||'get').toLowerCase(),
                inputs: Array.from(f.querySelectorAll('input, textarea, select')).map(i => ({
                  name: i.getAttribute('name') || null,
                  type: (i.getAttribute('type')||i.tagName||'').toLowerCase(),
                  placeholder: i.getAttribute('placeholder') || null
                }))
              }))
            """)
            if page_forms: forms.extend(page_forms)

            # legales (heurística por URL o texto)
            low = url.lower()
            if any(k in low for k in ["privacidad","privacy","terminos","terms","cookies","aviso-legal","legal"]):
                legal_pages.add(url)

            # integraciones (muy básico)
            scripts = await p.evaluate("Array.from(document.scripts).map(s => s.src || '').filter(Boolean)")
            for s in scripts:
                if "gtag/js" in s or "googletagmanager" in s or "analytics.js" in s: analytics.add("google")
                if "connect.facebook" in s or "fbq(" in html: pixels.add("meta")
                if "hotjar" in s: analytics.add("hotjar")

            # JSON-LD (schema.org) crudo
            ld_json = await p.evaluate("""
              () => Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.textContent).filter(Boolean)
            """)

            # señales WP (tema/plugins por assets simples, REST)
            if "/wp-json" in html or "/wp-json/" in html:
                wp_signals["rest_api"] = True
            for m in re.finditer(r"/wp-content/themes/([^/]+)/", html):
                wp_signals["theme"] = wp_signals["theme"] or m.group(1)
            for m in re.finditer(r"/wp-content/plugins/([^/]+)/", html):
                wp_signals["plugins"].add(m.group(1))

            # Encolar enlaces internos (limitar crecimiento)
            links = await p.locator("a[href]").evaluate_all("els => els.map(e => e.getAttribute('href'))")
            for h in links:
                u = _norm(h, url)
                if not u or _is_asset(u): continue
                if _same_site(u, base_url) and u not in visited and len(visited)+len(queue) < max_pages:
                    queue.append(u)

            # guardar snapshot por página
            pages_data.append({
                "url": url,
                "status": resp.status,
                "emails_found": list({e for e in EMAIL_RE.findall(text)}),
                "phones_found": list({ph for ph in PHONE_RE.findall(text)}),
                "jsonld_raw": ld_json[:5],  # limitar muestra
                "forms_count": len(page_forms) if page_forms else 0
            })
        except Exception:
            pass
        finally:
            await p.close()

    # resumen global del sitio
    site_summary = {
        "pages_crawled": len(visited),
        "contacts": {
            "emails": sorted(contact_emails),
            "phones": sorted(phones),
            "whatsapp": sorted(whatsapps)
        },
        "socials": {k: sorted(v) for k, v in socials.items() if v},
        "forms_found": len(forms),
        "legal_pages": sorted(legal_pages),
        "integrations": {"analytics": sorted(analytics), "pixels": sorted(pixels)},
        "wp": {"theme": wp_signals["theme"], "plugins": sorted(wp_signals["plugins"]), "rest_api": wp_signals["rest_api"]}
    }
    return site_summary, pages_data
