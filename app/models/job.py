# app/models/job.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index, JSON
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
from enum import Enum


class JobStatus(str, Enum):
    """Estados posibles de un Job"""
    PENDING = "pending"          # Creado, esperando ejecución
    RUNNING = "running"          # En ejecución
    COMPLETED = "completed"      # Completado exitosamente
    FAILED = "failed"            # Falló con error
    CANCELLED = "cancelled"      # Cancelado por el usuario
    PAUSED = "paused"           # Pausado temporalmente


class JobType(str, Enum):
    """Tipos de trabajos disponibles"""
    BATCH_SCRAPING = "batch_scraping"     # Scraping en lote de múltiples dominios
    SINGLE_SCRAPING = "single_scraping"   # Scraping de un solo dominio
    REPORT_GENERATION = "report_generation"  # Generación de reportes
    DATA_EXPORT = "data_export"           # Exportación de datos


class JobStep(Base):
    """
    Modelo para representar un paso individual de un Job.
    Permite seguimiento granular del progreso.
    """
    __tablename__ = "job_steps"

    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id", ondelete="CASCADE"), nullable=False, index=True)
    
    # Información del paso
    step_number = Column(Integer, nullable=False)  # Orden del paso
    name = Column(String(255), nullable=False)      # Nombre descriptivo
    description = Column(Text)                      # Descripción detallada
    
    # Estado del paso
    status = Column(String(50), nullable=False, default=JobStatus.PENDING)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Resultado
    result_data = Column(JSON)  # Datos del resultado (ej: report_id, errores, etc.)
    error_message = Column(Text)
    
    # Relación con Job
    job = relationship("Job", back_populates="steps")
    
    # Índices
    __table_args__ = (
        Index('idx_step_job_number', 'job_id', 'step_number'),
    )

    def to_dict(self):
        """Serializa el paso a diccionario"""
        return {
            "id": self.id,
            "job_id": self.job_id,
            "step_number": self.step_number,
            "name": self.name,
            "description": self.description,
            "status": self.status,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "result_data": self.result_data,
            "error_message": self.error_message,
        }

    def mark_started(self):
        """Marca el paso como iniciado"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result_data=None):
        """Marca el paso como completado"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result_data:
            self.result_data = result_data

    def mark_failed(self, error_message: str):
        """Marca el paso como fallido"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message


class Job(Base):
    """
    Modelo que representa un trabajo (job) en lote.
    Permite ejecución asíncrona de tareas sin bloquear la UI.
    """
    __tablename__ = "jobs"

    id = Column(Integer, primary_key=True, index=True)
    
    # Tipo y configuración
    job_type = Column(String(50), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    description = Column(Text)
    
    # Configuración del job (parámetros, opciones, etc.)
    config = Column(JSON)  # ej: {"domains": ["example.com", "test.com"], "options": {...}}
    
    # Estado general
    status = Column(String(50), nullable=False, default=JobStatus.PENDING, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    started_at = Column(DateTime)
    completed_at = Column(DateTime)
    
    # Progreso
    total_steps = Column(Integer, default=0)
    completed_steps = Column(Integer, default=0)
    failed_steps = Column(Integer, default=0)
    
    # Resultados
    result_summary = Column(JSON)  # Resumen de resultados
    error_message = Column(Text)
    
    # Metadata
    created_by = Column(String(255))  # Usuario que creó el job
    priority = Column(Integer, default=5)  # 1-10, mayor = más prioritario
    
    # Relaciones
    steps = relationship("JobStep", back_populates="job", cascade="all, delete-orphan", order_by="JobStep.step_number")
    
    # Índices compuestos
    __table_args__ = (
        Index('idx_job_status_created', 'status', 'created_at'),
        Index('idx_job_type_status', 'job_type', 'status'),
    )

    def to_dict(self, include_steps: bool = False):
        """
        Serializa el job a diccionario.
        
        Args:
            include_steps: Si True, incluye todos los pasos.
        """
        data = {
            "id": self.id,
            "job_type": self.job_type,
            "name": self.name,
            "description": self.description,
            "config": self.config,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_steps": self.total_steps,
            "completed_steps": self.completed_steps,
            "failed_steps": self.failed_steps,
            "progress_percentage": self.get_progress_percentage(),
            "result_summary": self.result_summary,
            "error_message": self.error_message,
            "created_by": self.created_by,
            "priority": self.priority,
        }
        
        if include_steps and self.steps:
            data["steps"] = [step.to_dict() for step in self.steps]
        
        return data

    def get_progress_percentage(self) -> int:
        """Calcula el porcentaje de progreso"""
        if self.total_steps == 0:
            return 0
        return int((self.completed_steps / self.total_steps) * 100)

    def mark_started(self):
        """Marca el job como iniciado"""
        self.status = JobStatus.RUNNING
        self.started_at = datetime.utcnow()

    def mark_completed(self, result_summary=None):
        """Marca el job como completado"""
        self.status = JobStatus.COMPLETED
        self.completed_at = datetime.utcnow()
        if result_summary:
            self.result_summary = result_summary

    def mark_failed(self, error_message: str):
        """Marca el job como fallido"""
        self.status = JobStatus.FAILED
        self.completed_at = datetime.utcnow()
        self.error_message = error_message

    def mark_cancelled(self):
        """Marca el job como cancelado"""
        self.status = JobStatus.CANCELLED
        self.completed_at = datetime.utcnow()

    def update_progress(self):
        """Actualiza contadores de progreso basado en los pasos"""
        if self.steps:
            self.completed_steps = sum(1 for step in self.steps if step.status == JobStatus.COMPLETED)
            self.failed_steps = sum(1 for step in self.steps if step.status == JobStatus.FAILED)

    def add_step(self, name: str, description: str = None) -> 'JobStep':
        """Agrega un paso al job"""
        step = JobStep(
            job_id=self.id,
            step_number=self.total_steps + 1,
            name=name,
            description=description,
            status=JobStatus.PENDING
        )
        self.total_steps += 1
        return step
