# WP Scrap - Domain Analyzer

## Descripcion general
WP Scrap es una herramienta FastAPI para auditar dominios WordPress y sitios generales. Usa Playwright para cargar paginas reales, extrae senales SEO y tecnicas, mide peticiones de red y recopila datos de contacto. Los resultados quedan almacenados en SQLite para poder revisarlos desde un panel web, compararlos historicamente y agregar comentarios.

## Principales funcionalidades
- **Scraping integral**: inspeccion de metadatos, cabeceras, links, imagenes, rendimiento y cabeceras de seguridad con Playwright (`app/services/scrap_domain.py`).
- **Persistencia estructurada**: dominios y reportes se normalizan con SQLAlchemy y se guardan en SQLite (`app/models/domain.py`, `app/services/storage_service.py`).
- **Reportes enriquecidos**: recopilacion de contactos (emails, telefonos, WhatsApp), `team_contacts` con schema `Person`, formularios detallados, CTAs destacados e insights de negocio (`site.business`, `forms_detailed`, `cta_highlights`).
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
4. Revisa `/report/{id}` para inspeccionar un reporte con bloques SEO, tecnicos, de seguridad y ahora tambien contactos enriquecidos, formularios detectados, CTAs y resumen de negocio.
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

## Datos y reportes
- Los reportes guardan un resumen cacheado (palabras, enlaces, solicitudes) y el JSON completo comprimido cuando es grande. Las nuevas claves incluyen:
  - `site.contacts` con emails, telefonos, WhatsApp y buckets de confianza (`personal` / `generic`).
  - `site.team_contacts` con nombre, cargo, email, telefono y perfiles sociales.
  - `site.forms_detailed` con metadata de formularios (metodo, accion, campos, integracion, CAPTCHA) y `site.forms_found` como conteo.
  - `site.cta_highlights` con texto, URL y pagina de origen para CTAs visibles.
  - `site.business` con value proposition, pricing, servicios y testimonios detectados.
  - `pages[]` anotadas con `page_type`, `seed_type`, contactos encontrados y formularios por pagina.
- `DATABASE.md` documenta comandos utiles para inspeccionar `wp_scrap.db` y mantener los historicos.

## Notas sobre la UI
- `static/js/pages/report_detail.js` renderiza las secciones enriquecidas y tablas de CTAs, formularios y contactos de equipo.
- `static/style.css` incluye estilos para subsecciones (`.info-subsection`) y estados muted utilizados en el reporte detallado.
- Recuerda hacer hard-reload tras desplegar cambios estaticos para evitar cache del navegador.

## Pruebas rapidas
```bash
# Ejecutar suite completa localmente
pytest

# Solo pruebas unitarias
pytest -m unit
# Solo integracion
pytest -m integration

# En Docker (reutilizando servicio `wp-scrap`)
docker compose run --rm wp-scrap pytest -m "not e2e"

# TODO: documentar flujo Playwright completo para pruebas `pytest -m e2e`.

## Limitaciones conocidas
- Algunas clases CSS contienen caracteres fuera de ASCII debido a codificacion previa; revisa `static/style.css` si necesitas normalizarlos.
- El helper JS expone metodos de jobs para `retry`, `delete`, `progress` y `logs`, pero la API aun no los ofrece, por lo que acciones masivas pueden fallar hasta completar esos endpoints.
- Para scraping estable via Playwright se recomienda ejecutar en entornos con dependencias de Chromium instaladas (ver documentacion de Playwright si se usa Linux headless).
