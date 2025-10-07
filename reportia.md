# Plan de implementación de Reportes IA

## Backend
- **[Servicios de generación]** Crear `app/services/report_generation_service.py` para orquestar llamados a LMStudio (`http://100.111.140.81:1234`) usando cliente OpenAI-compatible, armar prompts según tipo (técnico/comercial/entregable), formatear respuesta en Markdown y manejar errores/reintentos.
- **[Endpoints de generación]** Añadir rutas (por ejemplo en `app/routes/reports.py`) `POST /api/reports/{report_id}/generate` que reciban `{ "type": "technical" | "commercial" | "deliverable" }`, validen existencia del reporte base y devuelvan Markdown generado.
- **[Persistencia de prompts]** Definir modelo `ReportPrompt` (tabla con columnas `type`, `prompt_template`, `updated_at`, `updated_by`) y rutas `GET/PUT /api/settings/prompts` para leer/guardar los textos. Incluir migración y seeding de prompts por defecto.
- **[Auditoría y cache]** Opcional: guardar historial de generaciones (`ReportGenerationLog`) con metadatos (tipo, duración, tokens, errores) y almacenar última versión del Markdown para reutilizarla.

## Frontend
- **[Integración en report_detail]** Extender `static/js/pages/report_detail.js` para escuchar clics en los botones IA, enviar la petición al endpoint de generación, mostrar loading y renderizar el Markdown en `#report-ia-container` (usar librería como `marked.js` o `markdown-it`).
- **[Manejo de estado]** Añadir feedback visual (spinners, manejo de errores, reintentos) y permitir descargar/copiar el Markdown generado.
- **[Configuraciones]** Crear nueva pantalla o modal (p.ej. `templates/pages/settings.html` + `static/js/pages/settings.js`) accesible desde la UI, con formulario para editar los prompts por tipo, validación básica y vista previa opcional.

## Infraestructura y configuración
- **[Variables de entorno]** Registrar en configuración (`config.py` o `.env`) el endpoint de LMStudio y, si aplica, clave API. Documentar pasos de instalación y arranque.
- **[Dependencias]** Agregar cliente OpenAI (`openai` o `litellm`) o librería HTTP utilizada, y asegurar compatibilidad con entorno actual.

## Pruebas y QA
- **[Unit tests]** Mockear LMStudio para probar `report_generation_service` en escenarios de éxito, timeout y error.
- **[Integration tests]** Validar endpoints de generación y de prompts con la base de datos en memoria.
- **[Manual/UX]** Testear desde la UI los tres tipos de reporte, guardar cambios de prompts y verificar que se persisten.

## Seguimiento
- **[Tareas pendientes]** Priorizar backend de generación y endpoints, luego wiring frontend, y finalmente la pantalla de configuraciones.
- **[Monitoreo]** Registrar métricas básicas (tiempo de respuesta, errores) en logs para ajustar prompts y performance.
