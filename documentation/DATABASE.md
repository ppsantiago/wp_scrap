# Base de Datos - Documentación

## 📋 Visión General

El sistema incluye persistencia de datos usando **SQLite + SQLAlchemy**. Los reportes de scraping se guardan automáticamente en la base de datos para análisis histórico y comparaciones.

## 🐳 Configuración Docker con Volúmenes

### Montaje de Volúmenes

La aplicación está configurada para usar volúmenes Docker que permiten:

- **Persistencia**: La base de datos sobrevive reinicios del contenedor
- **Desarrollo**: Cambios en el código se reflejan inmediatamente
- **Separación**: Código fuente separado de datos

### Configuración Actual

**docker-compose.yaml:**
```yaml
services:
  wp-scrap:
    image: scrap20-wp-scrap
    build: .
    ports:
      - "8000:8000"
    environment:
      - DB_DIR=/app/data  # Ruta donde se guarda la DB dentro del contenedor
    volumes:
      - ./data:/app/data  # Monta directorio local ./data al contenedor /app/data
      - ./app:/app        # Monta código fuente para desarrollo
      - ./templates:/app/templates
      - ./static:/app/static
    restart: unless-stopped
```

### Ubicación de la Base de Datos

- **Dentro del contenedor**: `/app/data/wp_scrap.db`
- **En el host (tu máquina)**: `./data/wp_scrap.db`
- **Configurable**: Puedes cambiar `DB_DIR` con variable de entorno

### Cómo Funciona

1. **Al iniciar**: Docker crea el directorio `./data/` en tu máquina si no existe
2. **Base de datos**: Se crea en `./data/wp_scrap.db` cuando la aplicación inicia
3. **Persistencia**: Los datos sobreviven aunque el contenedor se detenga/reinicie
4. **Hot reload**: Cambios en el código fuente se reflejan inmediatamente

### Comandos Útiles

```bash
# Iniciar aplicación con Docker
docker compose up

# Ver logs
docker compose logs -f wp-scrap

# Detener aplicación
docker compose down

# Limpiar contenedores (manteniendo datos)
docker compose down

# Limpiar todo incluyendo volúmenes (⚠️ borra datos)
docker compose down -v

# Construir nueva imagen
docker compose build

# Ver estado de contenedores
docker compose ps
```

### Inspeccionar Base de Datos

```bash
# Conectar a la base de datos desde el contenedor
docker compose exec wp-scrap sqlite3 /app/data/wp_scrap.db

# Desde tu máquina (si tienes sqlite3 instalado)
sqlite3 data/wp_scrap.db

# Ejemplos de consultas:
.tables
.schema domains
.schema reports
SELECT domain, total_reports FROM domains ORDER BY last_scraped_at DESC;
```

### Desarrollo Local vs Docker

**Para desarrollo local** (sin Docker):
- La base de datos se crea en `./wp_scrap.db` (junto al código)
- Usa `python test_database.py` para probar

**Para desarrollo con Docker**:
- La base de datos se crea en `./data/wp_scrap.db`
- Usa `docker compose up` para iniciar

### Backup y Restauración

```bash
# Backup
cp data/wp_scrap.db data/backup_$(date +%Y%m%d_%H%M%S).db

# Restaurar
cp data/backup_20231201_120000.db data/wp_scrap.db

# Backup desde contenedor
docker compose exec wp-scrap cp /app/data/wp_scrap.db /tmp/backup.db
docker compose cp wp-scrap:/tmp/backup.db ./data/
```

### Troubleshooting Docker

**Problema: "Base de datos bloqueada"**
```bash
# Aumentar timeout en app/database.py
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"timeout": 60}  # Aumentar si es necesario
)
```

**Problema: "No se puede escribir en directorio"**
```bash
# Verificar permisos
ls -la data/

# Crear directorio con permisos correctos
sudo mkdir -p data
sudo chmod 755 data
```

**Problema: "Archivo de base de datos no encontrado"**
```bash
# Crear directorio manualmente
mkdir -p data

# Reiniciar contenedor
docker compose down
docker compose up
```

