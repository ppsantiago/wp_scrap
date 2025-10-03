from pathlib import Path
from datetime import datetime
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

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
        "index.html",
        {
            "request": request,
            "title": "Home | FastAPI",
            "app_name": "My FastAPI App",
            "year": datetime.now().year,
        },
    )

@app.get("/list", response_class=HTMLResponse, tags=["web"])  # list page
async def list_page(request: Request):
    return templates.TemplateResponse(
        "list.html",
        {
            "request": request,
            "title": "Lista | FastAPI",
            "app_name": "My FastAPI App",
            "year": datetime.now().year,
        },
    )
