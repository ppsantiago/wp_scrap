from typing import Dict, Any, List, Set, Tuple
import re
import json
import heapq
from itertools import count
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

GENERIC_EMAIL_PREFIXES = {
    "info","contact","contacto","hello","hola","support","ventas","sales",
    "marketing","admin","hi","team","office","comercial","press","pr"
}

PAGE_KEYWORDS: Dict[str, List[str]] = {
    "contact": ["contact", "contacto", "contato", "contatt", "kontakt", "support"],
    "team": ["team", "equipo", "staff", "people", "persona"],
    "about": ["about", "nosotros", "quienes", "empresa", "historia", "mission", "mision"],
    "pricing": ["pricing", "precios", "tarifa", "plan", "planes", "quote", "cotizacion"],
    "blog": ["blog", "noticias", "news", "articulos", "recursos", "press", "stories"],
}

PAGE_PRIORITY: Dict[str, int] = {
    "contact": 0,
    "team": 1,
    "about": 2,
    "pricing": 3,
    "home": 4,
    "blog": 5,
    "other": 6,
}

CTA_KEYWORDS = {
    "contact", "contáctanos", "contáctame", "contáctanos", "comenzar", "get started",
    "start", "comprar", "buy", "demo", "cotizar", "try", "solicitar", "habla", "agenda",
    "agendar", "enviar", "registrarse", "sign up", "apply", "download", "descargar"
}

INTEGRATION_HINTS = {
    "hubspot": ["hsforms", "hubspot"],
    "typeform": ["typeform"],
    "zoho": ["zohoforms", "zoho"],
}

ADDRESS_KEYWORDS = [
    "street", "st.", "st ", "avenue", "ave", "avenida", "calle", "road", "rd", "piso",
    "floor", "suite", "ste", "barrio", "local", "oficina", "office", "ciudad", "city",
    "provincia", "state", "zip", "código postal", "codigo postal", "postal"
]

VALUE_PROP_KEYWORDS = [
    "we help", "we support", "soluciones", "ayudamos", "impulsamos", "especialistas",
    "experts", "expertos", "nos dedicamos", "nuestra misión", "our mission", "transformamos",
    "empoderamos"
]

SERVICE_KEYWORDS = ["servicios", "services", "lo que hacemos", "solutions", "soluciones"]
PRICING_KEYWORDS = [
    "$", "€", "usd", "ars", "plan", "plans", "pricing", "precio", "tarifa", "mensual",
    "anual", "month", "year"
]
TESTIMONIAL_KEYWORDS = ["testimonio", "testimonial", "client", "cliente", "lo que dicen"]

TYPE_PAGE_LIMITS: Dict[str, int] = {
    "contact": 5,
    "team": 5,
    "about": 4,
    "pricing": 4,
    "home": 3,
    "blog": 8,
    "other": 15,
}

MAX_FORMS_STORED = 80
MAX_CTA_HIGHLIGHTS = 60
MAX_TEAM_CONTACTS = 40


def _page_priority(label: str) -> int:
    return PAGE_PRIORITY.get(label, PAGE_PRIORITY.get("other", 6))


def _classify_by_url(url: str) -> str:
    path = urlparse(url).path.lower()
    if path in ("", "/"):
        return "home"
    for label, keywords in PAGE_KEYWORDS.items():
        if any(kw in path for kw in keywords):
            return label
    return "other"


def _classify_page(url: str, text: str | None) -> str:
    base_label = _classify_by_url(url)
    if not text:
        return base_label

    lowered = text.lower()
    for label, keywords in PAGE_KEYWORDS.items():
        if any(kw in lowered for kw in keywords):
            return label
    return base_label


def _looks_like_cta(text: str) -> bool:
    if not text:
        return False
    lowered = text.strip().lower()
    if len(lowered) > 80:
        return False
    if any(lowered.startswith(prefix) for prefix in ("http", "tel:", "mailto:")):
        return False
    return any(keyword in lowered for keyword in CTA_KEYWORDS)


def _dedupe_list(values: List[str]) -> List[str]:
    seen: Set[str] = set()
    ordered: List[str] = []
    for value in values:
        if value not in seen:
            seen.add(value)
            ordered.append(value)
    return ordered


