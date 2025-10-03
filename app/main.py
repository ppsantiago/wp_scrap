
from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from playwright.async_api import async_playwright

# Create app
app = FastAPI(title="My FastAPI App")

# Resolve project base directory regardless of where the server is started from
BASE_DIR = Path(__file__).resolve().parent.parent

# Static files and templates
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


@app.get("/health", tags=["health"])  # simple liveness endpoint
async def health():
    return {"status": "ok"}


@app.get("/", response_class=HTMLResponse, tags=["web"])  # home page
async def home_index(request: Request):
    return templates.TemplateResponse(
        "pages/index.html",
        {
            "request": request,
            "title": "Home | FastAPI",
            "app_name": "My FastAPI App",
            "year": datetime.now().year,
        },
    )


@app.get("/scrap", response_class=HTMLResponse, tags=["web"])  
async def scrap_page(request: Request):
    return templates.TemplateResponse(
        "pages/scrap.html",
        {
            "request": request,
            "title": "WP Scraper",
            "app_name": "WP Scraper",
            "year": datetime.now().year,
        },
    )

@app.get("/check-domain", tags=["tools"])
async def check_domain(domain: str):
    if not domain.startswith("http"):
        domain = f"http://{domain}"
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            response = await page.goto(domain, timeout=10000)  # 10 segundos timeout
            await browser.close()
            if response:
                return {"domain": domain, "status_code": response.status, "success": True}
            else:
                return {"domain": domain, "error": "No response received", "success": False}
    except Exception as e:
        return {"domain": domain, "error": str(e), "success": False}