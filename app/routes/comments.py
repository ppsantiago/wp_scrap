# app/routes/comments.py
from fastapi import APIRouter, Depends, HTTPException, Query, Path, Body
from sqlalchemy.orm import Session
from app.services.comment_service import CommentService
from app.database import get_db
from typing import List, Optional
from pydantic import BaseModel
import logging

router = APIRouter(prefix="/api/comments", tags=["comments"])
logger = logging.getLogger(__name__)


# Modelos Pydantic para validación
class CommentCreate(BaseModel):
    content_type: str
    object_id: int
    author: str
    content: str
    parent_id: Optional[int] = None


class CommentUpdate(BaseModel):
    content: Optional[str] = None
    author: Optional[str] = None
    is_active: Optional[bool] = None
    is_pinned: Optional[bool] = None


# ============================================================================
# RUTAS ESPECÍFICAS (DEBEN IR PRIMERO)
# ============================================================================

@router.post("", summary="Crear un nuevo comentario")
async def create_comment(
    comment_data: CommentCreate,
    db: Session = Depends(get_db)
):
    """Crea un nuevo comentario asociado a una entidad específica."""
    try:
        comment = CommentService.create_comment(
            db=db,
            content_type=comment_data.content_type,
            object_id=comment_data.object_id,
            author=comment_data.author,
            content=comment_data.content,
            parent_id=comment_data.parent_id
        )

        return {
            "message": "Comentario creado exitosamente",
            "comment": comment.to_dict()
        }
    except Exception as e:
        logger.error(f"Error creando comentario: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/recent", summary="Comentarios recientes")
async def get_recent_comments(
    limit: int = Query(20, ge=1, le=100, description="Número máximo de comentarios"),
    content_type: Optional[str] = Query(None, description="Tipo de entidad específico"),
    db: Session = Depends(get_db)
):
    """Obtiene comentarios recientes de manera global o filtrados por tipo de entidad."""
    comments = CommentService.get_recent_comments(
        db=db,
        limit=limit,
        content_type=content_type
    )

    comments_payload = CommentService.enrich_comments_with_entity_data(
        db=db,
        comments=comments
    )

    return {
        "total_comments": len(comments),
        "limit": limit,
        "content_type_filter": content_type,
        "comments": comments_payload
    }


@router.get("/search", summary="Buscar comentarios")
async def search_comments(
    q: str = Query(..., description="Texto a buscar"),
    content_type: Optional[str] = Query(None, description="Tipo de entidad específico"),
    limit: int = Query(20, ge=1, le=50, description="Número máximo de resultados"),
    db: Session = Depends(get_db)
):
    """Busca comentarios que contengan texto específico."""
    if not q.strip():
        raise HTTPException(status_code=400, detail="El parámetro de búsqueda no puede estar vacío")

    comments = CommentService.search_comments(
        db=db,
        query=q.strip(),
        content_type=content_type,
        limit=limit
    )

    return {
        "query": q,
        "total_results": len(comments),
        "limit": limit,
        "content_type_filter": content_type,
        "comments": [comment.to_dict() for comment in comments]
    }


@router.get("/statistics", summary="Estadísticas de comentarios")
async def get_comment_statistics(
    content_type: Optional[str] = Query(None, description="Tipo de entidad específico"),
    db: Session = Depends(get_db)
):
    """Obtiene estadísticas generales sobre comentarios"""
    stats = CommentService.get_comment_statistics(
        db=db,
        content_type=content_type
    )

    return {
        "content_type_filter": content_type,
        "statistics": stats
    }


@router.get("/entity/{content_type}/{object_id}", summary="Obtener comentarios de una entidad")
async def get_entity_comments(
    content_type: str = Path(..., description="Tipo de entidad (domain, report, etc.)"),
    object_id: int = Path(..., description="ID de la entidad"),
    include_replies: bool = Query(True, description="Incluir respuestas anidadas"),
    include_inactive: bool = Query(False, description="Incluir comentarios inactivos"),
    db: Session = Depends(get_db)
):
    """Obtiene todos los comentarios asociados a una entidad específica."""
    comments = CommentService.get_comments_for_entity(
        db=db,
        content_type=content_type,
        object_id=object_id,
        include_replies=include_replies,
        include_inactive=include_inactive
    )

    return {
        "content_type": content_type,
        "object_id": object_id,
        "total_comments": len(comments),
        "comments": [comment.to_dict() for comment in comments]
    }


@router.get("/thread/{comment_id}", summary="Obtener hilo completo de comentarios")
async def get_comment_thread(
    comment_id: int = Path(..., description="ID del comentario raíz"),
    max_depth: int = Query(5, ge=1, le=10, description="Máxima profundidad de respuestas"),
    db: Session = Depends(get_db)
):
    """Obtiene un hilo completo de comentarios empezando desde un comentario específico."""
    comment = CommentService.get_comment_thread(
        db=db,
        comment_id=comment_id,
        max_depth=max_depth
    )

    if not comment:
        raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")

    return {
        "thread_root": comment_id,
        "comment": comment.to_dict()
    }


