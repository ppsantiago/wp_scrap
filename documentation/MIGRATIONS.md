# Estrategia de migraciones de base de datos

## Objetivos
- **[Versionado controlado]** Mantener un historial claro de cambios en el esquema mediante scripts versionados.
- **[Compatibilidad SQLite]** Asegurar que las migraciones se puedan ejecutar en entornos locales y Docker usando SQLite.
- **[Reproducibilidad]** Garantizar que cualquier colaborador pueda replicar el estado de la base de datos desde cero o actualizar un entorno existente.

## Herramientas y estructura
- **[Directorio de migraciones]** Los scripts viven en `app/migrations/`.
- **[Formato de archivos]** Se utilizan archivos `.sql` numerados incrementalmente (`0001_*.sql`, `0002_*.sql`, ...). Cada archivo es idempotente mediante `CREATE TABLE IF NOT EXISTS` (u otro mecanismo equivalente) cuando sea posible.
- **[Script inicial]** `app/migrations/0001_create_generated_reports.sql` crea la tabla `generated_reports`, índices y trigger `updated_at`.
- **[Alembic futuro]** El proyecto incluye `alembic` en `requirements.txt`; más adelante se evaluará generar scripts automáticamente (`alembic revision --autogenerate`) manteniendo los SQL planos para despliegues en SQLite.

## Flujo de trabajo recomendado
- **[1. Planificar]** Documentar el cambio de esquema requerido (nueva tabla, columna, índice o transformación de datos). Validar impacto en modelos de `app/models/`.
- **[2. Actualizar modelos]** Modificar primero los modelos SQLAlchemy asegurando coherencia con la migración.
- **[3. Crear script]** Añadir un archivo numerado en `app/migrations/` siguiendo convención snake_case descriptiva.
- **[4. Revisar/validar]** Ejecutar el script contra una copia local de la base (`sqlite3`) y verificar que los modelos siguen operando (p. ej. correr `pytest tests/unit` o pruebas específicas).
- **[5. Documentar]** Registrar el cambio en `reportia.md` (sección Seguimiento) y, si aplica, actualizar `documentation/MIGRATIONS.md` con notas adicionales.
- **[6. Aplicar en entornos]** Ejecutar el script en cada entorno (local, Docker, producción) siguiendo los comandos descritos abajo y confirmar estados.

## Comandos de aplicación
- **[Local simple]**
  ```bash
  sqlite3 data/wp_scrap.db < app/migrations/0001_create_generated_reports.sql
  ```
- **[Docker]**
  ```bash
  docker compose exec wp-scrap sqlite3 /app/data/wp_scrap.db < /app/migrations/0001_create_generated_reports.sql
  ```
- **[CI/CD]** Incluir un paso que ejecute todos los scripts en orden (`for file in app/migrations/*.sql; do ...`). Evitar aplicar migraciones en paralelo.

## Convenciones de numeración
- **[Incremental]** Usar tres dígitos (`000`, `001`, ...). Reservar números consecutivos sin huecos para evitar confusiones.
- **[Descripción]** El sufijo describe brevemente el cambio (`create_generated_reports`, `add_prompt_metadata_column`, etc.).
- **[Orden determinista]** El prefijo garantiza el orden de ejecución; scripts posteriores pueden depender de anteriores.

## Rollback y recuperación
- **[Backups previos]** Antes de aplicar migraciones en ambientes compartidos, generar backup (copiar `data/wp_scrap.db`).
- **[Scripts de reversión]** Para cambios críticos, crear un script complementario (`0001_down.sql`) o documentar pasos de rollback manual.
- **[Tolerancia a fallos]** En caso de fallo parcial: restaurar backup, corregir el script y volver a ejecutar.

## Migraciones de datos
- **[Transformaciones]** Incluir `UPDATE`/`INSERT` en el mismo script si la modificación del esquema lo requiere. Documentar supuestos para evitar inconsistencias.
- **[Bloqueos]** Para operaciones pesadas, considerar dividir en batches o programar mantenimiento para evitar bloqueos prolongados en SQLite.

## Coordinación con modelos y servicios
- **[Modelos]** Asegurar que `app/models/` refleje el nuevo esquema antes de despliegue para evitar errores al mapear columnas.
- **[Servicios]** Actualizar servicios (`app/services/`) y rutas (`app/routes/`) que consuman el nuevo esquema, agregando validaciones o migrando datos existentes.

## Línea base inicial
- **[Run base]** Al configurar un entorno nuevo: ejecutar `app/database.py:init_db()` (si se requiere) y luego todos los scripts en orden ascendente.
- **[Verificación]** Después de aplicar la migración base, correr `pytest tests/unit/test_database.py` o pruebas relevantes para confirmar integridad.

## Roadmap futuro (Alembic)
- **[Inicializar entorno]** `alembic init alembic` (directorio aún no versionado).
- **[Configurar target_metadata]** Apuntar a `app.database.Base.metadata` para permitir autogeneración.
- **[Generar scripts]** `alembic revision --autogenerate -m "mensaje"` y convertir la salida en SQL plano compatible con SQLite si se desea mantener ambos flujos (alembic + scripts).
- **[Sincronización]** Mantener correspondencia entre revisiones Alembic y archivos `.sql` para que los despliegues sigan un único historial coherente.

