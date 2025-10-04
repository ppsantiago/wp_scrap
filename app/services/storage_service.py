# app/services/storage_service.py
from sqlalchemy.orm import Session
from sqlalchemy import desc, and_
from app.models.domain import Domain, Report
from typing import Optional, List
from datetime import datetime, timedelta
import logging

logger = logging.getLogger(__name__)


class StorageService:
    """
    Servicio para gestionar el almacenamiento de dominios y reportes.
    Maneja toda la lógica de persistencia y consultas.
    """
    
    @staticmethod
    def save_report(db: Session, domain_name: str, report_data: dict) -> Report:
        """
        Guarda un reporte de scraping en la base de datos.
        Crea el dominio si no existe, o actualiza el existente.
        
        Args:
            db: Sesión de SQLAlchemy
            domain_name: Nombre del dominio (ej: "example.com")
            report_data: Diccionario con los datos del scraping
            
        Returns:
            El reporte guardado
        """
        try:
            # Buscar o crear dominio
            domain = db.query(Domain).filter(Domain.domain == domain_name).first()
            
            if not domain:
                domain = Domain(
                    domain=domain_name,
                    first_scraped_at=datetime.utcnow(),
                    last_scraped_at=datetime.utcnow(),
                    total_reports=0,
                    status="active"
                )
                db.add(domain)
                db.flush()  # Para obtener el ID
                logger.info(f"Nuevo dominio creado: {domain_name}")
            else:
                domain.last_scraped_at = datetime.utcnow()
                logger.info(f"Dominio existente actualizado: {domain_name}")
            
            # Extraer datos del reporte
            seo = report_data.get("seo", {})
            tech = report_data.get("tech", {})
            security = report_data.get("security", {})
            site = report_data.get("site", {})
            pages = report_data.get("pages", [])
            
            # Extraer métricas para caché
            links = seo.get("links", {})
            images = seo.get("images", {})
            requests = tech.get("requests", {})
            timing = tech.get("timing", {})
            contacts = site.get("contacts", {})
            
            # Crear reporte
            report = Report(
                domain_id=domain.id,
                scraped_at=datetime.utcnow(),
                status_code=report_data.get("status_code"),
                success=report_data.get("success", False),
                error_message=report_data.get("error"),
                
                # Métricas cacheadas
                pages_crawled=site.get("pages_crawled", 0),
                seo_title=seo.get("title"),
                seo_word_count=seo.get("wordCount"),
                seo_links_total=links.get("total", 0),
                seo_images_total=images.get("total", 0),
                tech_requests_count=requests.get("count", 0),
                tech_total_bytes=requests.get("total_bytes", 0),
                tech_ttfb=timing.get("ttfb"),
                contacts_emails_count=len(contacts.get("emails", [])),
                contacts_phones_count=len(contacts.get("phones", [])),
                forms_found=site.get("forms_found", 0),
            )
            
            # Guardar datos JSON (con compresión automática si son grandes)
            report.set_json_data("seo_data", seo)
            report.set_json_data("tech_data", tech)
            report.set_json_data("security_data", security)
            report.set_json_data("site_data", site)
            report.set_json_data("pages_data", pages)
            
            db.add(report)
            
            # Actualizar contador de reportes del dominio
            domain.total_reports += 1
            
            # Commit
            db.commit()
            db.refresh(report)
            
            logger.info(f"Reporte guardado: ID={report.id}, Domain={domain_name}, Success={report.success}")
            return report
            
        except Exception as e:
            db.rollback()
            logger.error(f"Error guardando reporte para {domain_name}: {str(e)}")
            raise
    
    @staticmethod
    def get_domain_by_name(db: Session, domain_name: str) -> Optional[Domain]:
        """Obtiene un dominio por su nombre"""
        return db.query(Domain).filter(Domain.domain == domain_name).first()
    
    @staticmethod
    def get_domain_by_id(db: Session, domain_id: int) -> Optional[Domain]:
        """Obtiene un dominio por su ID"""
        return db.query(Domain).filter(Domain.id == domain_id).first()
    
    @staticmethod
    def get_all_domains(db: Session, limit: int = 100, offset: int = 0) -> List[Domain]:
        """
        Obtiene todos los dominios con paginación.
        Ordenados por último scraping (más reciente primero).
        """
        return (
            db.query(Domain)
            .order_by(desc(Domain.last_scraped_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    @staticmethod
    def get_report_by_id(db: Session, report_id: int) -> Optional[Report]:
        """Obtiene un reporte por su ID"""
        return db.query(Report).filter(Report.id == report_id).first()
    
    @staticmethod
    def get_latest_report(db: Session, domain_name: str) -> Optional[Report]:
        """Obtiene el reporte más reciente de un dominio"""
        domain = StorageService.get_domain_by_name(db, domain_name)
        if not domain:
            return None
        
        return (
            db.query(Report)
            .filter(Report.domain_id == domain.id)
            .order_by(desc(Report.scraped_at))
            .first()
        )
    
    @staticmethod
    def get_domain_reports(
        db: Session,
        domain_name: str,
        limit: int = 20,
        offset: int = 0,
        success_only: bool = False
    ) -> List[Report]:
        """
        Obtiene todos los reportes de un dominio con paginación.
        Ordenados por fecha (más reciente primero).
        
        Args:
            db: Sesión de base de datos
            domain_name: Nombre del dominio
            limit: Número máximo de reportes a retornar
            offset: Offset para paginación
            success_only: Si True, solo retorna reportes exitosos
        """
        domain = StorageService.get_domain_by_name(db, domain_name)
        if not domain:
            return []
        
        query = db.query(Report).filter(Report.domain_id == domain.id)
        
        if success_only:
            query = query.filter(Report.success == True)
        
        return (
            query
            .order_by(desc(Report.scraped_at))
            .limit(limit)
            .offset(offset)
            .all()
        )
    
    @staticmethod
    def get_recent_reports(
        db: Session,
        days: int = 7,
        limit: int = 50
    ) -> List[Report]:
        """
        Obtiene reportes recientes de todos los dominios.
        
        Args:
            db: Sesión de base de datos
            days: Número de días hacia atrás
            limit: Número máximo de reportes
        """
        cutoff_date = datetime.utcnow() - timedelta(days=days)
        
        return (
            db.query(Report)
            .filter(Report.scraped_at >= cutoff_date)
            .order_by(desc(Report.scraped_at))
            .limit(limit)
            .all()
        )
    
    @staticmethod
    def delete_old_reports(
        db: Session,
        domain_name: str,
        keep_latest: int = 10
    ) -> int:
        """
        Elimina reportes antiguos de un dominio, manteniendo solo los N más recientes.
        
        Args:
            db: Sesión de base de datos
            domain_name: Nombre del dominio
            keep_latest: Cantidad de reportes recientes a mantener
            
        Returns:
            Número de reportes eliminados
        """
        domain = StorageService.get_domain_by_name(db, domain_name)
        if not domain:
            return 0
        
        # Obtener IDs de los reportes a mantener
        keep_ids = [
            r.id for r in db.query(Report.id)
            .filter(Report.domain_id == domain.id)
            .order_by(desc(Report.scraped_at))
            .limit(keep_latest)
            .all()
        ]
        
        if not keep_ids:
            return 0
        
        # Eliminar los reportes que no están en keep_ids
        deleted = (
            db.query(Report)
            .filter(
                and_(
                    Report.domain_id == domain.id,
                    ~Report.id.in_(keep_ids)
                )
            )
            .delete(synchronize_session=False)
        )
        
        db.commit()
        logger.info(f"Eliminados {deleted} reportes antiguos de {domain_name}")
        
        return deleted
    
    @staticmethod
    def get_statistics(db: Session) -> dict:
        """
        Obtiene estadísticas generales de la base de datos.
        """
        total_domains = db.query(Domain).count()
        total_reports = db.query(Report).count()
        successful_reports = db.query(Report).filter(Report.success == True).count()
        failed_reports = db.query(Report).filter(Report.success == False).count()
        
        # Dominio más rastreado
        most_scraped = (
            db.query(Domain)
            .order_by(desc(Domain.total_reports))
            .first()
        )
        
        return {
            "total_domains": total_domains,
            "total_reports": total_reports,
            "successful_reports": successful_reports,
            "failed_reports": failed_reports,
            "success_rate": round(successful_reports / total_reports * 100, 2) if total_reports > 0 else 0,
            "most_scraped_domain": most_scraped.domain if most_scraped else None,
            "most_scraped_count": most_scraped.total_reports if most_scraped else 0
        }
