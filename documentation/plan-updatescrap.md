# Plan de actualización del scraper

## Objetivo
- **Motivación**: mejorar la calidad de la información para outreach comercial en frío.
- **Resultado esperado**: reportes enriquecidos que incluyan contactos confiables, señales de intención y contexto de negocio.

## Alcance
- **Cobertura**: dominios ya soportados por `scrap_domain.py`.
- **Exclusiones**: automatizaciones externas de envío de correos, scoring avanzado de leads.

## Entregables principales
- **Actualizaciones backend**: expansión de `site_summary`, `pages_data` y nuevos modelos si es necesario.
- **Captura de datos ampliada**: detección de perfiles, formularios, direcciones y CTAs.
- **Documentación**: guía de uso y checklist de QA.

## Fases y tareas
- **Fase 1 – Priorización de páginas**
  - Clasificar URLs según intención (About, Contact, Team, Pricing, Blog) dentro de `_crawl_site()`.
  - Etiquetar cada dato con la fuente y página de origen.
- **Fase 2 – Enriquecimiento de contactos**
  - Extraer nombres, cargos y enlaces sociales desde secciones de equipo y schema `Person`.
  - Normalizar teléfonos y correos, detectar propietarios (persona vs. genérico).
  - Extender `site_summary["contacts"]` con campos `team_contacts` y `contact_confidence`.
- **Fase 3 – Formularios y CTAs**
  - Guardar texto de botones, labels visibles y presencia de CAPTCHA.
  - Identificar integraciones (HubSpot, Typeform, Zoho) vía scripts y atributos.
  - Añadir `forms_detailed` y `cta_highlights` al reporte.
- **Fase 4 – Información de negocio**
  - Detectar direcciones físicas y geocodificarlas opcionalmente.
  - Extraer propuestas de valor, servicios clave, planes de precios y testimonios.
  - Resumir hallazgos en `site_summary["business"]` con campos `value_prop`, `pricing`, `testimonials`.
- **Fase 5 – Integraciones externas y QA**
  - Configurar hooks opcionales a APIs (Hunter, Clearbit, LinkedIn) y documentar uso de llaves.
  - Diseñar pruebas en `tests/integration/test_comments.py` y nuevas suites específicas para scraper.
  - Documentar procedimiento de verificación manual.

## Cambios técnicos previstos
- **Refactor de `_crawl_site()`** para usar colas por prioridad y límite por tipo de página.
- **Nuevos helpers** en `app/services/scrap_domain.py` para parsing de schema.org, detección de direcciones y CTAs.
- **Migraciones** potenciales para ampliar modelos `Report` y `TrustedContact` si se almacenan datos adicionales.

## Datos a capturar
- **Contactos personales**: nombres, cargos, correos, LinkedIn.
- **Ubicaciones**: direcciones postales, coordenadas estimadas.
- **Formularios**: método, acción, campos, integraciones, captcha, copy del botón.
- **Señales comerciales**: pricing tiers, testimonios, servicios destacados, últimas publicaciones.

## Métricas y seguimiento
- **Cobertura de contactos**: porcentaje de dominios con al menos un contacto nominal.
- **Calidad**: ratio de correos válidos vs. totales detectados.
- **Latencia**: tiempo medio por dominio antes y después de las mejoras.
- **Adopción**: número de reportes que consumen los nuevos campos en `report_detail.html`.

## Riesgos y mitigaciones
- **Tiempo de scraping**: priorizar páginas y establecer límites finos de `max_pages`.
- **Bloqueos**: rotar user-agents y considerar backoff entre requests.
- **Falsos positivos**: implementar validaciones y revisión manual de muestras.
- **Dependencia de APIs externas**: encapsular integraciones y manejar cuotas/errores.

## Próximos pasos inmediatos
- **Definir backlog detallado** para cada fase con issues y estimaciones.
- **Actualizar UI** en `templates/pages/report_detail.html` y `static/js/pages/report_detail.js` para mostrar los nuevos campos.
- **Programar demo interna** tras finalizar Fase 3 para feedback temprano.
