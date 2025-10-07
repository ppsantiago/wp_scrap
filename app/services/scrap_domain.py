from typing import Dict, Any, List, Set
import re
from urllib.parse import urlparse, urljoin

import phonenumbers
from phonenumbers import PhoneNumberFormat
from phonenumbers.phonenumberutil import NumberParseException
from playwright.async_api import async_playwright

# ---- Tipificación simple por tipo de recurso ----
def _guess_type(url: str, resource_type: str | None) -> str:
    if resource_type:
        rt = resource_type.lower()
        # Playwright usa: document, stylesheet, image, media, font, script, xhr, fetch, other
        if rt in ("document","stylesheet","image","media","font","script","xhr","fetch"): 
            return rt
    u = url.lower()
    for ext, kind in [
        (".css","stylesheet"), (".js","script"), (".mjs","script"),
        (".jpg","image"), (".jpeg","image"), (".png","image"), (".webp","image"),
        (".gif","image"), (".svg","image"), (".ico","image"),
        (".woff","font"), (".woff2","font"), (".ttf","font"), (".otf","font"),
        (".mp4","media"), (".webm","media"), (".mp3","media")
    ]:
        if ext in u: return kind
    return "other"

# ---- Colector de red (cuenta, bytes, por tipo, 1ros/3ros) ----
class NetworkCollector:
    def __init__(self, base_host: str):
        self.base_host = base_host
        self.count = 0
        self.total_bytes = 0
        self.by_type: dict[str, dict[str,int]] = {}   # {type: {"count": n, "bytes": b}}
        self.third_party_bytes = 0
        self.first_party_bytes = 0
        # NUEVO: detalles de imágenes
        self.images: list[dict] = []   # [{url, bytes, content_type, ext}]
        self.images_by_mime: dict[str, int] = {}
        self.images_by_ext: dict[str, int] = {}

    def _add(self, typ: str, size: int, third_party: bool, url: str = "", content_type: str | None = None):
        self.count += 1
        self.total_bytes += size
        bucket = self.by_type.setdefault(typ, {"count": 0, "bytes": 0})
        bucket["count"] += 1
        bucket["bytes"] += size
        if third_party:
            self.third_party_bytes += size
        else:
            self.first_party_bytes += size

        # Si es imagen, guardamos detalles y contamos por formato
        if typ == "image":
            # Extensión (heurística)
            ext = ""
            low = url.lower()
            for e in [".avif",".webp",".svg",".png",".jpg",".jpeg",".gif",".ico"]:
                if e in low:
                    ext = e.lstrip(".")
                    break
            # MIME (si viene en header)
            mime = (content_type or "").split(";")[0].strip() if content_type else ""
            self.images.append({
                "url": url, "bytes": size, "content_type": mime, "ext": ext
            })
            if mime:
                self.images_by_mime[mime] = self.images_by_mime.get(mime, 0) + 1
            if ext:
                self.images_by_ext[ext] = self.images_by_ext.get(ext, 0) + 1

    def as_dict(self):
        return {
            "count": self.count,
            "total_bytes": self.total_bytes,
            "by_type": self.by_type,
            "first_party_bytes": self.first_party_bytes,
            "third_party_bytes": self.third_party_bytes,
            # NUEVO: resúmenes de imágenes
            "images_by_mime": self.images_by_mime,
            "images_by_ext": self.images_by_ext,
            "images_sample": self.images[:10],  # pequeña muestra para depurar
        }

EMAIL_RE = re.compile(r"[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}", re.I)
PHONE_RE = re.compile(r"(?:\+?\d[\d\s().-]{6,}\d)", re.I)
MIN_PHONE_DIGITS = 8
MAX_PHONE_DIGITS = 15
DEFAULT_PHONE_REGION = "AR"
SOCIAL_HOSTS = {"facebook.com":"facebook","instagram.com":"instagram","x.com":"x","twitter.com":"x","linkedin.com":"linkedin","youtube.com":"youtube","tiktok.com":"tiktok","wa.me":"whatsapp","api.whatsapp.com":"whatsapp"}

def _normalize_phone(raw: str, default_region: str = DEFAULT_PHONE_REGION) -> tuple[str, str] | None:
    if not raw:
        return None

    digits_only = re.sub(r"\D", "", raw)
    if len(digits_only) < MIN_PHONE_DIGITS or len(digits_only) > MAX_PHONE_DIGITS:
        return None
    if digits_only.count("0") == len(digits_only):
        return None

    candidate = raw.strip()
    try:
        number = phonenumbers.parse(candidate, default_region)
    except NumberParseException:
        try:
            number = phonenumbers.parse(f"+{digits_only}", None)
        except NumberParseException:
            return None

    if not phonenumbers.is_possible_number(number):
        return None

    e164 = phonenumbers.format_number(number, PhoneNumberFormat.E164)
    international = phonenumbers.format_number(number, PhoneNumberFormat.INTERNATIONAL)
    return e164, international