## 📝 Sistema de Comentarios

### Modelo de Comentarios

El sistema incluye un modelo independiente de comentarios que puede asociarse a diferentes entidades (dominios, reportes, etc.) y soporta hilos de conversación.

### Tabla: `comments`

| Campo | Tipo | Descripción |
|-------|------|-------------|
| `id` | INTEGER | ID único (Primary Key) |
| `content_type` | VARCHAR(50) | Tipo de entidad ('domain', 'report', etc.) |
| `object_id` | INTEGER | ID de la entidad comentada |
| `parent_id` | INTEGER | ID del comentario padre (para respuestas) |
| `author` | VARCHAR(255) | Autor del comentario (texto por ahora) |
| `content` | TEXT | Contenido del comentario |
| `created_at` | DATETIME | Fecha de creación |
| `updated_at` | DATETIME | Fecha de última actualización |
| `is_active` | BOOLEAN | Si el comentario está activo |
| `is_pinned` | BOOLEAN | Si el comentario está destacado |

### Características del Sistema de Comentarios

#### ✅ Comentarios Independientes
- Asociados a cualquier entidad mediante `content_type` y `object_id`
- Soporte para futuras entidades sin cambios en el esquema

#### ✅ Hilos de Conversación
- Comentarios raíz (sin padre)
- Respuestas anidadas mediante `parent_id`
- Profundidad ilimitada (aunque se recomienda máximo 5 niveles)

#### ✅ Gestión de Estado
- Comentarios activos/inactivos (borrado lógico)
- Comentarios destacados (pinned)
- Auditoría completa (created_at, updated_at)

#### ✅ Consultas Avanzadas
- Comentarios por entidad específica
- Comentarios por autor
- Comentarios recientes
- Búsqueda de texto
- Estadísticas generales

### API de Comentarios

#### Crear Comentario
```bash
POST /comments
Content-Type: application/json

{
  "content_type": "domain",
  "object_id": 1,
  "author": "usuario_ejemplo",
  "content": "Este dominio tiene excelente SEO",
  "parent_id": null
}
```

#### Obtener Comentarios de una Entidad
```bash
GET /comments/entity/domain/1
# Comentarios del dominio con ID 1

GET /comments/entity/report/5
# Comentarios del reporte con ID 5
```

#### Crear Respuesta
```bash
POST /comments
Content-Type: application/json

{
  "content_type": "domain",
  "object_id": 1,
  "author": "otro_usuario",
  "content": "Estoy de acuerdo contigo",
  "parent_id": 123  # ID del comentario padre
}
```

#### Obtener Hilo Completo
```bash
GET /comments/thread/123
# Obtiene el comentario 123 y todas sus respuestas
```

#### Buscar Comentarios
```bash
GET /comments/search?q=excelente&content_type=domain
# Busca comentarios que contengan "excelente" en dominios
```

#### Estadísticas
```bash
GET /comments/statistics
# Estadísticas generales de comentarios

GET /comments/statistics?content_type=domain
# Estadísticas solo de comentarios en dominios
```

### Uso en Aplicación

#### Comentarios en Dominios
```python
from app.services.comment_service import CommentService

# Crear comentario en dominio
comment = CommentService.create_comment(
    db=db,
    content_type="domain",
    object_id=domain.id,
    author="usuario1",
    content="Comentario sobre el dominio"
)

# Obtener comentarios del dominio
comments = CommentService.get_comments_for_entity(
    db=db,
    content_type="domain",
    object_id=domain.id,
    include_replies=True
)
```

#### Comentarios en Reportes
```python
# Crear comentario en reporte
comment = CommentService.create_comment(
    db=db,
    content_type="report",
    object_id=report.id,
    author="usuario2",
    content="Comentario sobre el reporte"
)

# Obtener comentarios del reporte
comments = CommentService.get_comments_for_entity(
    db=db,
    content_type="report",
    object_id=report.id,
    include_replies=True
)
```

### Rutas Especializadas

#### Dominio con Comentarios
```bash
GET /reports/domain/example.com/with-comments
# Información completa del dominio + comentarios
```

