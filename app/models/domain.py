# app/models/domain.py
from sqlalchemy import Column, Integer, String, DateTime, Boolean, Text, ForeignKey, Index, UniqueConstraint, func, and_
from sqlalchemy.orm import relationship
from datetime import datetime
from app.database import Base
import json
import zlib
import base64


class Comment(Base):
    """
    Modelo independiente para comentarios que pueden estar asociados a diferentes entidades.
    Soporta hilos de comentarios con respuestas anidadas.
    """
    __tablename__ = "comments"

    id = Column(Integer, primary_key=True, index=True)
    content_type = Column(String(50), nullable=False, index=True)  # domain, report, etc.
    object_id = Column(Integer, nullable=False, index=True)  # ID de la entidad comentada
    parent_id = Column(Integer, ForeignKey("comments.id"), index=True)  # Para respuestas anidadas

    # Información del comentario
    author = Column(String(255), nullable=False)  # Por ahora texto, futuro: user_id
    content = Column(Text, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Estado del comentario
    is_active = Column(Boolean, default=True, index=True)
    is_pinned = Column(Boolean, default=False)  # Comentarios destacados

    # Relaciones
    parent = relationship("Comment", remote_side=[id])  # Comentario padre
    replies = relationship("Comment", remote_side=[parent_id])  # Respuestas

    # Índices compuestos para consultas eficientes
    __table_args__ = (
        Index('idx_comment_entity', 'content_type', 'object_id'),
        Index('idx_comment_thread', 'parent_id', 'created_at'),
    )

    def to_dict(self, include_replies: bool = True):
        """Serializa el comentario a diccionario"""
        data = {
            "id": self.id,
            "content_type": self.content_type,
            "object_id": self.object_id,
            "parent_id": self.parent_id,
            "author": self.author,
            "content": self.content,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "is_active": self.is_active,
            "is_pinned": self.is_pinned,
            "reply_count": len(self.replies) if self.replies else 0
        }

        if include_replies and self.replies:
            data["replies"] = [reply.to_dict(include_replies=False) for reply in self.replies]

        return data

    def add_reply(self, author: str, content: str):
        """Agrega una respuesta a este comentario"""
        reply = Comment(
            content_type=self.content_type,
            object_id=self.object_id,
            parent_id=self.id,
            author=author,
            content=content
        )
        return reply

    @classmethod
    def get_comments_for_entity(cls, db_session, content_type: str, object_id: int):
        """Obtiene todos los comentarios raíz para una entidad específica"""
        return db_session.query(cls).filter(
            and_(
                cls.content_type == content_type,
                cls.object_id == object_id,
                cls.parent_id.is_(None),
                cls.is_active == True
            )
        ).order_by(cls.created_at).all()


class Domain(Base):
    """
    Modelo que representa un dominio rastreado.
    Mantiene metadatos y relación con múltiples reportes históricos.
    """
    __tablename__ = "domains"

    id = Column(Integer, primary_key=True, index=True)
    domain = Column(String(255), unique=True, index=True, nullable=False)
    first_scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_scraped_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    total_reports = Column(Integer, default=0)
    status = Column(String(50), default="active")  # active, archived, error

    # Relación con reportes
    reports = relationship("Report", back_populates="domain", cascade="all, delete-orphan")

    # Índice compuesto para consultas por estado y fecha
    __table_args__ = (
        Index('idx_domain_status_date', 'status', 'last_scraped_at'),
    )

    def to_dict(self):
        """Serializa el dominio a diccionario"""
        return {
            "id": self.id,
            "domain": self.domain,
            "first_scraped_at": self.first_scraped_at.isoformat() if self.first_scraped_at else None,
            "last_scraped_at": self.last_scraped_at.isoformat() if self.last_scraped_at else None,
            "total_reports": self.total_reports,
            "status": self.status
        }


class TrustedContact(Base):
    """Modelo que almacena el contacto de confianza seleccionado para un dominio."""
    __tablename__ = "trusted_contacts"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="SET NULL"), nullable=True, index=True)
    email = Column(String(255), nullable=True)
    phone = Column(String(50), nullable=True)
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    domain = relationship("Domain", backref="trusted_contacts")
    report = relationship("Report")

    __table_args__ = (
        Index("idx_trusted_contact_domain_active", "domain_id", "is_active"),
    )

    def to_dict(self):
        return {
            "id": self.id,
            "domain_id": self.domain_id,
            "report_id": self.report_id,
            "email": self.email,
            "phone": self.phone,
            "is_active": self.is_active,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }


