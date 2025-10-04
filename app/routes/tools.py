# app/routes/tools.py
from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session
from app.services.scrap_domain import scrap_domain
from app.services.storage_service import StorageService
from app.database import get_db
import logging

router = APIRouter()
logger = logging.getLogger(__name__)


@router.get("/check-domain", tags=["tools"])
async def scrap(
    domain: str = Query(..., description="Dominio a analizar (ej: example.com)"),
    save_to_db: bool = Query(True, description="Guardar resultado en base de datos"),
    db: Session = Depends(get_db)
):
    """
    Realiza scraping de un dominio y opcionalmente guarda el resultado en la base de datos.
    
    Parámetros:
    - domain: El dominio a analizar (puede incluir http:// o https://)
    - save_to_db: Si True (por defecto), guarda el reporte en la base de datos
    
    Retorna:
    - Objeto JSON con toda la información del dominio (SEO, técnica, seguridad, etc.)
    """
    # Realizar el scraping
    result = await scrap_domain(domain)
    
    # Guardar en base de datos si está habilitado
    if save_to_db and result:
        try:
            # Limpiar el dominio para guardarlo (quitar http://)
            clean_domain = domain.replace("http://", "").replace("https://", "").strip("/")
            
            report = StorageService.save_report(
                db=db,
                domain_name=clean_domain,
                report_data=result
            )
            
            # Agregar ID del reporte guardado a la respuesta
            result["report_id"] = report.id
            result["saved_to_db"] = True
            
            logger.info(f"Reporte guardado con ID {report.id} para dominio {clean_domain}")
        except Exception as e:
            logger.error(f"Error al guardar reporte en DB: {str(e)}")
            result["saved_to_db"] = False
            result["db_error"] = str(e)
    else:
        result["saved_to_db"] = False
    
    return result