def _same_site(u:str, base:str)->bool:
    up, bp = urlparse(u), urlparse(base)
    return up.scheme in ("http","https") and up.netloc == bp.netloc

def _norm(href:str, base:str)->str|None:
    if not href: return None
    if href.startswith(("javascript:","data:")): return None
    return urljoin(base, href)

def _is_asset(u:str)->bool:
    return re.search(r"\.(pdf|jpg|jpeg|png|gif|webp|svg|zip|rar|7z|docx?|xlsx?|pptx?)($|\?)", u, re.I) is not None

# --- SEO básico para la página actual (compatible con tu UI) ---
async def get_seo_stats(page, main_headers: dict[str,str] | None = None) -> dict:
    # Lee head/meta/link de una vez para evitar timeouts por elementos faltantes
    base = await page.evaluate("""
      () => {
        const $ = (sel) => document.querySelector(sel);
        const $all = (sel) => Array.from(document.querySelectorAll(sel));
        const meta = (n) => { const el = document.querySelector(`meta[name="${n}"]` ); return el ? el.content : null; };
        const link = (r) => { const el = document.querySelector(`link[rel="${r}"]` ); return el ? el.href : null; };

        const og = {};
        $all('meta[property^="og:"]').forEach(m => { og[m.getAttribute('property')] = m.getAttribute('content') || ''; });
        const tw = {};
        $all('meta[name^="twitter:"]').forEach(m => { tw[m.getAttribute('name')] = m.getAttribute('content') || ''; });

        const headings = $all('h1,h2,h3,h4,h5,h6').map(h => ({ tag: h.tagName, text: (h.textContent||'').trim().slice(0,200) }));

        const ld = $all('script[type="application/ld+json"]').map(s => s.textContent).filter(Boolean);

        const robots = (meta('robots')||'').toLowerCase();
        return {
          title: document.title || '',
          metaDescription: meta('description') || '',
          robots,
          canonical: link('canonical') || '',
          og, twitter: tw,
          h1: { count: $all('h1').length, text: ($('h1') ? $('h1').textContent.trim().slice(0,200) : '') },
          headings,
          schema: { ld_json: ld },
          wordCount: document.body ? (document.body.innerText||'').trim().split(/\\s+/).filter(Boolean).length : 0
        };
      }
    """)

    # Indexabilidad (robots meta + X-Robots-Tag)
    xrobots = ""
    if main_headers:
        for k,v in main_headers.items():
            if k.lower() == "x-robots-tag":
                xrobots = (v or "").lower()
                break
    robots_all = ",".join(filter(None, [base.get("robots",""), xrobots]))
    disallow = ("noindex" in robots_all)
    nofollow = ("nofollow" in robots_all)
    # Links/Imágenes (como ya tenías)
    page_url = page.url
    from urllib.parse import urlparse, urljoin
    cur_host = urlparse(page_url).netloc.lower()
    hrefs = await page.locator('a[href]').evaluate_all("els => els.map(e => ({href: e.getAttribute('href'), rel: (e.getAttribute('rel')||'')}))")
    total_links = internal = external = nofollow_links = 0
    for a in hrefs:
        href = (a.get("href") or "").strip()
        if not href or href.startswith(("javascript:", "#")): continue
        total_links += 1
        if "nofollow" in (a.get("rel") or "").lower(): nofollow_links += 1
        abs_url = urljoin(page_url, href)
        host = urlparse(abs_url).netloc.lower()
        if host == cur_host or host == "":
            internal += 1
        else:
            external += 1

    imgs = await page.locator('img').evaluate_all("els => els.map(e => ({alt: e.getAttribute('alt')}))")
    images_total = len(imgs)
    images_without_alt = sum(1 for i in imgs if not (i.get('alt') or '').strip())

    base.update({
      "links": { "total": total_links, "internal": internal, "external": external, "nofollow": nofollow_links },
      "images": { "total": images_total, "withoutAlt": images_without_alt },
      "indexable": not disallow,
      "follow": not nofollow
    })
    return base

