# app/routes/reports.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path
from sqlalchemy.orm import Session
from app.services.storage_service import StorageService
from app.services.comment_service import CommentService
from app.services.trusted_contact_service import TrustedContactService
from app.database import get_db
from typing import List, Optional
import logging
from pydantic import BaseModel, Field, validator

from app.services.report_generation_service import (
    ReportGenerationError,
    ReportGenerationService,
)

router = APIRouter(prefix="/reports", tags=["reports"])
logger = logging.getLogger(__name__)


class TrustedContactPayload(BaseModel):
    email: Optional[str] = None
    phone: Optional[str] = None

    @validator("email", "phone", pre=True)
    def _normalize(cls, value):
        if value is None:
            return None
        if isinstance(value, str):
            stripped = value.strip()
            return stripped or None
        return value


class ReportGenerationRequest(BaseModel):
    type: str = Field(..., description="Tipo de reporte IA a generar")
    force_refresh: bool = Field(False, description="Ignorar cache y forzar nueva generación")

    @validator("type")
    def _validate_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ReportGenerationService.SUPPORTED_TYPES:
            raise ValueError(
                f"Tipo de reporte no soportado. Opciones válidas: {', '.join(ReportGenerationService.SUPPORTED_TYPES)}"
            )
        return normalized


class PromptUpdateItem(BaseModel):
    type: str = Field(..., description="Tipo de reporte al que aplica el prompt")
    prompt_template: str = Field(..., description="Plantilla en formato Markdown para el prompt")
    updated_by: Optional[str] = Field(None, description="Usuario que actualiza el prompt")

    @validator("type")
    def _validate_prompt_type(cls, value: str) -> str:
        normalized = (value or "").strip().lower()
        if normalized not in ReportGenerationService.SUPPORTED_TYPES:
            raise ValueError(
                f"Tipo de prompt no soportado. Opciones válidas: {', '.join(ReportGenerationService.SUPPORTED_TYPES)}"
            )
        return normalized

    @validator("prompt_template")
    def _validate_template(cls, value: str) -> str:
        if not value or not value.strip():
            raise ValueError("El prompt_template no puede estar vacío")
        return value


class PromptUpdateRequest(BaseModel):
    prompts: List[PromptUpdateItem]


