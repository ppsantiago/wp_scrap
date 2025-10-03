# app/routes/tools.py
from fastapi import APIRouter
from app.services.domain_checker import check_domain_status

router = APIRouter()

@router.get("/check-domain", tags=["tools"])
async def check_domain(domain: str):
    return await check_domain_status(domain)