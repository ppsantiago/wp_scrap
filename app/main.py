# app/main.py
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

# Importa routers
from app.routes.web import router as web_router
from app.routes.tools import router as tools_router

# Crea la app
app = FastAPI(title="My FastAPI App")

# Directorio base
BASE_DIR = Path(__file__).resolve().parent.parent

# Archivos estáticos y plantillas
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

# Registra routers
app.include_router(web_router)
app.include_router(tools_router)

# Ruta de salud (puedes moverla a un router si quieres)
@app.get("/health", tags=["health"])
async def health():
    return {"status": "ok"}