# app/services/comment_service.py
from sqlalchemy.orm import Session, joinedload
from sqlalchemy import and_, or_, desc, select
from app.models.domain import Comment, Domain, Report
from typing import Optional, List
from datetime import datetime
import logging
from urllib.parse import quote

logger = logging.getLogger(__name__)


class CommentService:
    """
    Servicio para gestionar comentarios asociados a diferentes entidades.
    Maneja operaciones CRUD y consultas avanzadas de comentarios.
    """

    @staticmethod
    def create_comment(
        db: Session,
        content_type: str,
        object_id: int,
        author: str,
        content: str,
        parent_id: Optional[int] = None
    ) -> Comment:
        """
        Crea un nuevo comentario.

        Args:
            db: Sesión de base de datos
            content_type: Tipo de entidad ('domain', 'report', etc.)
            object_id: ID de la entidad comentada
            author: Autor del comentario
            content: Contenido del comentario
            parent_id: ID del comentario padre (para respuestas)

        Returns:
            Comentario creado
        """
        # Verificar que la entidad existe (opcional, pero recomendado)
        CommentService._validate_entity_exists(db, content_type, object_id)

        comment = Comment(
            content_type=content_type,
            object_id=object_id,
            parent_id=parent_id,
            author=author,
            content=content
        )

        db.add(comment)
        db.commit()
        db.refresh(comment)

        logger.info(f"Comentario creado: ID={comment.id}, Tipo={content_type}, Object={object_id}")
        return comment

    @staticmethod
    def get_comment_by_id(db: Session, comment_id: int) -> Optional[Comment]:
        """Obtiene un comentario por su ID"""
        return db.query(Comment).filter(Comment.id == comment_id).first()

    @staticmethod
    def get_comments_for_entity(
        db: Session,
        content_type: str,
        object_id: int,
        include_replies: bool = True,
        include_inactive: bool = False
    ) -> List[Comment]:
        """
        Obtiene todos los comentarios raíz para una entidad específica.

        Args:
            db: Sesión de base de datos
            content_type: Tipo de entidad
            object_id: ID de la entidad
            include_replies: Si incluir respuestas anidadas
            include_inactive: Si incluir comentarios inactivos

        Returns:
            Lista de comentarios ordenados por fecha
        """
        query = db.query(Comment).filter(
            and_(
                Comment.content_type == content_type,
                Comment.object_id == object_id,
                Comment.parent_id.is_(None)  # Solo comentarios raíz
            )
        )

        if not include_inactive:
            query = query.filter(Comment.is_active == True)

        comments = query.order_by(Comment.created_at).all()

        # Cargar respuestas si se solicitan
        if include_replies:
            for comment in comments:
                CommentService._load_comment_replies(db, comment)

        return comments

    @staticmethod
    def get_comment_thread(
        db: Session,
        comment_id: int,
        max_depth: int = 5
    ) -> Optional[Comment]:
        """
        Obtiene un hilo completo de comentarios empezando desde un comentario específico.

        Args:
            db: Sesión de base de datos
            comment_id: ID del comentario raíz del hilo
            max_depth: Máxima profundidad de respuestas a cargar

        Returns:
            Comentario raíz con todas sus respuestas cargadas
        """
        comment = CommentService.get_comment_by_id(db, comment_id)
        if not comment:
            return None

        CommentService._load_comment_replies_recursive(db, comment, max_depth)
        return comment

    @staticmethod
    def update_comment(
        db: Session,
        comment_id: int,
        content: Optional[str] = None,
        author: Optional[str] = None,
        is_active: Optional[bool] = None,
        is_pinned: Optional[bool] = None
    ) -> Optional[Comment]:
        """
        Actualiza un comentario existente.

        Args:
            db: Sesión de base de datos
            comment_id: ID del comentario a actualizar
            content: Nuevo contenido (opcional)
            author: Nuevo autor (opcional)
            is_active: Nuevo estado activo (opcional)
            is_pinned: Nuevo estado destacado (opcional)

        Returns:
            Comentario actualizado o None si no existe
        """
        comment = CommentService.get_comment_by_id(db, comment_id)
        if not comment:
            return None

        if content is not None:
            comment.content = content
        if author is not None:
            comment.author = author
        if is_active is not None:
            comment.is_active = is_active
        if is_pinned is not None:
            comment.is_pinned = is_pinned

        comment.updated_at = datetime.utcnow()
        db.commit()
        db.refresh(comment)

        logger.info(f"Comentario actualizado: ID={comment_id}")
        return comment

    @staticmethod
    def delete_comment(db: Session, comment_id: int, soft_delete: bool = True) -> bool:
        """
        Elimina un comentario (borrado físico o lógico).

        Args:
            db: Sesión de base de datos
            comment_id: ID del comentario a eliminar
            soft_delete: Si True, marca como inactivo; si False, elimina físicamente

        Returns:
            True si se eliminó correctamente, False si no existe
        """
        comment = CommentService.get_comment_by_id(db, comment_id)
        if not comment:
            return False

        if soft_delete:
            # Borrado lógico: marcar como inactivo
            comment.is_active = False
            comment.updated_at = datetime.utcnow()
            db.commit()
            logger.info(f"Comentario marcado como inactivo: ID={comment_id}")
        else:
            # Borrado físico: eliminar completamente
            db.delete(comment)
            db.commit()
            logger.info(f"Comentario eliminado físicamente: ID={comment_id}")

        return True

    @staticmethod
    def get_comments_by_author(
        db: Session,
        author: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Comment]:
        """
        Obtiene comentarios de un autor específico.

        Args:
            db: Sesión de base de datos
            author: Nombre del autor
            limit: Número máximo de comentarios
            offset: Offset para paginación

        Returns:
            Lista de comentarios del autor
        """
        return (
            db.query(Comment)
            .filter(Comment.author == author)
            .order_by(desc(Comment.created_at))
            .limit(limit)
            .offset(offset)
            .all()
        )

    @staticmethod
    def get_recent_comments(
        db: Session,
        limit: int = 20,
        content_type: Optional[str] = None
    ) -> List[Comment]:
        """
        Obtiene comentarios recientes de manera global o filtrados por tipo.

        Args:
            db: Sesión de base de datos
            limit: Número máximo de comentarios
            content_type: Tipo de entidad específico (opcional)

        Returns:
            Lista de comentarios recientes
        """
        query = db.query(Comment).filter(Comment.is_active == True)

        if content_type:
            query = query.filter(Comment.content_type == content_type)

        return (
            query
            .order_by(desc(Comment.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def enrich_comments_with_entity_data(
        db: Session,
        comments: List[Comment]
    ) -> List[dict]:
        """Convierte comentarios a dict y agrega información de la entidad asociada."""
        if not comments:
            return []

        domain_ids = {comment.object_id for comment in comments if comment.content_type == "domain"}
        report_ids = {comment.object_id for comment in comments if comment.content_type == "report"}

        domain_map = {}
        if domain_ids:
            domain_rows = db.query(Domain).filter(Domain.id.in_(domain_ids)).all()
            domain_map = {domain.id: domain for domain in domain_rows}

        report_map = {}
        if report_ids:
            report_rows = (
                db.query(Report)
                .options(joinedload(Report.domain))
                .filter(Report.id.in_(report_ids))
                .all()
            )
            report_map = {report.id: report for report in report_rows}

        enriched_comments: List[dict] = []
        for comment in comments:
            comment_dict = comment.to_dict()
            entity_info = None

            if comment.content_type == "domain":
                domain = domain_map.get(comment.object_id)
                if domain:
                    domain_slug = quote(domain.domain, safe="")
                    entity_info = {
                        "type": "domain",
                        "id": domain.id,
                        "name": domain.domain,
                        "label": f"Dominio: {domain.domain}",
                        "url": f"/domain/{domain_slug}"
                    }
            elif comment.content_type == "report":
                report = report_map.get(comment.object_id)
                if report:
                    entity_info = {
                        "type": "report",
                        "id": report.id,
                        "label": f"Reporte #{report.id}",
                        "url": f"/report/{report.id}"
                    }

                    if report.domain:
                        domain_slug = quote(report.domain.domain, safe="")
                        entity_info["domain"] = {
                            "id": report.domain.id,
                            "name": report.domain.domain,
                            "url": f"/domain/{domain_slug}"
                        }

            if entity_info:
                comment_dict["entity"] = entity_info

            enriched_comments.append(comment_dict)

        return enriched_comments

    @staticmethod
    def search_comments(
        db: Session,
        query: str,
        content_type: Optional[str] = None,
        limit: int = 20
    ) -> List[Comment]:
        """
        Busca comentarios que contengan texto específico.

        Args:
            db: Sesión de base de datos
            query: Texto a buscar
            content_type: Tipo de entidad específico (opcional)
            limit: Número máximo de resultados

        Returns:
            Lista de comentarios que coinciden con la búsqueda
        """
        search_query = db.query(Comment).filter(
            and_(
                Comment.is_active == True,
                Comment.content.ilike(f"%{query}%")
            )
        )

        if content_type:
            search_query = search_query.filter(Comment.content_type == content_type)

        return (
            search_query
            .order_by(desc(Comment.created_at))
            .limit(limit)
            .all()
        )

    @staticmethod
    def get_comment_statistics(db: Session, content_type: Optional[str] = None) -> dict:
        """
        Obtiene estadísticas sobre comentarios.

        Args:
            db: Sesión de base de datos
            content_type: Tipo de entidad específico (opcional)

        Returns:
            Diccionario con estadísticas
        """
        query = db.query(Comment)

        if content_type:
            query = query.filter(Comment.content_type == content_type)

        total_comments = query.count()
        active_comments = query.filter(Comment.is_active == True).count()
        pinned_comments = query.filter(Comment.is_pinned == True).count()

        # Comentarios con respuestas
        replies_parent_ids = select(Comment.parent_id).where(Comment.parent_id.isnot(None))

        comments_with_replies = (
            db.query(Comment.id)
            .filter(Comment.parent_id.is_(None))
            .filter(Comment.id.in_(replies_parent_ids))
            .count()
        )

        return {
            "total_comments": total_comments,
            "active_comments": active_comments,
            "pinned_comments": pinned_comments,
            "comments_with_replies": comments_with_replies,
            "inactive_comments": total_comments - active_comments
        }

    @staticmethod
    def _validate_entity_exists(db: Session, content_type: str, object_id: int) -> bool:
        """
        Valida que la entidad comentada existe.

        Args:
            db: Sesión de base de datos
            content_type: Tipo de entidad
            object_id: ID de la entidad

        Returns:
            True si existe, False en caso contrario
        """
        if content_type == "domain":
            return db.query(Domain).filter(Domain.id == object_id).first() is not None
        elif content_type == "report":
            return db.query(Report).filter(Report.id == object_id).first() is not None
        else:
            # Para tipos futuros, asumir que existe por ahora
            return True

    @staticmethod
    def _load_comment_replies(db: Session, comment: Comment, max_depth: int = 3):
        """
        Carga recursivamente las respuestas de un comentario.

        Args:
            db: Sesión de base de datos
            comment: Comentario padre
            max_depth: Máxima profundidad de carga
        """
        if max_depth <= 0:
            return

        # Obtener respuestas directas
        replies = (
            db.query(Comment)
            .filter(
                and_(
                    Comment.parent_id == comment.id,
                    Comment.is_active == True
                )
            )
            .order_by(Comment.created_at)
            .all()
        )

        comment.replies = replies

        # Cargar respuestas de respuestas
        for reply in replies:
            CommentService._load_comment_replies(db, reply, max_depth - 1)

    @staticmethod
    def _load_comment_replies_recursive(db: Session, comment: Comment, max_depth: int = 5):
        """
        Carga respuestas de manera recursiva con límite de profundidad.

        Args:
            db: Sesión de base de datos
            comment: Comentario raíz
            max_depth: Máxima profundidad
        """
        CommentService._load_comment_replies(db, comment, max_depth)