class Report(Base):
    """
    Modelo que representa un reporte de scraping de un dominio.
    Almacena datos completos en JSON (comprimido si es grande).
    """
    __tablename__ = "reports"

    id = Column(Integer, primary_key=True, index=True)
    domain_id = Column(Integer, ForeignKey("domains.id", ondelete="CASCADE"), nullable=False)
    scraped_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    # Metadatos del scraping
    status_code = Column(Integer)
    success = Column(Boolean, nullable=False, default=False)
    error_message = Column(Text)

    # Datos completos como JSON (pueden estar comprimidos)
    seo_data = Column(Text)
    tech_data = Column(Text)
    security_data = Column(Text)
    site_data = Column(Text)
    pages_data = Column(Text)  # Array de páginas individuales

    is_compressed = Column(Boolean, default=False)  # Indica si los datos están comprimidos

    # Métricas cacheadas para consultas rápidas (sin parsear JSON)
    pages_crawled = Column(Integer, default=0)
    seo_title = Column(String(500))
    seo_word_count = Column(Integer)
    seo_links_total = Column(Integer)
    seo_images_total = Column(Integer)
    tech_requests_count = Column(Integer)
    tech_total_bytes = Column(Integer)
    tech_ttfb = Column(Integer)  # Time to first byte
    contacts_emails_count = Column(Integer, default=0)
    contacts_phones_count = Column(Integer, default=0)
    forms_found = Column(Integer, default=0)

    # Relación con dominio
    domain = relationship("Domain", back_populates="reports")
    generated_reports = relationship(
        "GeneratedReport",
        back_populates="report",
        cascade="all, delete-orphan",
        order_by="GeneratedReport.created_at.desc()",
    )

    # Índices compuestos para consultas eficientes
    __table_args__ = (
        Index('idx_report_domain_date', 'domain_id', 'scraped_at'),
        Index('idx_report_success', 'success', 'scraped_at'),
    )

    @staticmethod
    def _compress_if_large(data: str, threshold: int = 10000) -> tuple[str, bool]:
        """
        Comprime el string JSON si supera el threshold (en caracteres).
        Retorna (data, is_compressed)
        """
        if len(data) > threshold:
            compressed = zlib.compress(data.encode('utf-8'))
            encoded = base64.b64encode(compressed).decode('ascii')
            return encoded, True
        return data, False

    @staticmethod
    def _decompress_if_needed(data: str, is_compressed: bool) -> str:
        """Descomprime el string si es necesario"""
        if not data:
            return "{}"
        if is_compressed:
            try:
                decoded = base64.b64decode(data.encode('ascii'))
                return zlib.decompress(decoded).decode('utf-8')
            except (UnicodeEncodeError, ValueError, zlib.error):
                # Si el flag indica compresión pero los datos no están codificados en base64,
                # devolvemos el string original para evitar errores en reportes antiguos.
                return data
        return data

    def set_json_data(self, field: str, data: dict):
        """Serializa y opcionalmente comprime datos JSON"""
        json_str = json.dumps(data, ensure_ascii=False)
        compressed_str, is_compressed = self._compress_if_large(json_str)
        setattr(self, field, compressed_str)
        if is_compressed:
            self.is_compressed = True

    def get_json_data(self, field: str) -> dict:
        """Deserializa y opcionalmente descomprime datos JSON"""
        raw_data = getattr(self, field, None)
        if not raw_data:
            return {}
        json_str = self._decompress_if_needed(raw_data, self.is_compressed)
        try:
            return json.loads(json_str)
        except json.JSONDecodeError:
            try:
                decoded = base64.b64decode(json_str.encode("ascii"))
                inflated = zlib.decompress(decoded).decode("utf-8")
                return json.loads(inflated)
            except Exception:
                return {}

    def to_dict(self, include_full_data: bool = False):
        """
        Serializa el reporte a diccionario.

        Args:
            include_full_data: Si True, incluye todos los datos JSON completos.
                              Si False, solo incluye métricas cacheadas (más rápido).
        """
        base = {
            "id": self.id,
            "domain_id": self.domain_id,
            "scraped_at": self.scraped_at.isoformat() if self.scraped_at else None,
            "status_code": self.status_code,
            "success": self.success,
            "error_message": self.error_message,
            "metrics": {
                "pages_crawled": self.pages_crawled,
                "seo_title": self.seo_title,
                "seo_word_count": self.seo_word_count,
                "seo_links_total": self.seo_links_total,
                "seo_images_total": self.seo_images_total,
                "tech_requests_count": self.tech_requests_count,
                "tech_total_bytes": self.tech_total_bytes,
                "tech_ttfb": self.tech_ttfb,
                "contacts_emails_count": self.contacts_emails_count,
                "contacts_phones_count": self.contacts_phones_count,
                "forms_found": self.forms_found,
            }
        }

        if include_full_data:
            base.update({
                "seo": self.get_json_data("seo_data"),
                "tech": self.get_json_data("tech_data"),
                "security": self.get_json_data("security_data"),
                "site": self.get_json_data("site_data"),
                "pages": self.get_json_data("pages_data"),
            })

        return base


    def to_frontend_format(self):
        """
        Convierte el reporte al formato esperado por el frontend.
        Compatible con la estructura actual de domainForm.js
        """
        return {
            "domain": self.domain.domain if self.domain else "unknown",
            "status_code": self.status_code,
            "success": self.success,
            "error": self.error_message,
            "seo": self.get_json_data("seo_data"),
            "tech": self.get_json_data("tech_data"),
            "security": self.get_json_data("security_data"),
            "site": self.get_json_data("site_data"),
            "pages": self.get_json_data("pages_data"),
        }


