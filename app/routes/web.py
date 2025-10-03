from fastapi import APIRouter, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from pathlib import Path

router = APIRouter()
BASE_DIR = Path(__file__).resolve().parent.parent.parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))

@router.get("/", response_class=HTMLResponse, tags=["web"])
async def home_index(request: Request):
    return templates.TemplateResponse(
        "pages/index.html",
        {"request": request, "title": "Home | FastAPI", "app_name": "My FastAPI App"},
    )

@router.get("/scrap", response_class=HTMLResponse, tags=["web"])
async def scrap_page(request: Request):
    return templates.TemplateResponse(
        "pages/scrap.html",
        {"request": request, "title": "WP Scraper", "app_name": "WP Scraper"},
    )