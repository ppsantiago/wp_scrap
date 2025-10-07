# Plan de implementación de Reportes IA

## Backend
- **[Servicios de generación]** `app/services/report_generation_service.py` ahora incluye reintentos configurables (`settings.report_generation_max_retries`), orquestación, almacenamiento de Markdown (`GeneratedReport`) y reutiliza historial.
- **[Endpoints de generación]** `POST /api/reports/{report_id}/generate` implementado. Se añadieron `GET /api/reports/{report_id}/generated`, `GET /api/reports/{report_id}/generated/{type}` y `PUT /api/reports/{report_id}/generated` para listar, obtener y guardar salidas persistidas.
- **[Persistencia de prompts]** Modelo `ReportPrompt` y rutas de configuración siguen operativas; queda por migrar validadores a Pydantic v2 y preparar seeding definitivo.
- **[Persistencia de reportes IA]** `GeneratedReport` creado (serializa `tags` y `metadata`, relación con `Report`). Migración inicial lista en `app/migrations/0001_create_generated_reports.sql`; siguiente paso: aplicar script y evaluar comentarios sobre reportes generados.
- **[Auditoría y cache]** `ReportGenerationLog` continúa registrando ejecuciones; evaluar métricas adicionales y limpieza periódica.

## Frontend
- **[Integración en report_detail]** Extender `static/js/pages/report_detail.js` para escuchar clics en los botones IA, enviar la petición al endpoint de generación, mostrar loading y renderizar el Markdown en `#report-ia-container` (usar librería como `marked.js` o `markdown-it`).
- **[Manejo de estado]** Añadir feedback visual (spinners, manejo de errores, reintentos) y permitir descargar/copiar el Markdown generado.
- **[Configuraciones]** Crear nueva pantalla o modal (p.ej. `templates/pages/settings.html` + `static/js/pages/settings.js`) accesible desde la UI, con formulario para editar los prompts por tipo, validación básica y vista previa opcional.
- **[Previsualización Markdown]** Implementar componente de vista previa instantánea para el Markdown generado y los prompts editados (usar `marked.js`/`markdown-it`), mostrando loading/errores y permitiendo comentar versiones guardadas.

## Infraestructura y configuración
- **[Variables de entorno]** Registrar en configuración (`config.py` o `.env`) el endpoint de LMStudio y, si aplica, clave API. Documentar pasos de instalación y arranque.
- **[Dependencias]** Agregar cliente OpenAI (`openai` o `litellm`) o librería HTTP utilizada, y asegurar compatibilidad con entorno actual.
- **[Migraciones]** Estrategia documentada en `documentation/MIGRATIONS.md`; pendiente automatizar ejecución en CI/CD y revisar integración futura con Alembic.

## Pruebas y QA
- **[Unit tests]** Mockear LMStudio para probar `report_generation_service` en escenarios de éxito, timeout y error.
- **[Integration tests]** Validar endpoints de generación y de prompts con la base de datos en memoria.
- **[Manual/UX]** Testear desde la UI los tres tipos de reporte, guardar cambios de prompts y verificar que se persisten.

## Seguimiento
- **[Tareas completadas]** Reintentos configurables implementados en `app/services/report_generation_service.py`. Migración inicial creada en `app/migrations/0001_create_generated_reports.sql`.
- **[Tareas pendientes]** Exponer nuevas rutas en frontend, migrar validadores a Pydantic v2 y aplicar la migración en entornos existentes.
- **[Monitoreo]** Mantener métricas de generación y revisar advertencias (SQLAlchemy overlaps, Pydantic deprecations) antes del despliegue.