#### Reporte con Comentarios
```bash
GET /reports/report/123/with-comments?format=frontend
# Reporte específico + comentarios asociados
```

#### Dominios con Comentarios Recientes
```bash
GET /reports/domains/with-recent-comments?limit=10
# Lista de dominios que tienen comentarios recientes
```

### Frontend Integration

Los comentarios están diseñados para integrarse fácilmente con el frontend existente:

```javascript
// Ejemplo de integración en el componente de dominio
const domainData = await fetch(`/reports/domain/${domain}/with-comments`);
const { comments, recent_reports, ...domainInfo } = await domainData.json();

// Renderizar comentarios
comments.forEach(comment => {
    renderComment(comment);
    comment.replies?.forEach(reply => renderReply(reply));
});
```

### Seguridad y Moderación

- **Borrado lógico**: Los comentarios se marcan como inactivos en lugar de eliminarse
- **Auditoría**: Todas las acciones quedan registradas con timestamps
- **Filtrado**: Los comentarios inactivos se excluyen por defecto de las consultas
- **Moderación futura**: Preparado para implementar roles de moderadores

### Rendimiento

- **Índices optimizados**: Consultas rápidas por entidad, autor y fecha
- **Carga lazy**: Las respuestas se cargan solo cuando se solicitan
- **Paginación**: Soporte para grandes cantidades de comentarios
- **Cache friendly**: Estructura diseñada para cachear resultados

### 4. **Dependency Injection**
FastAPI maneja automáticamente las sesiones de base de datos usando `Depends(get_db)`.

## 📡 API Endpoints

### Scraping y Guardado

#### `GET /check-domain`
Realiza scraping y guarda el reporte.

```bash
# Scraping con guardado automático
curl "http://localhost:8000/check-domain?domain=example.com"

# Scraping sin guardar
curl "http://localhost:8000/check-domain?domain=example.com&save_to_db=false"
```

**Respuesta incluye:**
```json
{
  "domain": "http://example.com",
  "status_code": 200,
  "success": true,
  "seo": {...},
  "tech": {...},
  "security": {...},
  "site": {...},
  "pages": [...],
  "report_id": 123,
  "saved_to_db": true
}
```

### Consultar Dominios

#### `GET /reports/domains`
Lista todos los dominios rastreados.

```bash
curl "http://localhost:8000/reports/domains?limit=50&offset=0"
```

#### `GET /reports/domain/{domain_name}`
Info de un dominio específico.

```bash
curl "http://localhost:8000/reports/domain/example.com"
```

### Historial de Reportes

#### `GET /reports/domain/{domain_name}/history`
Historial completo de un dominio.

```bash
# Solo métricas (rápido)
curl "http://localhost:8000/reports/domain/example.com/history?limit=20"

# Con datos completos
curl "http://localhost:8000/reports/domain/example.com/history?include_data=true"

# Solo reportes exitosos
curl "http://localhost:8000/reports/domain/example.com/history?success_only=true"
```

#### `GET /reports/domain/{domain_name}/latest`
Último reporte de un dominio (formato frontend).

```bash
curl "http://localhost:8000/reports/domain/example.com/latest"
```

### Reportes Individuales

#### `GET /reports/report/{report_id}`
Obtiene un reporte específico.

```bash
# Formato completo
curl "http://localhost:8000/reports/report/123?format=full"

# Formato frontend (compatible con UI)
curl "http://localhost:8000/reports/report/123?format=frontend"

# Solo métricas
curl "http://localhost:8000/reports/report/123?format=metrics"
```

### Reportes Recientes

#### `GET /reports/recent`
Reportes recientes de todos los dominios.

```bash
curl "http://localhost:8000/reports/recent?days=7&limit=50"
```

### Comparación

#### `GET /reports/compare/{domain_name}`
Compara métricas entre reportes.

```bash
curl "http://localhost:8000/reports/compare/example.com?report_ids=1,5,10&metrics=seo_word_count,tech_requests_count"
```