def _dedupe_dicts(items: List[Dict[str, Any]], key_fields: Tuple[str, ...]) -> List[Dict[str, Any]]:
    seen: Set[Tuple[Any, ...]] = set()
    result: List[Dict[str, Any]] = []
    for item in items:
        key = tuple(item.get(field) for field in key_fields)
        if key in seen:
            continue
        seen.add(key)
        result.append(item)
    return result


def _email_confidence(email: str) -> str:
    prefix = email.split("@", 1)[0]
    primary = prefix.split(".")[0].lower()
    return "generic" if primary in GENERIC_EMAIL_PREFIXES else "personal"


def _iter_ld_nodes(raw: str):
    try:
        data = json.loads(raw)
    except Exception:
        return

    stack = [data]
    while stack:
        current = stack.pop()
        if isinstance(current, dict):
            yield current
            for key in ("@graph", "graph", "itemListElement", "mainEntity", "hasPart"):
                value = current.get(key)
                if value:
                    if isinstance(value, list):
                        stack.extend(value)
                    else:
                        stack.append(value)
        elif isinstance(current, list):
            stack.extend(current)


def _node_has_type(node: Dict[str, Any], type_name: str) -> bool:
    raw_type = node.get("@type")
    if not raw_type:
        return False
    if isinstance(raw_type, str):
        return raw_type.lower() == type_name.lower()
    if isinstance(raw_type, list):
        return any(isinstance(t, str) and t.lower() == type_name.lower() for t in raw_type)
    return False


def _extract_schema_people(ld_json_list: List[str], page_url: str) -> List[Dict[str, Any]]:
    people: List[Dict[str, Any]] = []
    for raw in ld_json_list or []:
        for node in _iter_ld_nodes(raw):
            if not _node_has_type(node, "Person"):
                continue
            person = {
                "name": node.get("name"),
                "job_title": node.get("jobTitle"),
                "email": None,
                "phone": None,
                "same_as": [],
                "source": page_url,
            }
            contact_point = node.get("contactPoint")
            if isinstance(contact_point, dict):
                person.setdefault("email", contact_point.get("email"))
                person.setdefault("phone", contact_point.get("telephone"))
            elif isinstance(contact_point, list):
                for cp in contact_point:
                    if isinstance(cp, dict):
                        person.setdefault("email", cp.get("email"))
                        person.setdefault("phone", cp.get("telephone"))

            if node.get("email") and not person["email"]:
                person["email"] = node.get("email")
            if node.get("telephone") and not person["phone"]:
                person["phone"] = node.get("telephone")

            same_as = node.get("sameAs")
            if isinstance(same_as, list):
                person["same_as"] = [s for s in same_as if isinstance(s, str)]
            elif isinstance(same_as, str):
                person["same_as"] = [same_as]

            people.append(person)
    return people


def _sentences_with_keywords(text: str, keywords: List[str]) -> List[str]:
    if not text:
        return []
    sentences = re.split(r"[\r\n\.\?!]+", text)
    results: List[str] = []
    for sentence in sentences:
        stripped = sentence.strip()
        if len(stripped) < 12:
            continue
        lowered = stripped.lower()
        if any(keyword in lowered for keyword in keywords):
            results.append(stripped)
    return results


def _extract_business_signals(text: str) -> Dict[str, List[str]]:
    return {
        "value_prop": _sentences_with_keywords(text, VALUE_PROP_KEYWORDS)[:5],
        "services": _sentences_with_keywords(text, SERVICE_KEYWORDS)[:5],
        "pricing": _sentences_with_keywords(text, PRICING_KEYWORDS)[:5],
        "testimonials": _sentences_with_keywords(text, TESTIMONIAL_KEYWORDS)[:5],
        "addresses": _sentences_with_keywords(text, ADDRESS_KEYWORDS)[:5],
    }


