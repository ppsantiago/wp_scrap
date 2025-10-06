/**
 * Job Manager Component
 * Maneja la creación y ejecución de jobs de scraping en lote
 */

class JobManager {
    constructor() {
        this.jobs = [];
        this.currentJob = null;
        this.refreshInterval = null;
    }

    /**
     * Crea un nuevo job de scraping en lote
     */
    async createBatchScrapingJob(domains, name = null, description = null, createdBy = 'user') {
        try {
            const response = await fetch('/api/jobs/batch-scraping', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    domains,
                    name,
                    description,
                    created_by: createdBy
                })
            });

            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.detail || 'Error creando job');
            }

            if (data.success) {
                return data.job;
            } else {
                throw new Error(data.message || 'Error creando job');
            }
        } catch (error) {
            console.error('Error creando job:', error);
            throw error;
        }
    }

    /**
     * Lista jobs con filtros opcionales
     */
    async listJobs(filters = {}) {
        try {
            const params = new URLSearchParams();
            
            if (filters.status) params.append('status', filters.status);
            if (filters.job_type) params.append('job_type', filters.job_type);
            if (filters.limit) params.append('limit', filters.limit);
            if (filters.offset) params.append('offset', filters.offset);

            const response = await fetch(`/api/jobs?${params}`);
            const data = await response.json();

            if (data.success) {
                this.jobs = data.jobs;
                return data.jobs;
            } else {
                throw new Error('Error listando jobs');
            }
        } catch (error) {
            console.error('Error listando jobs:', error);
            throw error;
        }
    }

    /**
     * Obtiene detalles de un job específico
     */
    async getJob(jobId, includeSteps = true) {
        try {
            const params = new URLSearchParams({ include_steps: includeSteps });
            const response = await fetch(`/api/jobs/${jobId}?${params}`);
            const data = await response.json();

            if (data.success) {
                this.currentJob = data.job;
                return data.job;
            } else {
                throw new Error('Error obteniendo job');
            }
        } catch (error) {
            console.error('Error obteniendo job:', error);
            throw error;
        }
    }

    /**
     * Cancela un job en ejecución
     */
    async cancelJob(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}/cancel`, {
                method: 'POST'
            });
            const data = await response.json();

            if (data.success) {
                return true;
            } else {
                throw new Error('Error cancelando job');
            }
        } catch (error) {
            console.error('Error cancelando job:', error);
            throw error;
        }
    }

    /**
     * Obtiene los pasos de un job
     */
    async getJobSteps(jobId) {
        try {
            const response = await fetch(`/api/jobs/${jobId}/steps`);
            const data = await response.json();

            if (data.success) {
                return data.steps;
            } else {
                throw new Error('Error obteniendo pasos del job');
            }
        } catch (error) {
            console.error('Error obteniendo pasos:', error);
            throw error;
        }
    }

    /**
     * Obtiene estadísticas resumidas de jobs
     */
    async getJobsSummary() {
        try {
            const response = await fetch('/api/jobs/stats/summary');
            const data = await response.json();

            if (data.success) {
                return data.summary;
            } else {
                throw new Error('Error obteniendo estadísticas');
            }
        } catch (error) {
            console.error('Error obteniendo estadísticas:', error);
            throw error;
        }
    }

    /**
     * Inicia polling automático de un job
     * Útil para actualizar el estado en tiempo real
     */
    startJobPolling(jobId, callback, interval = 3000) {
        if (this.refreshInterval) {
            this.stopJobPolling();
        }

        // Primera carga inmediata
        this.getJob(jobId, true).then(callback).catch(console.error);

        // Polling periódico
        this.refreshInterval = setInterval(async () => {
            try {
                const job = await this.getJob(jobId, true);
                callback(job);

                // Detener polling si el job terminó
                if (['completed', 'failed', 'cancelled'].includes(job.status)) {
                    this.stopJobPolling();
                }
            } catch (error) {
                console.error('Error en polling:', error);
            }
        }, interval);
    }

    /**
     * Detiene el polling automático
     */
    stopJobPolling() {
        if (this.refreshInterval) {
            clearInterval(this.refreshInterval);
            this.refreshInterval = null;
        }
    }

    /**
     * Formatea el estado de un job para mostrar
     */
    formatJobStatus(status) {
        const statusMap = {
            pending: { label: 'Pendiente', color: 'yellow' },
            running: { label: 'En Ejecución', color: 'blue' },
            completed: { label: 'Completado', color: 'green' },
            failed: { label: 'Fallido', color: 'red' },
            cancelled: { label: 'Cancelado', color: 'gray' },
            paused: { label: 'Pausado', color: 'orange' }
        };

        return statusMap[status] || { label: status, color: 'gray' };
    }

    /**
     * Formatea el tipo de job para mostrar
     */
    formatJobType(type) {
        const typeMap = {
            batch_scraping: 'Scraping en Lote',
            single_scraping: 'Scraping Individual',
            report_generation: 'Generación de Reportes',
            data_export: 'Exportación de Datos'
        };

        return typeMap[type] || type;
    }

    /**
     * Calcula el tiempo transcurrido
     */
    calculateElapsedTime(startTime, endTime = null) {
        const start = new Date(startTime);
        const end = endTime ? new Date(endTime) : new Date();
        const diff = end - start;

        const seconds = Math.floor(diff / 1000);
        const minutes = Math.floor(seconds / 60);
        const hours = Math.floor(minutes / 60);

        if (hours > 0) {
            return `${hours}h ${minutes % 60}m`;
        } else if (minutes > 0) {
            return `${minutes}m ${seconds % 60}s`;
        } else {
            return `${seconds}s`;
        }
    }

    /**
     * Valida una lista de dominios
     */
    validateDomains(domains) {
        const errors = [];
        const validDomains = [];

        domains.forEach((domain, index) => {
            const cleaned = domain.trim();
            
            if (!cleaned) {
                return; // Ignorar líneas vacías
            }

            // Validación básica de formato de dominio
            const domainRegex = /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z0-9][a-z0-9-]{0,61}[a-z0-9]$/i;
            
            // Limpiar protocolo si existe
            const cleanedDomain = cleaned.replace(/^https?:\/\//, '').replace(/\/$/, '');
            
            if (domainRegex.test(cleanedDomain)) {
                validDomains.push(cleanedDomain);
            } else {
                errors.push({
                    line: index + 1,
                    domain: cleaned,
                    message: 'Formato de dominio inválido'
                });
            }
        });

        return { validDomains, errors };
    }
}

// Exportar como singleton
const jobManager = new JobManager();

// Hacer disponible globalmente
if (typeof window !== 'undefined') {
    window.JobManager = jobManager;
}

export default jobManager;