class ReportPrompt(Base):
    """Plantilla de prompt por tipo de reporte IA."""

    __tablename__ = "report_prompts"

    id = Column(Integer, primary_key=True, index=True)
    type = Column(String(50), nullable=False, unique=True, index=True)
    prompt_template = Column(Text, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
    updated_by = Column(String(255), nullable=True)

    __table_args__ = (
        UniqueConstraint("type", name="uq_report_prompt_type"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "type": self.type,
            "prompt_template": self.prompt_template,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
            "updated_by": self.updated_by,
        }


class ReportGenerationLog(Base):
    """Historial de generaciones IA para auditoría y cache."""

    __tablename__ = "report_generation_logs"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    prompt_id = Column(Integer, ForeignKey("report_prompts.id", ondelete="SET NULL"), nullable=True, index=True)
    type = Column(String(50), nullable=False, index=True)
    status = Column(String(50), nullable=False, index=True)
    duration_ms = Column(Integer, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    cached = Column(Boolean, default=False)
    markdown_output = Column(Text, nullable=True)
    error_message = Column(Text, nullable=True)
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)

    report = relationship("Report", backref="generation_logs")
    prompt = relationship("ReportPrompt")

    __table_args__ = (
        Index("idx_report_generation_type_report", "type", "report_id"),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "prompt_id": self.prompt_id,
            "type": self.type,
            "status": self.status,
            "duration_ms": self.duration_ms,
            "tokens_used": self.tokens_used,
            "cached": self.cached,
            "markdown_output": self.markdown_output,
            "error_message": self.error_message,
            "metadata": self.metadata_json,
            "created_at": self.created_at.isoformat() if self.created_at else None,
        }


class GeneratedReport(Base):
    """Persistencia de salidas IA generadas para un reporte base."""

    __tablename__ = "generated_reports"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("reports.id", ondelete="CASCADE"), nullable=False, index=True)
    type = Column(String(50), nullable=False, index=True)
    markdown = Column(Text, nullable=False)
    tags_json = Column("tags", Text, nullable=True)
    metadata_json = Column("metadata", Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False, index=True)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    report = relationship("Report", back_populates="generated_reports")

    __table_args__ = (
        Index("idx_generated_report_unique", "report_id", "type", unique=True),
    )

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "report_id": self.report_id,
            "type": self.type,
            "markdown": self.markdown,
            "tags": self.get_tags(),
            "metadata": self.get_metadata(),
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }

    def set_tags(self, tags: list[str] | None) -> None:
        if tags is None:
            self.tags_json = None
            return
        self.tags_json = json.dumps(tags, ensure_ascii=False)

    def get_tags(self) -> list[str]:
        if not self.tags_json:
            return []
        try:
            data = json.loads(self.tags_json)
            return data if isinstance(data, list) else []
        except json.JSONDecodeError:
            return []

    def set_metadata(self, metadata: dict | None) -> None:
        if metadata is None:
            self.metadata_json = None
            return
        self.metadata_json = json.dumps(metadata, ensure_ascii=False)

    def get_metadata(self) -> dict:
        if not self.metadata_json:
            return {}
        try:
            data = json.loads(self.metadata_json)
            return data if isinstance(data, dict) else {}
        except json.JSONDecodeError:
            return {}