def _merge_business_info(target: Dict[str, List[str]], new_info: Dict[str, List[str]]) -> None:
    for key, values in new_info.items():
        if not values:
            continue
        bucket = target.setdefault(key, [])
        bucket.extend(values)
        if key == "addresses":
            # Addresses are likely shorter; keep more but dedupe
            target[key] = _dedupe_list(target[key])[:20]
        else:
            target[key] = _dedupe_list(target[key])[:15]


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
    queued: Set[str] = set()
    pages_data: List[Dict[str,Any]] = []
    contact_emails: Set[str] = set()
    whatsapps: Set[str] = set()
    phones_by_e164: dict[str, str] = {}
    socials: dict[str,set] = {k:set() for k in ["facebook","instagram","x","linkedin","youtube","tiktok","whatsapp"]}
    legal_pages: Set[str] = set()
    analytics: Set[str] = set()
    pixels: Set[str] = set()
    forms_detailed: List[Dict[str, Any]] = []
    forms_total_count = 0
    forms_integrations: Set[str] = set()
    cta_highlights: List[Dict[str, Any]] = []
    team_contacts: List[Dict[str, Any]] = []
    business_summary: Dict[str, List[str]] = {
        "value_prop": [],
        "services": [],
        "pricing": [],
        "testimonials": [],
        "addresses": [],
    }
    wp_signals = {"theme": None, "plugins": set(), "rest_api": False}

    priority_queue: List[Tuple[int, int, str, str]] = []
    type_enqueued: Dict[str, int] = {}
    order_counter = count()

    def enqueue(url: str):
        if not url or _is_asset(url):
            return
        if not _same_site(url, base_url):
            return
        if url in visited or url in queued:
            return
        label = _classify_by_url(url)
        limit = TYPE_PAGE_LIMITS.get(label, TYPE_PAGE_LIMITS.get("other", max_pages))
        if type_enqueued.get(label, 0) >= limit:
            return
        type_enqueued[label] = type_enqueued.get(label, 0) + 1
        heapq.heappush(priority_queue, (_page_priority(label), next(order_counter), url, label))
        queued.add(url)

    for seed in seeds:
        enqueue(seed)

    if not priority_queue:
        enqueue(base_url)

    type_processed: Dict[str, int] = {}

    while priority_queue and len(visited) < max_pages:
        _, _, url, seed_label = heapq.heappop(priority_queue)
        if url in visited:
            continue
        queued.discard(url)
        visited.add(url)

        p = await context.new_page()
        try:
            resp = await p.goto(url, timeout=timeout, wait_until="domcontentloaded")
            if not resp or not resp.ok:
                continue

            html = await p.content()
            text = await p.evaluate("document.body ? document.body.innerText : ''")

            page_type = _classify_page(url, text)
            type_processed[page_type] = type_processed.get(page_type, 0) + 1

            # Emails, phones, whatsapp detection
            page_emails = {e.lower() for e in EMAIL_RE.findall(text)}
            contact_emails.update(page_emails)

            page_phone_matches = set(PHONE_RE.findall(text))
            page_normalized_phones: set[str] = set()
            for ph in page_phone_matches:
                normalized = _normalize_phone(ph)
                if not normalized:
                    continue
                e164, display = normalized
                phones_by_e164.setdefault(e164, display)
                page_normalized_phones.add(display)

            anchor_hrefs = await p.locator("a[href]").evaluate_all("els => els.map(e => e.href)")
            for a in anchor_hrefs:
                if not a:
                    continue
                low_href = a.lower()
                if "wa.me" in low_href or "api.whatsapp.com" in low_href:
                    whatsapps.add(a)
                host = urlparse(a).netloc.lower()
                for dom, key in SOCIAL_HOSTS.items():
                    if dom in host:
                        socials[key].add(a)

            # Forms and CTA details from DOM
            page_struct = await p.evaluate("""
              () => {
                const toText = (el) => {
                  if (!el) return '';
                  const text = (el.innerText || el.textContent || '').trim();
                  return text;
                };
                const getLabel = (input) => {
                  if (!input) return null;
                  const id = input.getAttribute('id');
                  if (id) {
                    let selector = `label[for="${id}"]`;
                    if (window.CSS && typeof CSS.escape === 'function') {
                      selector = `label[for="${CSS.escape(id)}"]`;
                    }
                    const labelFor = document.querySelector(selector);
                    if (labelFor && labelFor.textContent) {
                      return labelFor.textContent.trim();
                    }
                  }
                  const parentLabel = input.closest('label');
                  if (parentLabel && parentLabel.textContent) {
                    return parentLabel.textContent.trim();
                  }
                  return null;
                };

                const forms = Array.from(document.querySelectorAll('form')).map(form => {
                  const inputs = Array.from(form.querySelectorAll('input, textarea, select')).map(input => ({
                    name: input.getAttribute('name') || null,
                    type: (input.getAttribute('type') || input.tagName || '').toLowerCase(),
                    placeholder: input.getAttribute('placeholder') || null,
                    label: getLabel(input),
                    required: input.hasAttribute('required')
                  }));
                  const buttons = Array.from(form.querySelectorAll('button, input[type="submit"], input[type="button"], a.button'))
                    .map(btn => toText(btn))
                    .filter(Boolean);
                  const hasCaptcha = Boolean(
                    form.querySelector('input[name*="captcha" i], input[id*="captcha" i], div[class*="captcha" i], iframe[src*="recaptcha" i], div[id*="recaptcha" i]')
                  );
                  const formAttributes = [form.getAttribute('id') || '', form.getAttribute('class') || ''].join(' ');
                  const integration = (() => {
                    if (/hubspot/i.test(formAttributes) || form.querySelector('[data-hs-cf-bound]')) return 'hubspot';
                    if (/typeform/i.test(formAttributes)) return 'typeform';
                    if (/zoho/i.test(formAttributes)) return 'zoho';
                    if (form.querySelector('script[src*="hsforms"]')) return 'hubspot';
                    return null;
                  })();
                  return {
                    action: form.getAttribute('action') || null,
                    method: (form.getAttribute('method') || 'get').toLowerCase(),
                    inputs,
                    buttons,
                    hasCaptcha,
                    integration,
                    id: form.getAttribute('id') || null
                  };
                });

                const ctas = Array.from(document.querySelectorAll('a, button')).map(el => {
                  const text = toText(el);
                  const href = el.getAttribute('href');
                  const role = el.getAttribute('role');
                  const dataset = el.getAttribute('data-cta') || el.getAttribute('data-track') || null;
                  const classes = el.getAttribute('class') || '';
                  const visible = !!(el.offsetParent || el.getClientRects().length);
                  return {
                    text,
                    href: href || null,
                    role: role || null,
                    dataset,
                    classes,
                    visible
                  };
                });

                return { forms, ctas };
              }
            """)

            page_forms = page_struct.get("forms") if isinstance(page_struct, dict) else []
            page_ctas = page_struct.get("ctas") if isinstance(page_struct, dict) else []

            forms_total_count += len(page_forms)
            for form in page_forms:
                detail = {
                    "page": url,
                    "page_type": page_type,
                    **{k: form.get(k) for k in ["action", "method", "inputs", "buttons", "hasCaptcha", "integration", "id"]},
                }
                forms_detailed.append(detail)
                integration = form.get("integration")
                if integration:
                    forms_integrations.add(integration)

            # CTA highlights
            for cta in page_ctas:
                if not isinstance(cta, dict):
                    continue
                if not cta.get("visible"):
                    continue
                text_cta = (cta.get("text") or "").strip()
                if not _looks_like_cta(text_cta):
                    continue
                highlight = {
                    "text": text_cta,
                    "href": cta.get("href"),
                    "page": url,
                    "page_type": page_type,
                }
                cta_highlights.append(highlight)

            # Legal pages heuristic
            low_url = url.lower()
            if any(k in low_url for k in ["privacidad","privacy","terminos","terms","cookies","aviso-legal","legal"]):
                legal_pages.add(url)

            # Integrations and tracking scripts
            scripts = await p.evaluate("Array.from(document.scripts).map(s => s.src || '').filter(Boolean)")
            lower_html = html.lower()
            for s in scripts:
                ls = s.lower()
                if "gtag/js" in ls or "googletagmanager" in ls or "analytics.js" in ls:
                    analytics.add("google")
                if "hotjar" in ls:
                    analytics.add("hotjar")
                if "connect.facebook" in ls or "fbq" in lower_html:
                    pixels.add("meta")
                for integration_key, hints in INTEGRATION_HINTS.items():
                    if any(h in ls for h in hints) or any(h in lower_html for h in hints):
                        forms_integrations.add(integration_key)

            # JSON-LD extraction and team contacts
            ld_json = await p.evaluate("""
              () => Array.from(document.querySelectorAll('script[type="application/ld+json"]')).map(s => s.textContent).filter(Boolean)
            """)
            schema_people = _extract_schema_people(ld_json, url)
            page_team_contacts: List[Dict[str, Any]] = []
            for person in schema_people:
                if not isinstance(person, dict):
                    continue
                email = person.get("email")
                if email:
                    email = email.strip()
                    person["email"] = email
                    contact_emails.add(email.lower())
                phone_display = None
                phone_e164 = None
                raw_phone = person.get("phone")
                if raw_phone:
                    normalized_phone = _normalize_phone(raw_phone)
                    if normalized_phone:
                        phone_e164, phone_display = normalized_phone
                        phones_by_e164.setdefault(phone_e164, phone_display)
                    else:
                        phone_display = raw_phone.strip()
                team_entry = {
                    "name": person.get("name"),
                    "job_title": person.get("job_title"),
                    "email": email,
                    "email_confidence": _email_confidence(email) if email else None,
                    "phone": phone_display,
                    "phone_e164": phone_e164,
                    "social_profiles": person.get("same_as", []),
                    "source": person.get("source", url),
                }
                page_team_contacts.append(team_entry)
                team_contacts.append(team_entry)

            # Business signals
            business_info = _extract_business_signals(text)
            _merge_business_info(business_summary, business_info)

            # WordPress signals
            if "/wp-json" in lower_html or "/wp-json/" in lower_html:
                wp_signals["rest_api"] = True
            for m in re.finditer(r"/wp-content/themes/([^/]+)/", html):
                wp_signals["theme"] = wp_signals["theme"] or m.group(1)
            for m in re.finditer(r"/wp-content/plugins/([^/]+)/", html):
                wp_signals["plugins"].add(m.group(1))

            # Enqueue new internal links respecting limits
            hrefs = await p.locator("a[href]").evaluate_all("els => els.map(e => e.getAttribute('href'))")
            for href in hrefs:
                u = _norm(href, url)
                if not u:
                    continue
                enqueue(u)

            # Page snapshot
            cta_sample = [entry for entry in cta_highlights[-3:]] if cta_highlights else []
            pages_data.append({
                "url": url,
                "status": resp.status,
                "page_type": page_type,
                "seed_type": seed_label,
                "emails_found": sorted(page_emails),
                "phones_found": sorted(page_normalized_phones),
                "jsonld_raw": ld_json[:5],
                "forms_count": len(page_forms),
                "team_contacts": page_team_contacts[:3],
                "cta_sample": cta_sample,
            })
        except Exception:
            pass
        finally:
            await p.close()

    # Deduplicate and limit collected data
    team_contacts = _dedupe_dicts(team_contacts, ("name", "email", "phone", "source"))[:MAX_TEAM_CONTACTS]
    forms_detailed = forms_detailed[:MAX_FORMS_STORED]
    cta_highlights = _dedupe_dicts(cta_highlights, ("text", "href", "page"))[:MAX_CTA_HIGHLIGHTS]

    contact_confidence = {"personal": [], "generic": []}
    for email in sorted(contact_emails):
        bucket = _email_confidence(email)
        contact_confidence.setdefault(bucket, []).append(email)

    for key, values in business_summary.items():
        business_summary[key] = _dedupe_list(values)

    site_summary = {
        "pages_crawled": len(visited),
        "contacts": {
            "emails": sorted(contact_emails),
            "phones": sorted(phones_by_e164.values()),
            "whatsapp": sorted(whatsapps),
            "team_contacts": team_contacts,
            "contact_confidence": {
                "personal": contact_confidence.get("personal", []),
                "generic": contact_confidence.get("generic", []),
            },
        },
        "socials": {k: sorted(v) for k, v in socials.items() if v},
        "forms_found": forms_total_count,
        "forms_detailed": forms_detailed,
        "cta_highlights": cta_highlights,
        "legal_pages": sorted(legal_pages),
        "integrations": {
            "analytics": sorted(analytics),
            "pixels": sorted(pixels),
            "forms": sorted(forms_integrations),
        },
        "business": business_summary,
        "wp": {
            "theme": wp_signals["theme"],
            "plugins": sorted(wp_signals["plugins"]),
            "rest_api": wp_signals["rest_api"],
        },
    }
    return site_summary, pages_data
