# app/routes/jobs.py
"""
Rutas API para gestión de Jobs (trabajos en lote).
"""
from fastapi import APIRouter, Depends, HTTPException, Query, Body
from sqlalchemy.orm import Session
from typing import List, Optional
from pydantic import BaseModel, Field
import logging

from app.database import get_db
from app.services.job_service import JobService
from app.models import JobStatus, JobType

router = APIRouter(prefix="/api/jobs", tags=["jobs"])
logger = logging.getLogger(__name__)


# ---- Schemas Pydantic ----

class CreateBatchScrapingJobRequest(BaseModel):
    """Request para crear un job de scraping en lote"""
    domains: List[str] = Field(..., description="Lista de dominios a scrapear", min_items=1)
    name: Optional[str] = Field(None, description="Nombre del job")
    description: Optional[str] = Field(None, description="Descripción del job")
    created_by: str = Field("system", description="Usuario que crea el job")


class JobResponse(BaseModel):
    """Response con información de un job"""
    id: int
    job_type: str
    name: str
    status: str
    progress_percentage: int
    total_steps: int
    completed_steps: int
    failed_steps: int


# ---- Endpoints ----

@router.post("/batch-scraping", status_code=201)
async def create_batch_scraping_job(
    request: CreateBatchScrapingJobRequest,
    db: Session = Depends(get_db)
):
    """
    Crea un job para scraping en lote de múltiples dominios.
    El job se ejecutará en background sin bloquear la UI.
    
    Returns:
        Job creado con su ID y estado inicial
    """
    try:
        # Crear el job
        job = JobService.create_batch_scraping_job(
            db=db,
            domains=request.domains,
            name=request.name,
            description=request.description,
            created_by=request.created_by
        )
        
        # Iniciar ejecución en background
        JobService.start_job(job.id)
        
        return {
            "success": True,
            "message": f"Job creado e iniciado: {job.name}",
            "job": job.to_dict(include_steps=False)
        }
        
    except Exception as e:
        logger.error(f"Error creando job de scraping en lote: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/")
async def list_jobs(
    status: Optional[str] = Query(None, description="Filtrar por estado"),
    job_type: Optional[str] = Query(None, description="Filtrar por tipo"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de resultados"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db)
):
    """
    Lista todos los jobs con filtros opcionales.
    
    Query params:
    - status: pending, running, completed, failed, cancelled
    - job_type: batch_scraping, single_scraping, report_generation, data_export
    - limit: Número máximo de resultados (default: 50, max: 100)
    - offset: Offset para paginación (default: 0)
    
    Returns:
        Lista de jobs con información resumida
    """
    try:
        jobs = JobService.list_jobs(
            db=db,
            status=status,
            job_type=job_type,
            limit=limit,
            offset=offset
        )
        
        return {
            "success": True,
            "count": len(jobs),
            "jobs": jobs
        }
        
    except Exception as e:
        logger.error(f"Error listando jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}")
async def get_job(
    job_id: int,
    include_steps: bool = Query(True, description="Incluir detalles de los pasos"),
    db: Session = Depends(get_db)
):
    """
    Obtiene detalles de un job específico.
    
    Path params:
    - job_id: ID del job
    
    Query params:
    - include_steps: Si True, incluye todos los pasos del job (default: True)
    
    Returns:
        Job con todos sus detalles y pasos
    """
    try:
        job = JobService.get_job_status(db=db, job_id=job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado")
        
        # Si no se piden los pasos, removerlos
        if not include_steps and "steps" in job:
            del job["steps"]
        
        return {
            "success": True,
            "job": job
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{job_id}/cancel")
async def cancel_job(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Cancela un job en ejecución o pendiente.
    
    Path params:
    - job_id: ID del job a cancelar
    
    Returns:
        Confirmación de cancelación
    """
    try:
        success = JobService.cancel_job(db=db, job_id=job_id)
        
        if not success:
            raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado")
        
        return {
            "success": True,
            "message": f"Job {job_id} cancelado exitosamente"
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error cancelando job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{job_id}/steps")
async def get_job_steps(
    job_id: int,
    db: Session = Depends(get_db)
):
    """
    Obtiene los pasos de un job específico.
    Útil para polling del progreso.
    
    Path params:
    - job_id: ID del job
    
    Returns:
        Lista de pasos con su estado actual
    """
    try:
        job = JobService.get_job_status(db=db, job_id=job_id)
        
        if not job:
            raise HTTPException(status_code=404, detail=f"Job {job_id} no encontrado")
        
        return {
            "success": True,
            "job_id": job_id,
            "status": job.get("status"),
            "progress_percentage": job.get("progress_percentage"),
            "steps": job.get("steps", [])
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error obteniendo pasos del job {job_id}: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats/summary")
async def get_jobs_summary(
    db: Session = Depends(get_db)
):
    """
    Obtiene estadísticas resumidas de todos los jobs.
    
    Returns:
        Resumen con contadores por estado
    """
    from app.models import Job
    from sqlalchemy import func
    
    try:
        # Contar jobs por estado
        stats = db.query(
            Job.status,
            func.count(Job.id).label('count')
        ).group_by(Job.status).all()
        
        # Total de jobs
        total = db.query(func.count(Job.id)).scalar()
        
        # Formatear respuesta
        summary = {
            "total": total,
            "by_status": {stat.status: stat.count for stat in stats}
        }
        
        return {
            "success": True,
            "summary": summary
        }
        
    except Exception as e:
        logger.error(f"Error obteniendo resumen de jobs: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