async def scrap_domain(domain: str, max_pages:int=60, timeout:int=10000) -> dict:
    if not domain.startswith("http"):
        domain = f"http://{domain}"

    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            context = await browser.new_context()
            page = await context.new_page()

            # host base para 1ros/3ros
            base_host = urlparse(domain).netloc.lower()
            net = NetworkCollector(base_host)

            # monitor de responses
            def _on_response(resp):
                try:
                    url = resp.url
                    rtype = resp.request.resource_type
                    typ = _guess_type(url, rtype)
                    headers = resp.headers or {}
                    # Tamaño (puede faltar)
                    size = int(headers.get("content-length","0") or "0")
                    # 1ros vs 3ros
                    host = urlparse(url).netloc.lower()
                    third = (host != base_host and host != "")
                    # NUEVO: content-type
                    ctype = headers.get("content-type")
                    net._add(typ, size, third, url=url, content_type=ctype)
                except Exception:
                    pass

            page.on("response", _on_response)

            response = await page.goto(domain, timeout=timeout, wait_until="domcontentloaded")

            # headers de la respuesta principal (para security + x-robots-tag)
            if response:
                hdrs = getattr(response, "headers", None)
                if callable(hdrs):
                    try:
                        main_headers = dict(hdrs())
                    except Exception:
                        main_headers = {}
                else:
                    main_headers = dict(hdrs or {})
            else:
                main_headers = {}

            # Navigation Timing (aprox TTFB/DCL/Load)
            nav = await page.evaluate("""
              () => {
                const n = performance.getEntriesByType('navigation')[0] || performance.timing;
                // Soporte dual (PerformanceNavigationTiming o legacy)
                const fetchStart = n.fetchStart || 0;
                const responseStart = n.responseStart || 0;
                const domContentLoadedEventEnd = n.domContentLoadedEventEnd || (n.domContentLoadedEventEnd===0?0:null);
                const loadEventEnd = n.loadEventEnd || (n.loadEventEnd===0?0:null);
                // TTFB aprox:
                const ttfb = (responseStart && fetchStart>=0) ? (responseStart - fetchStart) : null;
                return {
                  ttfb, dcl: domContentLoadedEventEnd || null, load: loadEventEnd || null
                };
              }
            """)

            seo = await get_seo_stats(page, main_headers) if response else None  # (tu función actual)
            status_code = response.status if response else None

            # Inyectamos resumen de formatos de imágenes (MIME y extensión) en el bloque SEO
            if seo is not None:
                seo.setdefault("images", {})
                # del collector (red de la home)
                req_dict = net.as_dict()
                seo["images"]["byMime"] = req_dict.get("images_by_mime", {})
                seo["images"]["byExt"] = req_dict.get("images_by_ext", {})

            tech = {
              "requests": net.as_dict(),
              "timing": nav,
              "wp": {"theme": None, "plugins": []},  # (rellenamos igual cuando crawleamos)
              "frontend": {"libs": []},
              "console": {"errors": [], "warnings": []}
            }

            # errores/warnings de consola rápida
            page_errors = []
            page_warnings = []

            page.on("pageerror", lambda e: page_errors.append(str(e)))

            def _on_console(msg):
                try:
                    # Acceso seguro a propiedades (str) o métodos callables
                    msg_type = getattr(msg, "type", "")
                    if callable(msg_type):
                        msg_type = msg_type()

                    msg_text = getattr(msg, "text", "")
                    if callable(msg_text):
                        msg_text = msg_text()

                    if msg_type == "warning":
                        page_warnings.append(msg_text)
                except Exception:
                    # Si algo falla, no romper el scraping
                    pass

            page.on("console", _on_console)

            tech["console"]["errors"] = page_errors
            tech["console"]["warnings"] = page_warnings

            # Headers de seguridad principales (siempre en minúsculas)
            def _h(name): 
                for k,v in main_headers.items():
                    if k.lower()==name: return v
                return None

            security = {
              "headers": {
                "hsts": _h("strict-transport-security"),
                "csp": _h("content-security-policy"),
                "xfo": _h("x-frame-options"),
                "xcto": _h("x-content-type-options")
              }
            }

            # 1) descubrir URLs semilla
            seeds = await _discover_seeds(context, domain, timeout)
            # 2) crawl interno limitado
            site_summary, pages_data = await _crawl_site(context, domain, seeds, max_pages=max_pages, timeout=timeout)

            await context.close()
            return {
                "domain": domain,
                "status_code": status_code,
                "seo": seo,
                "tech": tech,           # NUEVO
                "security": security,   # NUEVO
                "site": site_summary,
                "pages": pages_data,
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
    contact_emails, whatsapps = set(), set()
    phones_by_e164: dict[str, str] = {}
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
            page_phone_matches = set(PHONE_RE.findall(text))
            page_normalized_phones: set[str] = set()
            for ph in page_phone_matches:
                normalized = _normalize_phone(ph)
                if not normalized:
                    continue
                e164, display = normalized
                phones_by_e164.setdefault(e164, display)
                page_normalized_phones.add(display)
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
                "phones_found": sorted(page_normalized_phones),
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
            "phones": sorted(phones_by_e164.values()),
            "whatsapp": sorted(whatsapps)
        },
        "socials": {k: sorted(v) for k, v in socials.items() if v},
        "forms_found": len(forms),
        "legal_pages": sorted(legal_pages),
        "integrations": {"analytics": sorted(analytics), "pixels": sorted(pixels)},
        "wp": {"theme": wp_signals["theme"], "plugins": sorted(wp_signals["plugins"]), "rest_api": wp_signals["rest_api"]}
    }
    return site_summary, pages_data