@router.get("/author/{author}", summary="Comentarios por autor")
async def get_comments_by_author(
    author: str = Path(..., description="Nombre del autor"),
    limit: int = Query(50, ge=1, le=100, description="Número máximo de comentarios"),
    offset: int = Query(0, ge=0, description="Offset para paginación"),
    db: Session = Depends(get_db)
):
    """Obtiene comentarios de un autor específico"""
    comments = CommentService.get_comments_by_author(
        db=db,
        author=author,
        limit=limit,
        offset=offset
    )

    return {
        "author": author,
        "total_comments": len(comments),
        "limit": limit,
        "offset": offset,
        "comments": [comment.to_dict() for comment in comments]
    }


@router.get("/domain/{domain_id}", summary="Comentarios de un dominio")
async def get_domain_comments(
    domain_id: int = Path(..., description="ID del dominio"),
    include_replies: bool = Query(True, description="Incluir respuestas"),
    db: Session = Depends(get_db)
):
    """Comentarios asociados a un dominio específico"""
    return await get_entity_comments(
        content_type="domain",
        object_id=domain_id,
        include_replies=include_replies,
        db=db
    )


@router.get("/report/{report_id}", summary="Comentarios de un reporte")
async def get_report_comments(
    report_id: int = Path(..., description="ID del reporte"),
    include_replies: bool = Query(True, description="Incluir respuestas"),
    db: Session = Depends(get_db)
):
    """Comentarios asociados a un reporte específico"""
    return await get_entity_comments(
        content_type="report",
        object_id=report_id,
        include_replies=include_replies,
        db=db
    )


@router.get("/job/{job_id}", summary="Comentarios de un job")
async def get_job_comments(
    job_id: int = Path(..., description="ID del job"),
    include_replies: bool = Query(True, description="Incluir respuestas"),
    db: Session = Depends(get_db)
):
    """Comentarios asociados a un job específico"""
    comments = CommentService.get_comments_for_entity(
        db=db,
        content_type="job",
        object_id=job_id,
        include_replies=include_replies,
        include_inactive=False
    )
    
    return {
        "success": True,
        "content_type": "job",
        "object_id": job_id,
        "count": len(comments),
        "comments": [comment.to_dict() for comment in comments]
    }


@router.post("/job", summary="Crear comentario en un job")
async def create_job_comment(
    object_id: int = Body(..., description="ID del job"),
    author: str = Body(..., description="Autor del comentario"),
    content: str = Body(..., description="Contenido del comentario"),
    parent_id: Optional[int] = Body(None, description="ID del comentario padre (para respuestas)"),
    db: Session = Depends(get_db)
):
    """Crea un comentario asociado a un job"""
    try:
        comment = CommentService.create_comment(
            db=db,
            content_type="job",
            object_id=object_id,
            author=author,
            content=content,
            parent_id=parent_id
        )
        
        return {
            "success": True,
            "message": "Comentario creado exitosamente",
            "comment": comment.to_dict()
        }
    except Exception as e:
        logger.error(f"Error creando comentario de job: {str(e)}")
        raise HTTPException(status_code=400, detail=str(e))


# ============================================================================
# RUTAS GENÉRICAS (DEBEN IR AL FINAL)
# ============================================================================

@router.get("/{comment_id}", summary="Obtener comentario específico")
async def get_comment(
    comment_id: int = Path(..., description="ID del comentario"),
    db: Session = Depends(get_db)
):
    """Obtiene un comentario específico por su ID"""
    comment = CommentService.get_comment_by_id(db, comment_id)

    if not comment:
        raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")

    return comment.to_dict()


@router.put("/{comment_id}", summary="Actualizar comentario")
async def update_comment(
    comment_id: int = Path(..., description="ID del comentario"),
    comment_data: CommentUpdate = Body(...),
    db: Session = Depends(get_db)
):
    """Actualiza un comentario existente"""
    comment = CommentService.update_comment(
        db=db,
        comment_id=comment_id,
        content=comment_data.content,
        author=comment_data.author,
        is_active=comment_data.is_active,
        is_pinned=comment_data.is_pinned
    )

    if not comment:
        raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")

    return {
        "message": "Comentario actualizado exitosamente",
        "comment": comment.to_dict()
    }


@router.delete("/{comment_id}", summary="Eliminar comentario")
async def delete_comment(
    comment_id: int = Path(..., description="ID del comentario"),
    soft_delete: bool = Query(True, description="Borrado lógico (true) o físico (false)"),
    db: Session = Depends(get_db)
):
    """Elimina un comentario. Por defecto usa borrado lógico (marca como inactivo)."""
    success = CommentService.delete_comment(
        db=db,
        comment_id=comment_id,
        soft_delete=soft_delete
    )

    if not success:
        raise HTTPException(status_code=404, detail=f"Comentario {comment_id} no encontrado")

    action = "marcado como inactivo" if soft_delete else "eliminado físicamente"
    return {
        "message": f"Comentario {action} exitosamente",
        "comment_id": comment_id,
        "soft_delete": soft_delete
    }
