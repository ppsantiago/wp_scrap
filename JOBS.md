# Sistema de Jobs en Lote

Sistema completo para ejecutar trabajos de scraping en lote sin bloquear la interfaz de usuario.

## 📋 Características

- ✅ **Ejecución asíncrona**: Los jobs corren en background sin bloquear la UI
- ✅ **Progreso en tiempo real**: Seguimiento del progreso paso a paso
- ✅ **Estados detallados**: pending, running, completed, failed, cancelled
- ✅ **Reintentos automáticos**: Configurable por job (default: 2 reintentos)
- ✅ **Comentarios**: Sistema de comentarios integrado para cada job
- ✅ **Auto-refresh**: Actualización automática del estado cada 3-5 segundos
- ✅ **Historial completo**: Cada paso guarda su resultado y posibles errores

## 🏗️ Arquitectura

### Modelos de Datos

#### Job
```python
- id: Identificador único
- job_type: Tipo de trabajo (batch_scraping, single_scraping, etc.)
- name: Nombre descriptivo
- status: Estado actual (pending, running, completed, failed, cancelled)
- config: Configuración JSON con parámetros
- total_steps: Total de pasos a ejecutar
- completed_steps: Pasos completados exitosamente
- failed_steps: Pasos fallidos
- created_at, started_at, completed_at: Timestamps
```

#### JobStep
```python
- id: Identificador único
- job_id: Referencia al job padre
- step_number: Número de orden
- name: Nombre del paso (ej: "Scraping: example.com")
- status: Estado del paso
- result_data: JSON con resultados (ej: report_id)
- error_message: Mensaje de error si falló
- started_at, completed_at: Timestamps
```

### Servicios

#### JobService (`app/services/job_service.py`)

**Métodos principales:**

- `create_batch_scraping_job(domains, name, description)`: Crea un job para múltiples dominios
- `execute_job(job_id)`: Ejecuta el job de forma asíncrona
- `start_job(job_id)`: Inicia el job en background
- `cancel_job(job_id)`: Cancela un job en ejecución
- `get_job_status(job_id)`: Obtiene el estado actual
- `list_jobs(filters)`: Lista jobs con filtros opcionales

**Proceso de ejecución:**

1. Se crea el job con estado `pending`
2. Se generan los pasos (uno por dominio)
3. `start_job()` crea una tarea asyncio en background
4. Cada paso se ejecuta secuencialmente:
   - Marca el paso como `running`
   - Ejecuta scraping con reintentos
   - Guarda resultado en BD
   - Marca como `completed` o `failed`
5. Al finalizar todos los pasos, marca el job como `completed`

## 🔌 API Endpoints

### Jobs

```
POST   /api/jobs/batch-scraping     - Crear y ejecutar job de scraping en lote
GET    /api/jobs                     - Listar jobs (con filtros)
GET    /api/jobs/{job_id}            - Obtener detalles de un job
POST   /api/jobs/{job_id}/cancel     - Cancelar un job
GET    /api/jobs/{job_id}/steps      - Obtener pasos de un job
GET    /api/jobs/stats/summary       - Estadísticas generales
```

### Comentarios en Jobs

```
GET    /api/comments/job/{job_id}    - Obtener comentarios de un job
POST   /api/comments/job             - Crear comentario en un job
```

### Páginas Web

```
GET    /jobs                         - Lista de jobs
GET    /job/{job_id}                 - Detalle de un job específico
```

## 💻 Uso desde Frontend

### JavaScript (JobManager)

```javascript
// Crear un job
const domains = ['example.com', 'test.com', 'another.com'];
const job = await JobManager.createBatchScrapingJob(
    domains,
    'Mi Job de Scraping',
    'Descripción opcional'
);

// Redirigir al detalle
window.location.href = `/job/${job.id}`;

// Obtener estado de un job
const jobDetails = await JobManager.getJob(jobId);

// Iniciar polling automático
JobManager.startJobPolling(jobId, (job) => {
    console.log(`Progreso: ${job.progress_percentage}%`);
    console.log(`Completados: ${job.completed_steps}/${job.total_steps}`);
    
    if (job.status === 'completed') {
        console.log('Job finalizado!');
    }
}, 3000); // Actualiza cada 3 segundos

// Cancelar job
await JobManager.cancelJob(jobId);
```

### Desde Python

```python
from app.services.job_service import JobService
from app.database import SessionLocal

db = SessionLocal()

# Crear job
job = JobService.create_batch_scraping_job(
    db=db,
    domains=['example.com', 'test.com'],
    name='Mi Job',
    created_by='admin'
)

# Iniciar en background
JobService.start_job(job.id)

# Obtener estado
status = JobService.get_job_status(db, job.id)
print(f"Progreso: {status['progress_percentage']}%")
```

## 🎨 Interfaz de Usuario

