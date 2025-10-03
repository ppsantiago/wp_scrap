# app/routes/tools.py
from fastapi import APIRouter
from app.services.scrap_domain import scrap_domain

router = APIRouter()

@router.get("/check-domain", tags=["tools"])
async def scrap(domain: str):
    return await scrap_domain(domain)