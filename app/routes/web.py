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
        {"request": request, "title": "Dashboard | WP Scrap", "app_name": "WP Scrap"},
    )

@router.get("/scrap", response_class=HTMLResponse, tags=["web"])
async def scrap_page(request: Request):
    return templates.TemplateResponse(
        "pages/scrap.html",
        {"request": request, "title": "WP Scraper", "app_name": "WP Scraper"},
    )

@router.get("/domains", response_class=HTMLResponse, tags=["web"])
async def domains_list_page(request: Request):
    return templates.TemplateResponse(
        "pages/domains.html",
        {"request": request, "title": "Dominios | WP Scrap"},
    )

@router.get("/domain/{domain_name}", response_class=HTMLResponse, tags=["web"])
async def domain_detail_page(request: Request, domain_name: str):
    return templates.TemplateResponse(
        "pages/domain_detail.html",
        {"request": request, "title": f"{domain_name} | WP Scrap", "domain_name": domain_name},
    )

@router.get("/report/{report_id}", response_class=HTMLResponse, tags=["web"])
async def report_detail_page(request: Request, report_id: int):
    return templates.TemplateResponse(
        "pages/report_detail.html",
        {"request": request, "title": f"Reporte #{report_id} | WP Scrap", "report_id": report_id},
    )


@router.get("/jobs", response_class=HTMLResponse, tags=["web"])
async def jobs_list_page(request: Request):
    return templates.TemplateResponse(
        "pages/jobs.html",
        {"request": request, "title": "Jobs | WP Scrap"},
    )

@router.get("/job/{job_id}", response_class=HTMLResponse, tags=["web"])
async def job_detail_page(request: Request, job_id: int):
    return templates.TemplateResponse(
        "pages/job_detail.html",
        {"request": request, "title": f"Job #{job_id} | WP Scrap", "job_id": job_id},
    )


@router.get("/settings", response_class=HTMLResponse, tags=["web"])
async def settings_page(request: Request):
    return templates.TemplateResponse(
        "pages/settings.html",
        {"request": request, "title": "Configuración | WP Scrap"},
    )