### Lista de Jobs (`/jobs`)

- Visualización tipo card de todos los jobs
- Filtros por estado y tipo
- Estadísticas en tiempo real (pendientes, en ejecución, completados, fallidos)
- Botón para crear nuevo job
- Auto-refresh cada 5 segundos si hay jobs corriendo
- Barra de progreso visual para cada job

### Detalle de Job (`/job/{job_id}`)

- Información completa del job
- Lista de todos los pasos con su estado
- Barra de progreso general
- Métricas: total, completados, fallidos, pendientes
- Sistema de comentarios integrado
- Configuración del job (JSON)
- Auto-refresh cada 3 segundos si está en ejecución
- Botón para cancelar (solo si está running/pending)
- Links directos a los reportes generados

**Tabs disponibles:**
1. **Pasos**: Lista detallada de cada paso con iconos de estado
2. **Comentarios**: Sistema completo de comentarios
3. **Configuración**: Vista JSON de la configuración

## 🚀 Instalación y Migración

### 1. Migrar la base de datos

```bash
python migrate_jobs.py
```

Esto creará las tablas `jobs` y `job_steps` en la base de datos.

### 2. Verificar la instalación

```bash
# Iniciar el servidor
uvicorn app.main:app --reload

# Acceder a:
# - http://localhost:8000/jobs (lista de jobs)
# - http://localhost:8000/docs (documentación API)
```

## 📝 Ejemplo de Uso Completo

### 1. Crear un Job desde la UI

1. Ir a `/jobs`
2. Click en "Nuevo Job"
3. Ingresar nombre y descripción (opcional)
4. Pegar lista de dominios (uno por línea)
5. Click en "Crear e Iniciar Job"
6. Serás redirigido al detalle del job

### 2. Ver el progreso

La página de detalle se actualiza automáticamente cada 3 segundos mostrando:
- Progreso general (%)
- Estado de cada dominio (pending, running, completed, failed)
- Links a los reportes generados
- Errores específicos si alguno falló

### 3. Agregar comentarios

En el tab "Comentarios" puedes agregar notas sobre el job:
- Observaciones
- Decisiones tomadas
- Próximos pasos
- etc.

## 🔧 Configuración

### Reintentos

Por defecto, cada dominio se reintenta 2 veces si falla. Puedes modificar esto en la configuración del job:

```python
job = JobService.create_batch_scraping_job(
    db=db,
    domains=domains,
    name='Mi Job'
)

# Modificar configuración antes de iniciar
job.config['max_retries'] = 3  # 3 reintentos
db.commit()

JobService.start_job(job.id)
```

### Intervalo entre dominios

Por defecto hay una pausa de 1 segundo entre cada dominio. Puedes modificar esto en `job_service.py`:

```python
# En _execute_batch_scraping()
await asyncio.sleep(1)  # Cambiar según necesites
```

## 🐛 Debugging

### Ver logs del servidor

```bash
# Los logs mostrarán:
# - Inicio y fin de cada job
# - Cada paso ejecutado
# - Errores detallados
```

### Verificar estado en base de datos

```sql
-- Ver todos los jobs
SELECT id, name, status, progress_percentage, total_steps, completed_steps, failed_steps 
FROM jobs 
ORDER BY created_at DESC;

-- Ver pasos de un job específico
SELECT step_number, name, status, error_message 
FROM job_steps 
WHERE job_id = 1 
ORDER BY step_number;
```

## 🎯 Casos de Uso

### 1. Analizar cartera de clientes
```
Crear job con 50 dominios de clientes
→ Ejecuta en background sin bloquear
→ Recibes notificación al completar
→ Revisas reportes generados
```

### 2. Monitoreo periódico
```
Crear job programado (futuro: cron)
→ Re-escanea dominios importantes
→ Compara con reportes anteriores
→ Detecta cambios
```

### 3. Auditoría de portfolio
```
Exportar lista de dominios
→ Crear job masivo
→ Analizar resultados
→ Generar reporte consolidado
```

## 🔮 Futuras Mejoras

- [ ] Priorización de jobs (campo priority ya existe)
- [ ] Programación de jobs (cron jobs)
- [ ] Notificaciones (email, webhook) al completar
- [ ] Exportación de resultados (CSV, Excel, PDF)
- [ ] Jobs de comparación entre reportes
- [ ] Limitar jobs concurrentes
- [ ] Dashboard de métricas de jobs
- [ ] Webhook al completar cada paso
- [ ] API para integración externa

## 📚 Referencias

- **Modelos**: `app/models/job.py`
- **Servicio**: `app/services/job_service.py`
- **API Routes**: `app/routes/jobs.py`
- **Web Routes**: `app/routes/web.py`
- **Templates**: `templates/pages/jobs.html`, `templates/pages/job_detail.html`
- **JavaScript**: `static/js/components/jobManager.js`
