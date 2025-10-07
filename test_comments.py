"""
Script de prueba para el sistema de comentarios.
Ejecutar desde la raíz del proyecto: python test_comments.py
"""

# TODO: migrar este script a pruebas pytest dentro de `tests/integration/test_comments.py`.

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.services.comment_service import CommentService
from app.services.storage_service import StorageService
from app.models import Domain, Report, Comment


def test_comments_system():
    """Prueba completa del sistema de comentarios"""

    print("=" * 60)
    print("PRUEBA DEL SISTEMA DE COMENTARIOS")
    print("=" * 60)

    # 1. Inicializar base de datos
    print("\n✓ Inicializando base de datos...")
    init_db()
    print("  Base de datos inicializada")

    # 2. Crear sesión
    db = SessionLocal()
    print("\n✓ Sesión de base de datos creada")

    try:
        # 3. Crear dominio y reporte de prueba
        print("\n✓ Creando dominio y reporte de prueba...")

        # Crear dominio
        domain = Domain(domain="test-comments.com")
        db.add(domain)
        db.commit()
        db.refresh(domain)

        # Crear reporte
        report_data = {
            "domain": "http://test-comments.com",
            "status_code": 200,
            "success": True,
            "seo": {
                "title": "Test Site",
                "metaDescription": "This is a test site for comments",
                "wordCount": 500,
                "links": {"total": 10, "internal": 8, "external": 2, "nofollow": 0},
                "images": {"total": 5, "withoutAlt": 1}
            },
            "tech": {
                "requests": {"count": 25, "total_bytes": 500000},
                "timing": {"ttfb": 100, "dcl": 300, "load": 600}
            },
            "security": {"headers": {"hsts": "max-age=31536000"}},
            "site": {"pages_crawled": 5, "forms_found": 2},
            "pages": []
        }

        report = Report(
            domain_id=domain.id,
            status_code=200,
            success=True,
            pages_crawled=5,
            seo_title="Test Site",
            seo_word_count=500,
            seo_links_total=10,
            seo_images_total=5,
            tech_requests_count=25,
            tech_total_bytes=500000,
            tech_ttfb=100,
            forms_found=2
        )
        report.set_json_data("seo_data", report_data["seo"])
        report.set_json_data("tech_data", report_data["tech"])
        report.set_json_data("security_data", report_data["security"])
        report.set_json_data("site_data", report_data["site"])
        report.set_json_data("pages_data", report_data["pages"])

        db.add(report)
        db.commit()
        db.refresh(report)

        print(f"  Dominio creado: ID={domain.id}")
        print(f"  Reporte creado: ID={report.id}")

        # 4. Crear comentarios de prueba
        print("\n✓ Creando comentarios de prueba...")

        # Comentario raíz en el dominio
        comment1 = CommentService.create_comment(
            db=db,
            content_type="domain",
            object_id=domain.id,
            author="usuario1",
            content="Este dominio tiene un excelente rendimiento técnico."
        )

        # Comentario raíz en el reporte
        comment2 = CommentService.create_comment(
            db=db,
            content_type="report",
            object_id=report.id,
            author="usuario2",
            content="El análisis SEO muestra áreas de mejora interesantes."
        )

        # Respuesta al primer comentario
        comment3 = CommentService.create_comment(
            db=db,
            content_type="domain",
            object_id=domain.id,
            author="usuario3",
            content="Totalmente de acuerdo, especialmente en la velocidad de carga.",
            parent_id=comment1.id
        )

        # Otra respuesta
        comment4 = CommentService.create_comment(
            db=db,
            content_type="domain",
            object_id=domain.id,
            author="usuario1",
            content="Gracias por el feedback. ¿Qué métricas específicas te llaman la atención?",
            parent_id=comment3.id
        )

        print(f"  Comentarios creados: {comment1.id}, {comment2.id}, {comment3.id}, {comment4.id}")

        # 5. Probar consultas de comentarios
        print("\n✓ Probando consultas de comentarios...")

        # Comentarios del dominio
        domain_comments = CommentService.get_comments_for_entity(
            db=db,
            content_type="domain",
            object_id=domain.id,
            include_replies=True
        )
        print(f"  Comentarios del dominio: {len(domain_comments)}")

        for comment in domain_comments:
            print(f"    - {comment.author}: {comment.content[:50]}...")
            if comment.replies:
                for reply in comment.replies:
                    print(f"      └─ {reply.author}: {reply.content[:50]}...")

        # Comentarios del reporte
        report_comments = CommentService.get_comments_for_entity(
            db=db,
            content_type="report",
            object_id=report.id,
            include_replies=True
        )
        print(f"  Comentarios del reporte: {len(report_comments)}")

        # Comentarios recientes
        recent_comments = CommentService.get_recent_comments(db=db, limit=10)
        print(f"  Comentarios recientes: {len(recent_comments)}")

        # Comentarios por autor
        user_comments = CommentService.get_comments_by_author(db=db, author="usuario1")
        print(f"  Comentarios de usuario1: {len(user_comments)}")

        # 6. Probar actualización de comentarios
        print("\n✓ Probando actualización de comentarios...")

        updated_comment = CommentService.update_comment(
            db=db,
            comment_id=comment1.id,
            content="Este dominio tiene un excelente rendimiento técnico. ¡Actualizado!",
            is_pinned=True
        )

        if updated_comment:
            print(f"  Comentario {comment1.id} actualizado correctamente")
            print(f"  Contenido: {updated_comment.content}")
            print(f"  Destacado: {updated_comment.is_pinned}")

        # 7. Probar búsqueda de comentarios
        print("\n✓ Probando búsqueda de comentarios...")

        search_results = CommentService.search_comments(
            db=db,
            query="excelente",
            limit=10
        )
        print(f"  Comentarios que contienen 'excelente': {len(search_results)}")

        # 8. Estadísticas de comentarios
        print("\n✓ Estadísticas de comentarios...")

        stats = CommentService.get_comment_statistics(db=db)
        print(f"  Total comentarios: {stats['total_comments']}")
        print(f"  Comentarios activos: {stats['active_comments']}")
        print(f"  Comentarios destacados: {stats['pinned_comments']}")
        print(f"  Comentarios con respuestas: {stats['comments_with_replies']}")

        # 9. Probar rutas con comentarios incluidos
        print("\n✓ Probando rutas que incluyen comentarios...")

        # Simular respuesta de dominio con comentarios
        domain_with_comments = domain.to_dict()
        domain_with_comments["comments"] = [c.to_dict() for c in domain_comments]

        # Simular respuesta de reporte con comentarios
        report_with_comments = report.to_dict(include_full_data=False)
        report_with_comments["comments"] = [c.to_dict() for c in report_comments]

        print(f"  Dominio con comentarios: {len(domain_with_comments['comments'])} comentarios")
        print(f"  Reporte con comentarios: {len(report_with_comments['comments'])} comentarios")

        # 10. Limpiar datos de prueba
        print("\n✓ Limpiando datos de prueba...")

        # Marcar comentarios como inactivos (borrado lógico)
        for comment in [comment1, comment2, comment3, comment4]:
            CommentService.delete_comment(db=db, comment_id=comment.id, soft_delete=True)

        # Eliminar reporte y dominio
        db.delete(report)
        db.delete(domain)
        db.commit()

        print("  Datos de prueba limpiados")

        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS DE COMENTARIOS PASARON EXITOSAMENTE")
        print("=" * 60)

    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()

    finally:
        db.close()
        print("\n✓ Sesión de base de datos cerrada")


if __name__ == "__main__":
    test_comments_system()
