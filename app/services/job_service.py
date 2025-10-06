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
    
    # Registro de jobs en ejecución (job_id -> asyncio.Task)
    _running_jobs: Dict[int, asyncio.Task] = {}
    
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
    async def execute_job(cls, job_id: int):
        """
        Ejecuta un job de forma asíncrona.
        Esta función corre en background sin bloquear.
        
        Args:
            job_id: ID del job a ejecutar
        """
        # Crear una nueva sesión para este job
        db = SessionLocal()
        
        try:
            # Obtener el job
            job = db.query(Job).filter(Job.id == job_id).first()
            if not job:
                logger.error(f"Job {job_id} no encontrado")
                return
            
            # Marcar como iniciado
            job.mark_started()
            db.commit()
            
            logger.info(f"Iniciando ejecución de Job {job_id}: {job.name}")
            
            # Ejecutar según tipo
            if job.job_type == JobType.BATCH_SCRAPING:
                await cls._execute_batch_scraping(db, job)
            elif job.job_type == JobType.SINGLE_SCRAPING:
                await cls._execute_single_scraping(db, job)
            else:
                job.mark_failed(f"Tipo de job no soportado: {job.job_type}")
                db.commit()
            
            # Si terminó sin errores, marcar como completado
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
            except:
                pass
        finally:
            db.close()
            # Remover del registro de jobs en ejecución
            if job_id in cls._running_jobs:
                del cls._running_jobs[job_id]
    
    @classmethod
    async def _execute_batch_scraping(cls, db: Session, job: Job):
        """
        Ejecuta un job de scraping en lote.
        
        Args:
            db: Sesión de base de datos
            job: Job a ejecutar
        """
        domains = job.config.get("domains", [])
        max_retries = job.config.get("max_retries", 2)
        
        # Obtener pasos
        steps = db.query(JobStep).filter(
            JobStep.job_id == job.id
        ).order_by(JobStep.step_number).all()
        
        for step in steps:
            # Verificar si el job fue cancelado
            db.refresh(job)
            if job.status == JobStatus.CANCELLED:
                logger.info(f"Job {job.id} cancelado, deteniendo ejecución")
                break
            
            domain_idx = step.step_number - 1
            if domain_idx >= len(domains):
                continue
                
            domain = domains[domain_idx]
            
            # Marcar paso como iniciado
            step.mark_started()
            db.commit()
            
            logger.info(f"Job {job.id} - Paso {step.step_number}/{job.total_steps}: {domain}")
            
            # Intentar scraping con reintentos
            success = False
            last_error = None
            
            for attempt in range(max_retries + 1):
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
                        
                        # Marcar paso como completado
                        step.mark_completed({
                            "report_id": report.id,
                            "status_code": result.get("status_code"),
                            "domain": domain
                        })
                        
                        success = True
                        logger.info(f"Job {job.id} - Paso {step.step_number} completado: {domain}")
                        break
                    else:
                        last_error = result.get("error") if result else "Error desconocido"
                        
                except Exception as e:
                    last_error = str(e)
                    logger.error(f"Job {job.id} - Error en paso {step.step_number} (intento {attempt + 1}): {str(e)}")
                
                # Esperar antes de reintentar
                if attempt < max_retries:
                    await asyncio.sleep(2)
            
            # Si no tuvo éxito después de todos los intentos
            if not success:
                step.mark_failed(last_error or "Error en scraping")
                logger.warning(f"Job {job.id} - Paso {step.step_number} falló después de {max_retries + 1} intentos")
            
            db.commit()
            
            # Actualizar progreso del job
            job.update_progress()
            db.commit()
            
            # Pequeña pausa entre dominios para no sobrecargar
            await asyncio.sleep(1)
    
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
        Inicia la ejecución de un job en background.
        
        Args:
            job_id: ID del job a iniciar
            
        Returns:
            True si se inició correctamente, False si ya estaba corriendo
        """
        if job_id in cls._running_jobs:
            logger.warning(f"Job {job_id} ya está en ejecución")
            return False
        
        # Crear tarea asíncrona
        task = asyncio.create_task(cls.execute_job(job_id))
        cls._running_jobs[job_id] = task
        
        logger.info(f"Job {job_id} iniciado en background")
        return True
    
    @classmethod
    def cancel_job(cls, db: Session, job_id: int) -> bool:
        """
        Cancela un job en ejecución.
        
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
        
        # Si está en ejecución, cancelar la tarea
        if job_id in cls._running_jobs:
            task = cls._running_jobs[job_id]
            task.cancel()
            del cls._running_jobs[job_id]
            logger.info(f"Job {job_id} cancelado")
        
        return True
    
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
