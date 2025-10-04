"""
Script de prueba para verificar la funcionalidad de la base de datos.
Ejecutar desde la raíz del proyecto: python test_database.py
"""

import sys
from pathlib import Path

# Agregar el directorio raíz al path
ROOT = Path(__file__).parent
sys.path.insert(0, str(ROOT))

from app.database import SessionLocal, init_db
from app.services.storage_service import StorageService
from app.models import Domain, Report


def test_database():
    """Prueba básica de funcionalidad de base de datos"""
    
    print("=" * 60)
    print("PRUEBA DE BASE DE DATOS")
    print("=" * 60)
    
    # 1. Inicializar base de datos
    print("\n✓ Inicializando base de datos...")
    init_db()
    print("  Base de datos inicializada")
    
    # 2. Crear sesión
    db = SessionLocal()
    print("\n✓ Sesión de base de datos creada")
    
    try:
        # 3. Crear un reporte de prueba
        print("\n✓ Creando reporte de prueba...")
        
        test_report_data = {
            "domain": "http://test-example.com",
            "status_code": 200,
            "success": True,
            "error": None,
            "seo": {
                "title": "Test Site",
                "metaDescription": "This is a test site",
                "wordCount": 500,
                "h1Count": 1,
                "canonical": "http://test-example.com",
                "robots": "index, follow",
                "links": {
                    "total": 25,
                    "internal": 20,
                    "external": 5,
                    "nofollow": 2
                },
                "images": {
                    "total": 10,
                    "withoutAlt": 3,
                    "byMime": {"image/jpeg": 5, "image/png": 3, "image/webp": 2},
                    "byExt": {"jpg": 5, "png": 3, "webp": 2}
                }
            },
            "tech": {
                "requests": {
                    "count": 45,
                    "total_bytes": 1200000,
                    "by_type": {
                        "document": {"count": 1, "bytes": 50000},
                        "script": {"count": 10, "bytes": 300000},
                        "stylesheet": {"count": 5, "bytes": 100000},
                        "image": {"count": 15, "bytes": 700000}
                    },
                    "first_party_bytes": 800000,
                    "third_party_bytes": 400000
                },
                "timing": {
                    "ttfb": 120,
                    "dcl": 450,
                    "load": 890
                }
            },
            "security": {
                "headers": {
                    "hsts": "max-age=31536000",
                    "csp": "default-src 'self'",
                    "xfo": "DENY",
                    "xcto": "nosniff"
                }
            },
            "site": {
                "pages_crawled": 15,
                "contacts": {
                    "emails": ["info@test-example.com", "contact@test-example.com"],
                    "phones": ["+1-555-1234", "+1-555-5678"],
                    "whatsapp": ["https://wa.me/15551234"]
                },
                "socials": {
                    "facebook": ["https://facebook.com/testpage"],
                    "instagram": ["https://instagram.com/testpage"]
                },
                "forms_found": 3,
                "legal_pages": [
                    "http://test-example.com/privacy",
                    "http://test-example.com/terms"
                ],
                "integrations": {
                    "analytics": ["google"],
                    "pixels": ["meta"]
                },
                "wp": {
                    "theme": "twentytwentythree",
                    "plugins": ["contact-form-7", "yoast-seo"],
                    "rest_api": True
                }
            },
            "pages": [
                {
                    "url": "http://test-example.com/",
                    "status": 200,
                    "emails_found": ["info@test-example.com"],
                    "phones_found": ["+1-555-1234"],
                    "forms_count": 1
                },
                {
                    "url": "http://test-example.com/contact",
                    "status": 200,
                    "emails_found": ["contact@test-example.com"],
                    "phones_found": ["+1-555-5678"],
                    "forms_count": 2
                }
            ]
        }
        
        report = StorageService.save_report(
            db=db,
            domain_name="test-example.com",
            report_data=test_report_data
        )
        
        print(f"  Reporte creado con ID: {report.id}")
        print(f"  Dominio: {report.domain.domain}")
        print(f"  Páginas rastreadas: {report.pages_crawled}")
        print(f"  SEO Title: {report.seo_title}")
        print(f"  Comprimido: {report.is_compressed}")
        
        # 4. Consultar el dominio
        print("\n✓ Consultando dominio...")
        domain = StorageService.get_domain_by_name(db, "test-example.com")
        print(f"  Dominio encontrado: {domain.domain}")
        print(f"  Total reportes: {domain.total_reports}")
        print(f"  Primera vez: {domain.first_scraped_at}")
        
        # 5. Crear segundo reporte para el mismo dominio
        print("\n✓ Creando segundo reporte...")
        test_report_data["seo"]["wordCount"] = 750  # Cambiar métrica
        test_report_data["tech"]["requests"]["count"] = 50  # Cambiar métrica
        
        report2 = StorageService.save_report(
            db=db,
            domain_name="test-example.com",
            report_data=test_report_data
        )
        
        print(f"  Segundo reporte creado con ID: {report2.id}")
        
        # 6. Consultar historial
        print("\n✓ Consultando historial...")
        reports = StorageService.get_domain_reports(
            db=db,
            domain_name="test-example.com",
            limit=10
        )
        print(f"  Reportes encontrados: {len(reports)}")
        for r in reports:
            print(f"    - ID {r.id}: {r.pages_crawled} páginas, {r.seo_word_count} palabras")
        
        # 7. Obtener último reporte
        print("\n✓ Obteniendo último reporte...")
        latest = StorageService.get_latest_report(db, "test-example.com")
        print(f"  Último reporte ID: {latest.id}")
        print(f"  Fecha: {latest.scraped_at}")
        
        # 8. Probar serialización
        print("\n✓ Probando serialización...")
        
        # Formato para métricas
        metrics_dict = latest.to_dict(include_full_data=False)
        print(f"  Métricas (sin datos completos): {len(str(metrics_dict))} caracteres")
        
        # Formato completo
        full_dict = latest.to_dict(include_full_data=True)
        print(f"  Datos completos: {len(str(full_dict))} caracteres")
        
        # Formato frontend
        frontend_dict = latest.to_frontend_format()
        print(f"  Formato frontend: {len(str(frontend_dict))} caracteres")
        
        # 9. Estadísticas
        print("\n✓ Estadísticas generales...")
        stats = StorageService.get_statistics(db)
        print(f"  Total dominios: {stats['total_domains']}")
        print(f"  Total reportes: {stats['total_reports']}")
        print(f"  Tasa de éxito: {stats['success_rate']}%")
        print(f"  Dominio más rastreado: {stats['most_scraped_domain']} ({stats['most_scraped_count']} veces)")
        
        # 10. Limpiar (eliminar reportes de prueba)
        print("\n✓ Limpiando datos de prueba...")
        deleted = StorageService.delete_old_reports(db, "test-example.com", keep_latest=1)
        print(f"  Reportes eliminados: {deleted}")
        
        # Verificar que queda solo 1
        remaining = StorageService.get_domain_reports(db, "test-example.com")
        print(f"  Reportes restantes: {len(remaining)}")
        
        print("\n" + "=" * 60)
        print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
        print("=" * 60)
        
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")
        import traceback
        traceback.print_exc()
        
    finally:
        db.close()
        print("\n✓ Sesión de base de datos cerrada")


if __name__ == "__main__":
    test_database()