**Respuesta:**
```json
{
  "domain": "example.com",
  "reports_compared": 3,
  "metrics": ["seo_word_count", "tech_requests_count"],
  "comparison": [
    {
      "report_id": 1,
      "scraped_at": "2025-10-01T10:00:00",
      "metrics": {
        "seo_word_count": 1500,
        "tech_requests_count": 45
      }
    },
    ...
  ]
}
```

### Limpieza

#### `DELETE /reports/domain/{domain_name}/cleanup`
Elimina reportes antiguos.

```bash
# Mantener solo los últimos 10 reportes
curl -X DELETE "http://localhost:8000/reports/domain/example.com/cleanup?keep_latest=10"
```

### Estadísticas

#### `GET /reports/statistics`
Estadísticas generales del sistema.

```bash
curl "http://localhost:8000/reports/statistics"
```

**Respuesta:**
```json
{
  "total_domains": 42,
  "total_reports": 385,
  "successful_reports": 370,
  "failed_reports": 15,
  "success_rate": 96.1,
  "most_scraped_domain": "example.com",
  "most_scraped_count": 25
}
```

## 🚀 Uso desde Python

### Guardar un reporte manualmente

```python
from app.database import SessionLocal
from app.services.storage_service import StorageService

db = SessionLocal()

report_data = {
    "domain": "example.com",
    "status_code": 200,
    "success": True,
    "seo": {...},
    "tech": {...},
    # ... más datos
}

report = StorageService.save_report(
    db=db,
    domain_name="example.com",
    report_data=report_data
)

print(f"Reporte guardado con ID: {report.id}")
db.close()
```

### Consultar historial

```python
from app.database import SessionLocal
from app.services.storage_service import StorageService

db = SessionLocal()

# Obtener últimos 10 reportes
reports = StorageService.get_domain_reports(
    db=db,
    domain_name="example.com",
    limit=10,
    success_only=True
)

for report in reports:
    print(f"ID: {report.id}, Fecha: {report.scraped_at}, Páginas: {report.pages_crawled}")

db.close()
```

## 🔧 Mantenimiento

### Ubicación de la base de datos
El archivo SQLite se crea en:
```
wp_scrap/wp_scrap.db
```

### Respaldo
```bash
# Copiar la base de datos
cp wp_scrap.db wp_scrap_backup_$(date +%Y%m%d).db
```

### Inspeccionar con SQLite CLI
```bash
sqlite3 wp_scrap.db

# Ver tablas
.tables

# Ver estructura
.schema domains
.schema reports

# Consultas
SELECT domain, total_reports, last_scraped_at FROM domains ORDER BY last_scraped_at DESC LIMIT 10;

SELECT id, scraped_at, pages_crawled, seo_word_count FROM reports WHERE success = 1 ORDER BY scraped_at DESC LIMIT 20;
```

### Optimización
```python
# Limpiar reportes antiguos de todos los dominios
from app.database import SessionLocal
from app.services.storage_service import StorageService

db = SessionLocal()
domains = StorageService.get_all_domains(db)

for domain in domains:
    deleted = StorageService.delete_old_reports(db, domain.domain, keep_latest=10)
    print(f"{domain.domain}: {deleted} reportes eliminados")

db.close()
```

## 📝 Migraciones (Futuro)

Para cambios en el esquema, usar Alembic:

```bash
# Inicializar Alembic
alembic init alembic

# Crear migración
alembic revision --autogenerate -m "Descripción del cambio"

# Aplicar migración
alembic upgrade head
```

## 🐛 Troubleshooting

### Error: "database is locked"
SQLite puede tener problemas con concurrencia. Aumentar el timeout:
```python
# En app/database.py
engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    connect_args={"timeout": 30}  # Aumentar si es necesario
)
```

### Reporte muy grande
Los reportes grandes se comprimen automáticamente. Si siguen siendo muy grandes:
1. Reducir `max_pages` en `scrap_domain()`
2. Implementar paginación en `pages_data`

### Regenerar base de datos
```bash
# Eliminar base de datos existente
rm wp_scrap.db

# Reiniciar la aplicación (creará tablas nuevas)
python -m uvicorn app.main:app --reload
```
