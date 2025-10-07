# WP Scrap - Domain Analyzer

## Descripcion general
WP Scrap es una herramienta FastAPI para auditar dominios WordPress y sitios generales. Usa Playwright para cargar paginas reales, extrae senales SEO y tecnicas, mide peticiones de red y recopila datos de contacto. Los resultados quedan almacenados en SQLite para poder revisarlos desde un panel web, compararlos historicamente y agregar comentarios.

## Principales funcionalidades
- **Scraping integral**: inspeccion de metadatos, cabeceras, links, imagenes, rendimiento y cabeceras de seguridad con Playwright (`app/services/scrap_domain.py`).
- **Persistencia estructurada**: dominios y reportes se normalizan con SQLAlchemy y se guardan en SQLite (`app/models/domain.py`, `app/services/storage_service.py`).
- **UI administrativa**: paneles Jinja + JS para dashboard, listado de dominios, detalle de reportes y formulario de scraping (`templates/pages/*`, `static/js/pages/*`).
- **Sistema de comentarios**: hilos para dominios, reportes y jobs disponibles via `/api/comments/*` y componentes reutilizables en el frontend (`static/js/components/comments.js`).
- **Jobs en lote**: ejecucion asincrona de scraping masivo con seguimiento de pasos, reintentos y panel dedicado (`app/services/job_service.py`, `templates/pages/jobs.html`).

## Arquitectura de carpetas
```
app/
  main.py            # FastAPI + montado de rutas y estaticos
  routes/            # API y paginas (web, tools, reports, comments, jobs)
  services/          # Scraper, almacenamiento, comentarios, jobs
  models/            # ORM de dominios, reportes, comentarios y jobs
static/
  js/                # Utilidades, controladores de paginas y componentes UI
  style.css          # Estilos principales
templates/pages/     # Vistas HTML para dashboard, dominios, reportes, jobs, scrap
```

## Requisitos previos
- Python 3.10+
- Google Chromium instalable por Playwright
- (Opcional) Docker y Docker Compose

## Instalacion rapida en local
```bash
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
pip install playwright==1.48.0
playwright install chromium

# Ejecutar API con autoreload
uvicorn app.main:app --reload
```

La base de datos se crea por defecto en la ruta indicada por `DB_DIR` (valor predeterminado `/app/data/wp_scrap.db`). Puedes sobrescribirla exportando `DB_DIR` antes de iniciar el servidor.

## Ejecucion con Docker
```bash
docker compose up --build
```
El compose monta `./data` para persistir la base de datos y expone la aplicacion en `http://localhost:8000`. Revisa `DATABASE.md` para detalles de volumenes y backups.

## Como usar la herramienta
1. Abre `http://localhost:8000` para ver el dashboard con estadisticas agregadas y ultimos comentarios.
2. Usa `/scrap` para analizar un dominio puntual; el resultado se muestra en modal y se guarda si `save_to_db=true`.
3. Consulta `/domains` para filtrar dominios, ver historial y abrir comentarios especificos.
4. Revisa `/report/{id}` para inspeccionar un reporte con todos los bloques SEO, tecnico, seguridad y muestra de paginas.
5. Gestiona scraping masivo desde `/jobs`: crea un lote, sigue el progreso paso a paso y anota hallazgos en la pestana de comentarios.

## Endpoints clave
| Metodo | Ruta | Funcion |
| ------ | ---- | ------- |
| GET | `/check-domain` | Ejecuta scraping inmediato desde la UI o integraciones (`app/routes/tools.py`). |
| GET | `/reports/domains` | Lista dominios persistidos, admite paginacion (`app/routes/reports.py`). |
| GET | `/reports/domain/{domain}/latest` | Devuelve el ultimo reporte en formato frontend. |
| GET | `/reports/report/{id}` | Obtiene un reporte en modo `full`, `frontend` o `metrics`. |
| GET | `/reports/statistics` | Resumen global de dominios y reportes (`static/js/pages/dashboard.js`). |
| POST | `/api/comments` | Crea comentarios para dominios o reportes (`app/routes/comments.py`). |
| GET | `/api/comments/recent` | Lista comentarios recientes filtrables por tipo. |
| POST | `/api/jobs/batch-scraping` | Crea un job en lote y lo lanza en background (`app/routes/jobs.py`). |
| GET | `/api/jobs/{job_id}` | Estado y progreso de un job, con pasos incluidos. |

## Jobs en segundo plano
- Cada dominio del lote se procesa con reintentos configurables (`max_retries` en `job.config`).
- Los pasos registran bytes, errores o IDs de reporte generados.
- El listado de jobs refresca datos cada pocos segundos y permite cancelar ejecuciones en curso.

Funciones adicionales como reintentos manuales, borrado, progreso resumido y logs estan disponibles via `/api/jobs/{id}/retry`, `DELETE /api/jobs/{id}`, `/api/jobs/{id}/progress` y `/api/jobs/{id}/logs`, alineadas con los helpers en `static/js/utils/api.js`.

## Datos y reportes
- Los reportes guardan un resumen cacheado (palabras, enlaces, solicitudes) y el JSON completo comprimido cuando es grande.
- `DATABASE.md` documenta comandos utiles para inspeccionar `wp_scrap.db` y mantener los historicos.

## Pruebas rapidas
```bash
# Validar integracion con la base de datos
python test_database.py

# Revisar generacion de comentarios
python test_comments.py
```

## Documentacion complementaria
- `DATABASE.md`: montaje de volumenes, mantenimiento y ejemplos de queries.
- `FRONTEND.md`: detalle de paginas, componentes y ux.
- `JOBS.md`: flujo completo de jobs y casos de uso.

## Limitaciones conocidas
- Algunas clases CSS contienen caracteres fuera de ASCII debido a codificacion previa; revisa `static/style.css` si necesitas normalizarlos.
- El helper JS expone metodos de jobs para `retry`, `delete`, `progress` y `logs`, pero la API aun no los ofrece, por lo que acciones masivas pueden fallar hasta completar esos endpoints.
- Para scraping estable via Playwright se recomienda ejecutar en entornos con dependencias de Chromium instaladas (ver documentacion de Playwright si se usa Linux headless).