@router.get("/domains", summary="Listar todos los dominios")
async def get_domains(
    limit: int = Query(100, ge=1, le=1000, description="Número máximo de dominios"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la lista de todos los dominios rastreados.
    Ordenados por último scraping (más recientes primero).
    """
    domains = StorageService.get_all_domains(db, limit=limit, offset=offset)
    return {
        "total": len(domains),
        "limit": limit,
        "offset": offset,
        "domains": [d.to_dict() for d in domains]
    }


@router.delete("/domain/{domain_name}", summary="Eliminar un dominio")
async def delete_domain(
    domain_name: str = Path(..., description="Nombre del dominio"),
    db: Session = Depends(get_db)
):
    """Elimina un dominio junto con sus reportes y comentarios asociados."""
    result = StorageService.delete_domain(db, domain_name)
    if result is None:
        raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")

    return {
        "message": f"Dominio '{domain_name}' eliminado correctamente",
        **result
    }


@router.get("/domain/{domain_name}", summary="Obtener información de un dominio")
async def get_domain_info(
    domain_name: str = Path(..., description="Nombre del dominio"),
    db: Session = Depends(get_db)
):
    """
    Obtiene la información completa de un dominio específico.
    """
    domain = StorageService.get_domain_by_name(db, domain_name)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")

    return domain.to_dict()


@router.get("/domain/{domain_name}/history", summary="Historial de reportes de un dominio")
async def get_domain_history(
    domain_name: str = Path(..., description="Nombre del dominio"),
    limit: int = Query(20, ge=1, le=100, description="Número máximo de reportes"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    success_only: bool = Query(False, description="Solo reportes exitosos"),
    include_data: bool = Query(False, description="Incluir datos JSON completos"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el historial de reportes de un dominio específico.
    Por defecto solo retorna métricas (más rápido).
    Usa include_data=true para obtener los datos completos.
    """
    reports = StorageService.get_domain_reports(
        db,
        domain_name=domain_name,
        limit=limit,
        offset=offset,
        success_only=success_only
    )

    if not reports:
        # Verificar si el dominio existe
        domain = StorageService.get_domain_by_name(db, domain_name)
        if not domain:
            raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")
        return {
            "domain": domain_name,
            "total": 0,
            "reports": []
        }

    return {
        "domain": domain_name,
        "total": len(reports),
        "limit": limit,
        "offset": offset,
        "reports": [r.to_dict(include_full_data=include_data) for r in reports]
    }


@router.get("/domain/{domain_name}/latest", summary="Último reporte de un dominio")
async def get_latest_report(
    domain_name: str = Path(..., description="Nombre del dominio"),
    db: Session = Depends(get_db)
):
    """
    Obtiene el reporte más reciente de un dominio.
    Retorna el formato completo compatible con el frontend.
    """
    report = StorageService.get_latest_report(db, domain_name)

    if not report:
        domain = StorageService.get_domain_by_name(db, domain_name)
        if not domain:
            raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")
        raise HTTPException(status_code=404, detail=f"No hay reportes para '{domain_name}'")

    return report.to_frontend_format()


@router.get("/report/{report_id}", summary="Obtener un reporte específico")
async def get_report(
    report_id: int = Path(..., description="ID del reporte"),
    format: str = Query("full", regex="^(full|frontend|metrics)$", description="Formato de salida"),
    db: Session = Depends(get_db)
):
    """
    Obtiene un reporte específico por su ID.

    Formatos disponibles:
    - full: Todos los datos del reporte
    - frontend: Formato compatible con domainForm.js
    - metrics: Solo métricas cacheadas (más rápido)
    """
    report = StorageService.get_report_by_id(db, report_id)

    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    if format == "frontend":
        return report.to_frontend_format()
    elif format == "metrics":
        return report.to_dict(include_full_data=False)
    else:  # full
        return report.to_dict(include_full_data=True)


@router.get("/recent", summary="Reportes recientes de todos los dominios")
async def get_recent_reports(
    days: int = Query(7, ge=1, le=90, description="Días hacia atrás"),
    limit: int = Query(50, ge=1, le=200, description="Número máximo de reportes"),
    db: Session = Depends(get_db)
):
    """
    Obtiene los reportes más recientes de todos los dominios.
    Útil para dashboard o vista general.
    """
    reports = StorageService.get_recent_reports(db, days=days, limit=limit)

    return {
        "days": days,
        "total": len(reports),
        "reports": [r.to_dict(include_full_data=False) for r in reports]
    }


@router.delete("/domain/{domain_name}/cleanup", summary="Limpiar reportes antiguos")
async def cleanup_old_reports(
    domain_name: str = Path(..., description="Nombre del dominio"),
    keep_latest: int = Query(10, ge=1, le=100, description="Cantidad de reportes a mantener"),
    db: Session = Depends(get_db)
):
    """
    Elimina reportes antiguos de un dominio, manteniendo solo los N más recientes.
    Útil para gestionar el tamaño de la base de datos.
    """
    deleted_count = StorageService.delete_old_reports(db, domain_name, keep_latest)

    return {
        "domain": domain_name,
        "deleted": deleted_count,
        "kept": keep_latest,
        "message": f"Se eliminaron {deleted_count} reportes antiguos"
    }


@router.get("/statistics", summary="Estadísticas generales")
async def get_statistics(db: Session = Depends(get_db)):
    """
    Obtiene estadísticas generales de la base de datos.
    Incluye contadores, tasas de éxito y dominios más rastreados.
    """
    stats = StorageService.get_statistics(db)
    return stats


@router.get("/compare/{domain_name}", summary="Comparar reportes de un dominio")
async def compare_reports(
    domain_name: str = Path(..., description="Nombre del dominio"),
    report_ids: str = Query(..., description="IDs de reportes separados por coma (ej: 1,5,10)"),
    metrics: str = Query(
        "seo_word_count,tech_requests_count,tech_total_bytes,pages_crawled",
        description="Métricas a comparar separadas por coma"
    ),
    db: Session = Depends(get_db)
):
    """
    Compara métricas específicas entre diferentes reportes del mismo dominio.
    Útil para ver la evolución del sitio en el tiempo.
    """
    # Parsear IDs
    try:
        ids = [int(id.strip()) for id in report_ids.split(",")]
    except ValueError:
        raise HTTPException(status_code=400, detail="IDs de reportes inválidos")

    # Parsear métricas
    metric_list = [m.strip() for m in metrics.split(",")]

    # Obtener reportes
    domain = StorageService.get_domain_by_name(db, domain_name)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")

    comparison = []
    for report_id in ids:
        report = StorageService.get_report_by_id(db, report_id)
        if not report or report.domain_id != domain.id:
            continue

        report_data = {
            "report_id": report.id,
            "scraped_at": report.scraped_at.isoformat() if report.scraped_at else None,
            "metrics": {}
        }

        for metric in metric_list:
            if hasattr(report, metric):
                report_data["metrics"][metric] = getattr(report, metric)

        comparison.append(report_data)

    return {
        "domain": domain_name,
        "reports_compared": len(comparison),
        "metrics": metric_list,
        "comparison": comparison
    }


@router.post(
    "/report/{report_id}/generate",
    summary="Generar reporte IA",
    description="Genera un reporte IA (técnico, comercial o entregable) utilizando LMStudio",
)
async def generate_ai_report(
    report_id: int = Path(..., description="ID del reporte base"),
    payload: ReportGenerationRequest = None,
    db: Session = Depends(get_db),
):
    payload = payload or ReportGenerationRequest(type="technical")
    logger.info(
        "Solicitando generación IA para reporte=%s tipo=%s force_refresh=%s",
        report_id,
        payload.type,
        payload.force_refresh,
    )

    # Validar existencia del reporte base
    report = StorageService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    try:
        result = await ReportGenerationService.generate_report(
            db=db,
            report_id=report_id,
            report_type=payload.type,
            force_refresh=payload.force_refresh,
        )
        return result
    except ReportGenerationError as exc:
        logger.warning(
            "Error de negocio generando reporte IA report=%s type=%s: %s",
            report_id,
            payload.type,
            exc,
        )
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:  # pragma: no cover - fallback
        logger.exception(
            "Error inesperado generando reporte IA report=%s type=%s",
            report_id,
            payload.type,
        )
        raise HTTPException(
            status_code=500,
            detail="Ocurrió un error inesperado generando el reporte IA",
        ) from exc


@router.get(
    "/report/{report_id}/generation-history",
    summary="Historial de generaciones IA",
    description="Devuelve el historial de ejecuciones IA para un reporte específico",
)
async def get_ai_generation_history(
    report_id: int = Path(..., description="ID del reporte base"),
    limit: int = Query(20, ge=1, le=100, description="Cantidad máxima de entradas"),
    db: Session = Depends(get_db),
):
    report = StorageService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    history = ReportGenerationService.get_generation_history(db, report_id, limit)
    return {"report_id": report_id, "history": history}


@router.get(
    "/settings/prompts",
    summary="Listar prompts IA",
    description="Obtiene las plantillas de prompts configuradas para cada tipo de reporte IA",
)
async def list_ai_prompts(db: Session = Depends(get_db)):
    prompts = ReportGenerationService.list_prompts(db)
    return {"prompts": prompts}


@router.put(
    "/settings/prompts",
    summary="Actualizar prompts IA",
    description="Actualiza las plantillas de prompts para generación de reportes IA",
)
async def update_ai_prompts(
    payload: PromptUpdateRequest,
    db: Session = Depends(get_db),
):
    try:
        prompt_dicts = [item.dict() for item in payload.prompts]
        prompts = ReportGenerationService.upsert_prompts(db, prompt_dicts)
        return {"prompts": prompts}
    except ReportGenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc



# Nuevas rutas que incluyen comentarios

@router.get("/domain/{domain_name}/with-comments", summary="Dominio con comentarios")
async def get_domain_with_comments(
    domain_name: str = Path(..., description="Nombre del dominio"),
    include_reports: bool = Query(True, description="Incluir reportes del dominio"),
    db: Session = Depends(get_db)
):
    """
    Obtiene información completa de un dominio incluyendo sus comentarios.
    """
    # Obtener información del dominio
    domain = StorageService.get_domain_by_name(db, domain_name)
    if not domain:
        raise HTTPException(status_code=404, detail=f"Dominio '{domain_name}' no encontrado")

    # Obtener comentarios del dominio
    comments = CommentService.get_comments_for_entity(
        db=db,
        content_type="domain",
        object_id=domain.id,
        include_replies=True
    )

    result = domain.to_dict()
    result["comments"] = [comment.to_dict() for comment in comments]

    # Incluir reportes si se solicita
    if include_reports:
        reports = StorageService.get_domain_reports(db, domain_name, limit=5)
        result["recent_reports"] = [r.to_dict(include_full_data=False) for r in reports]

    return result


@router.get("/report/{report_id}/trusted-contact", summary="Opciones y selección de contacto de confianza")
async def get_trusted_contact(
    report_id: int = Path(..., description="ID del reporte"),
    db: Session = Depends(get_db)
):
    report = StorageService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    contact_options = TrustedContactService.get_contact_options(report)
    active_contact = TrustedContactService.get_active_contact(db, report.domain_id)

    return {
        "report_id": report.id,
        "domain_id": report.domain_id,
        "options": contact_options,
        "selected": TrustedContactService.serialize(active_contact),
    }


@router.put("/report/{report_id}/trusted-contact", summary="Actualizar contacto de confianza")
async def set_trusted_contact(
    report_id: int = Path(..., description="ID del reporte"),
    payload: TrustedContactPayload = None,
    db: Session = Depends(get_db)
):
    report = StorageService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    payload = payload or TrustedContactPayload()
    options = TrustedContactService.get_contact_options(report)

    if payload.email and payload.email not in options["emails"]:
        raise HTTPException(status_code=400, detail="Email no disponible entre los contactos detectados")
    if payload.phone and payload.phone not in options["phones"]:
        raise HTTPException(status_code=400, detail="Teléfono no disponible entre los contactos detectados")

    email = payload.email
    phone = payload.phone

    contact = TrustedContactService.set_trusted_contact(
        db,
        domain_id=report.domain_id,
        report_id=report.id,
        email=email,
        phone=phone,
    )

    return {
        "report_id": report.id,
        "domain_id": report.domain_id,
        "selected": TrustedContactService.serialize(contact),
    }


@router.get("/report/{report_id}/with-comments", summary="Reporte con comentarios")
async def get_report_with_comments(
    report_id: int = Path(..., description="ID del reporte"),
    format: str = Query("frontend", regex="^(full|frontend|metrics)$", description="Formato de salida"),
    db: Session = Depends(get_db)
):
    """
    Obtiene un reporte específico incluyendo sus comentarios asociados.
    """
    # Obtener reporte
    report = StorageService.get_report_by_id(db, report_id)
    if not report:
        raise HTTPException(status_code=404, detail=f"Reporte {report_id} no encontrado")

    # Obtener comentarios del reporte
    comments = CommentService.get_comments_for_entity(
        db=db,
        content_type="report",
        object_id=report.id,
        include_replies=True
    )

    # Construir respuesta según formato solicitado
    if format == "frontend":
        result = report.to_frontend_format()
    elif format == "metrics":
        result = report.to_dict(include_full_data=False)
    else:  # full
        result = report.to_dict(include_full_data=True)

    result["comments"] = [comment.to_dict() for comment in comments]

    return result


@router.get("/domains/with-recent-comments", summary="Dominios con comentarios recientes")
async def get_domains_with_recent_comments(
    limit: int = Query(20, ge=1, le=50, description="Número máximo de dominios"),
    db: Session = Depends(get_db)
):
    """
    Obtiene dominios que tienen comentarios recientes.
    Útil para ver qué dominios están generando discusión.
    """
    # Obtener comentarios recientes de dominios
    recent_comments = CommentService.get_recent_comments(
        db=db,
        limit=limit * 2,  # Obtener más para filtrar
        content_type="domain"
    )

    # Extraer IDs únicos de dominios comentados
    domain_ids = list(set(comment.object_id for comment in recent_comments))

    # Obtener información de los dominios
    domains_with_comments = []
    for domain_id in domain_ids[:limit]:  # Limitar al número solicitado
        domain = StorageService.get_domain_by_id(db, domain_id)
        if domain:
            # Obtener comentarios recientes para este dominio
            domain_comments = [
                comment for comment in recent_comments
                if comment.object_id == domain_id
            ][:3]  # Máximo 3 comentarios recientes

            domain_data = domain.to_dict()
            domain_data["recent_comments"] = [comment.to_dict() for comment in domain_comments]
            domains_with_comments.append(domain_data)

    return {
        "total_domains": len(domains_with_comments),
        "limit": limit,
        "domains": domains_with_comments
    }
