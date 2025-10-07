# app/services/job_service.py
"""
Servicio para manejo de Jobs asíncronos.
Permite ejecutar trabajos en lotes sin bloquear la UI.
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from sqlalchemy.orm import Session

from app.models import Job, JobStep, JobStatus, JobType
from app.services.scrap_domain import scrap_domain
from app.services.storage_service import StorageService
from app.database import SessionLocal

logger = logging.getLogger(__name__)


class JobService:
    """Servicio para gestionar y ejecutar jobs"""
    
    # Registro de jobs en ejecucion (job_id -> asyncio.Task)
    _running_jobs: Dict[int, asyncio.Task] = {}
    
    @staticmethod
    def _to_iso(value: Optional[datetime]) -> Optional[str]:
        return value.isoformat() if value else None

    @classmethod
    def create_batch_scraping_job(
        cls,
        db: Session,
        domains: List[str],
        name: str = None,
        description: str = None,
        created_by: str = "system"
    ) -> Job:
        """
        Crea un job para scraping en lote de múltiples dominios.
        
        Args:
            db: Sesión de base de datos
            domains: Lista de dominios a procesar
            name: Nombre del job (opcional)
            description: Descripción del job (opcional)
            created_by: Usuario que creó el job
            
        Returns:
            Job creado
        """
        # Limpiar dominios
        clean_domains = [
            d.replace("http://", "").replace("https://", "").strip("/")
            for d in domains
        ]
        
        # Crear job
        job = Job(
            job_type=JobType.BATCH_SCRAPING,
            name=name or f"Batch Scraping - {len(clean_domains)} dominios",
            description=description or f"Scraping en lote de {len(clean_domains)} dominios",
            config={
                "domains": clean_domains,
                "save_to_db": True,
                "max_retries": 2
            },
            status=JobStatus.PENDING,
            total_steps=len(clean_domains),
            created_by=created_by,
            priority=5
        )
        
        db.add(job)
        db.commit()
        db.refresh(job)
        
        # Crear pasos para cada dominio
        for idx, domain in enumerate(clean_domains, start=1):
            step = JobStep(
                job_id=job.id,
                step_number=idx,
                name=f"Scraping: {domain}",
                description=f"Analizar dominio {domain}",
                status=JobStatus.PENDING
            )
            db.add(step)

        db.commit()

        logger.info(f"Job creado: ID={job.id}, Tipo={job.job_type}, Pasos={job.total_steps}")
        return job

    @classmethod
    def create_single_scraping_job(
        cls,
        db: Session,
        domain: str,
        name: str = None,
        description: str = None,
        created_by: str = "system"
    ) -> Job:
        """Crea un job para scraping individual de un dominio."""
        if not domain or not isinstance(domain, str):
            raise ValueError("Dominio inválido para job individual")

        clean_domain = domain.replace("http://", "").replace("https://", "").strip().strip("/")
        if not clean_domain:
            raise ValueError("Dominio inválido para job individual")

        job = Job(
            job_type=JobType.SINGLE_SCRAPING,
            name=name or f"Single Scraping - {clean_domain}",
            description=description or f"Scraping individual para {clean_domain}",
            config={
                "domain": clean_domain,
                "save_to_db": True,
                "max_retries": 2,
            },
            status=JobStatus.PENDING,
            total_steps=1,
            created_by=created_by,
            priority=7,
        )

        db.add(job)
        db.commit()
        db.refresh(job)

        logger.info(f"Job creado: ID={job.id}, Tipo={job.job_type}, Dominio={clean_domain}")
        return job

    @classmethod
    async def execute_job(cls, job_id: int):
        """
        Ejecuta un job de forma asíncrona.
        Esta función corre en background sin bloquear.
        
        Args:
            job_id: ID del job a ejecutar
        """
        db = SessionLocal()
        
        try:
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} no encontrado")
                return
            
            job.mark_started()
            db.commit()
            
            logger.info(f"Iniciando ejecucion de Job {job_id}: {job.name}")
            
            if job.job_type == JobType.BATCH_SCRAPING:
                await cls._execute_batch_scraping(db, job)
            elif job.job_type == JobType.SINGLE_SCRAPING:
                await cls._execute_single_scraping(db, job)
            else:
                job.mark_failed(f"Tipo de job no soportado: {job.job_type}")
                db.commit()
            
            if job.status == JobStatus.RUNNING:
                result_summary = {
                    "total": job.total_steps,
                    "completed": job.completed_steps,
                    "failed": job.failed_steps,
                    "success_rate": f"{(job.completed_steps / job.total_steps * 100):.1f}%" if job.total_steps > 0 else "0%"
                }
                job.mark_completed(result_summary)
                db.commit()
            
            logger.info(f"Job {job_id} finalizado: {job.status}")
            
        except Exception as e:
            logger.error(f"Error ejecutando Job {job_id}: {str(e)}", exc_info=True)
            try:
                job = db.query(Job).filter(Job.id == job_id).first()
                if job:
                    job.mark_failed(str(e))
                    db.commit()
            except Exception:
                pass
        finally:
            db.close()
            if job_id in cls._running_jobs:
                del cls._running_jobs[job_id]
    
    @classmethod
    async def _execute_single_scraping(cls, db: Session, job: Job):
        """
        Ejecuta un job de scraping individual.
        
        Args:
            db: Sesión de base de datos
            job: Job a ejecutar
        """
        domain = job.config.get("domain")
        if not domain:
            job.mark_failed("Dominio no especificado en configuración")
            db.commit()
            return
        
        # Crear un paso único
        step = JobStep(
            job_id=job.id,
            step_number=1,
            name=f"Scraping: {domain}",
            description=f"Analizar dominio {domain}",
            status=JobStatus.PENDING
        )
        db.add(step)
        job.total_steps = 1
        db.commit()
        
        # Marcar paso como iniciado
        step.mark_started()
        db.commit()
        
        try:
            # Realizar scraping
            result = await scrap_domain(domain)
            
            if result and result.get("success"):
                # Guardar en base de datos
                report = StorageService.save_report(
                    db=db,
                    domain_name=domain,
                    report_data=result
                )
                
                step.mark_completed({
                    "report_id": report.id,
                    "status_code": result.get("status_code"),
                    "domain": domain
                })
                job.completed_steps = 1
            else:
                error = result.get("error") if result else "Error desconocido"
                step.mark_failed(error)
                job.failed_steps = 1
            
            db.commit()
            
        except Exception as e:
            step.mark_failed(str(e))
            job.failed_steps = 1
            db.commit()
    
    @classmethod
    def start_job(cls, job_id: int) -> bool:
        """
        Inicia la ejecucion de un job en background.
        
        Args:
            job_id: ID del job a iniciar
            
        Returns:
            True si se inició correctamente, False si ya estaba corriendo
        """
        if job_id in cls._running_jobs:
            logger.warning(f"Job {job_id} ya esta en ejecucion")
            return False
        
        # Crear tarea asíncrona
        task = asyncio.create_task(cls.execute_job(job_id))
        cls._running_jobs[job_id] = task
        
        logger.info(f"Job {job_id} iniciado en background")
        return True
    
    @classmethod
    def cancel_job(cls, db: Session, job_id: int) -> bool:
        """
        Cancela un job en ejecucion.
        
        Args:
            db: Sesión de base de datos
            job_id: ID del job a cancelar
            
        Returns:
            True si se canceló correctamente
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        
        # Marcar como cancelado en DB
        job.mark_cancelled()
        db.commit()
        
        # Si esta en ejecucion, cancelar la tarea
        if job_id in cls._running_jobs:
            task = cls._running_jobs[job_id]
            task.cancel()
            del cls._running_jobs[job_id]
            logger.info(f"Job {job_id} cancelado")
        
        return True
    
    @classmethod
    def is_job_running(cls, job_id: int) -> bool:
        task = cls._running_jobs.get(job_id)
        return bool(task and not task.done())

    @classmethod
    def delete_job(cls, db: Session, job_id: int) -> bool:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return False
        if cls.is_job_running(job_id):
            raise RuntimeError("Job en ejecucion, cancelalo antes de eliminarlo")
        db.delete(job)
        db.commit()
        logger.info(f"Job {job_id} eliminado")
        return True

    @classmethod
    def retry_job(cls, db: Session, job_id: int) -> Optional[Dict[str, Any]]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        if cls.is_job_running(job_id):
            raise RuntimeError("El job esta en ejecucion, no se puede reintentar")
        allowed_status = {JobStatus.FAILED, JobStatus.CANCELLED, JobStatus.COMPLETED}
        if job.status not in allowed_status:
            raise ValueError("Solo se pueden reintentar jobs fallidos, cancelados o completados")
        job.status = JobStatus.PENDING
        job.started_at = None
        job.completed_at = None
        job.error_message = None
        job.result_summary = None
        job.completed_steps = 0
        job.failed_steps = 0
        steps = db.query(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.step_number).all()
        for step in steps:
            step.status = JobStatus.PENDING
            step.started_at = None
            step.completed_at = None
            step.error_message = None
            step.result_data = None
        job.update_progress()
        db.commit()
        db.refresh(job)
        if not cls.start_job(job_id):
            raise RuntimeError("No se pudo iniciar el job de reintento")
        return job.to_dict(include_steps=False)

    @classmethod
    def get_job_progress(
        cls,
        db: Session,
        job_id: int,
        step_limit: Optional[int] = None
    ) -> Optional[Dict[str, Any]]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        steps_query = db.query(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.step_number)
        all_steps = steps_query.all()
        if step_limit and step_limit > 0:
            steps = all_steps[-step_limit:]
        else:
            steps = all_steps
        step_data = [
            {
                "step_number": step.step_number,
                "name": step.name,
                "status": step.status,
                "started_at": cls._to_iso(step.started_at),
                "completed_at": cls._to_iso(step.completed_at),
                "error_message": step.error_message,
                "result_data": step.result_data,
            }
            for step in steps
        ]
        progress = {
            "id": job.id,
            "job_type": job.job_type,
            "name": job.name,
            "status": job.status,
            "progress_percentage": job.get_progress_percentage(),
            "total_steps": job.total_steps,
            "completed_steps": job.completed_steps,
            "failed_steps": job.failed_steps,
            "running_steps": sum(1 for step in all_steps if step.status == JobStatus.RUNNING),
            "pending_steps": sum(1 for step in all_steps if step.status == JobStatus.PENDING),
            "started_at": cls._to_iso(job.started_at),
            "completed_at": cls._to_iso(job.completed_at),
            "steps": step_data,
        }
        return progress

    @classmethod
    def get_job_logs(cls, db: Session, job_id: int, limit: int = 100) -> Optional[Dict[str, Any]]:
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        steps = db.query(JobStep).filter(JobStep.job_id == job_id).order_by(JobStep.step_number).all()
        if limit and limit > 0:
            selected = steps[-limit:]
        else:
            selected = steps
        logs = [
            {
                "step_number": step.step_number,
                "name": step.name,
                "status": step.status,
                "started_at": cls._to_iso(step.started_at),
                "completed_at": cls._to_iso(step.completed_at),
                "error_message": step.error_message,
                "result_data": step.result_data,
            }
            for step in selected
        ]
        return {
            "job_id": job.id,
            "total_steps": len(steps),
            "returned_steps": len(logs),
            "logs": logs,
        }

    @classmethod
    def get_job_status(cls, db: Session, job_id: int) -> Optional[Dict[str, Any]]:
        """
        Obtiene el estado actual de un job.
        
        Args:
            db: Sesión de base de datos
            job_id: ID del job
            
        Returns:
            Diccionario con el estado del job o None si no existe
        """
        job = db.query(Job).filter(Job.id == job_id).first()
        if not job:
            return None
        
        return job.to_dict(include_steps=True)
    
    @classmethod
    def list_jobs(
        cls,
        db: Session,
        status: Optional[str] = None,
        job_type: Optional[str] = None,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict[str, Any]]:
        """
        Lista jobs con filtros opcionales.
        
        Args:
            db: Sesión de base de datos
            status: Filtrar por estado (opcional)
            job_type: Filtrar por tipo (opcional)
            limit: Número máximo de resultados
            offset: Offset para paginación
            
        Returns:
            Lista de jobs serializados
        """
        query = db.query(Job)
        
        if status:
            query = query.filter(Job.status == status)
        
        if job_type:
            query = query.filter(Job.job_type == job_type)
        
        jobs = query.order_by(Job.created_at.desc()).limit(limit).offset(offset).all()
        
        return [job.to_dict(include_steps=False) for job in jobs]
