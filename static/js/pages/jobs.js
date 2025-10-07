// static/js/pages/jobs.js
// Jobs page functionality

class JobsManager {
  constructor() {
    console.log('🏗️ JobsManager constructor called');
    this.jobs = [];
    this.filteredJobs = [];
    this.selectedJobs = new Set();
    this.searchQuery = '';
    this.stats = { by_status: {} };
    this.refreshInterval = null;
    this.isLoading = false;

    // Initialize immediately since we're loaded after API is ready
    this.init();
  }

  async init() {
    console.log('🚀 Initializing JobsManager...');

    // Final check to ensure API is available
    if (typeof window.API === 'undefined' || typeof window.API.jobs === 'undefined') {
      console.error('❌ API not available during initialization');
      return;
    }

    // Setup event listeners first
    this.setupEventListeners();

    // Initialize with empty state immediately
    this.renderStats();
    this.renderJobs();

    // Then load real data
    await this.loadData();

    console.log('✅ Jobs page ready');
  }

  async loadData() {
    console.log('📊 Loading jobs data...');

    try {
      await Promise.all([
        this.loadStats(),
        this.loadJobs()
      ]);

      console.log('✅ Data loaded successfully');
    } catch (error) {
      console.error('❌ Error loading data:', error);
    }
  }

  setupEventListeners() {
    // Search input
    const searchInput = document.getElementById('searchInput');
    if (searchInput) {
      searchInput.addEventListener('input', (e) => {
        this.searchQuery = e.target.value;
        this.applyFiltersAndSearch();
      });
    }

    // Create job button
    const createJobBtn = document.getElementById('createJobBtn');
    if (createJobBtn) {
      createJobBtn.addEventListener('click', (event) => {
        event.preventDefault();
        event.stopPropagation();
        this.showCreateModal();
      });
    }

    // Modal close buttons
    const cancelJobBtn = document.getElementById('cancelJobBtn');
    const cancelJobBtn2 = document.getElementById('cancelJobBtn2');
    if (cancelJobBtn) {
      cancelJobBtn.addEventListener('click', () => this.hideCreateModal());
    }
    if (cancelJobBtn2) {
      cancelJobBtn2.addEventListener('click', () => this.hideCreateModal());
    }

    // Close modal when clicking on backdrop
    const modal = document.getElementById('createJobModal');
    if (modal) {
      modal.addEventListener('click', (e) => {
        if (e.target === modal) {
          this.hideCreateModal();
        }
      });
    }

    // Refresh button
    const refreshBtn = document.getElementById('refreshBtn');
    if (refreshBtn) {
      refreshBtn.addEventListener('click', () => this.refreshData());
    }

    // Filters
    const statusFilter = document.getElementById('statusFilter');
    const typeFilter = document.getElementById('typeFilter');

    if (statusFilter) {
      statusFilter.addEventListener('change', () => this.applyFiltersAndSearch());
    }

    if (typeFilter) {
      typeFilter.addEventListener('change', () => this.applyFiltersAndSearch());
    }

    // Bulk actions
    this.setupBulkActionListeners();
    // Create job form
    const createJobForm = document.getElementById('createJobForm');
    if (createJobForm) {
      createJobForm.addEventListener('submit', (e) => this.handleCreateJob(e));
    }

    // Bulk actions
    this.setupBulkActionListeners();
  }

  setupBulkActionListeners() {
    const selectAllBtn = document.getElementById('selectAllBtn');
    const clearSelectionBtn = document.getElementById('clearSelectionBtn');
    const bulkCancelBtn = document.getElementById('bulkCancelBtn');
    const bulkRetryBtn = document.getElementById('bulkRetryBtn');
    const bulkDeleteBtn = document.getElementById('bulkDeleteBtn');

    if (selectAllBtn) {
      selectAllBtn.addEventListener('click', () => this.selectAllJobs());
    }

    if (clearSelectionBtn) {
      clearSelectionBtn.addEventListener('click', () => this.clearSelection());
    }

    if (bulkCancelBtn) {
      bulkCancelBtn.addEventListener('click', () => this.bulkCancelJobs());
    }

    if (bulkRetryBtn) {
      bulkRetryBtn.addEventListener('click', () => this.bulkRetryJobs());
    }

    if (bulkDeleteBtn) {
      bulkDeleteBtn.addEventListener('click', () => this.bulkDeleteJobs());
    }
  }

  async loadStats() {
    try {
      const response = await window.API.jobs.getStatsSummary();

      if (response && response.success) {
        this.stats = response.summary;
        this.renderStats();
      } else {
        this.stats = { by_status: {} };
        this.renderStats();
      }
    } catch (error) {
      console.error('Error loading stats:', error);
      this.stats = { by_status: {} };
      this.renderStats();
    }
  }

  async loadJobs() {
    try {
      const statusFilter = document.getElementById('statusFilter')?.value || null;
      const typeFilter = document.getElementById('typeFilter')?.value || null;

      const response = await window.API.jobs.list(statusFilter, typeFilter);

      if (response && response.success) {
        this.jobs = response.jobs || [];
        this.applyFiltersAndSearch();
      } else {
        this.jobs = [];
        this.applyFiltersAndSearch();
      }
    } catch (error) {
      console.error('Error loading jobs:', error);
      this.jobs = [];
      this.applyFiltersAndSearch();
    }
  }

  applyFiltersAndSearch() {
    const statusFilter = document.getElementById('statusFilter')?.value || null;
    const typeFilter = document.getElementById('typeFilter')?.value || null;

    // Filter jobs
    this.filteredJobs = this.jobs.filter(job => {
      // Status filter
      if (statusFilter && job.status !== statusFilter) {
        return false;
      }

      // Type filter
      if (typeFilter && job.job_type !== typeFilter) {
        return false;
      }

      // Search filter
      if (this.searchQuery) {
        const query = this.searchQuery.toLowerCase();
        const matchesName = job.name.toLowerCase().includes(query);
        const matchesDescription = job.description?.toLowerCase().includes(query);
        const matchesId = job.id.toString().includes(query);

        if (!matchesName && !matchesDescription && !matchesId) {
          return false;
        }
      }

      return true;
    });

    this.renderJobs();
    this.updateBulkActionsVisibility();
  }

  updateBulkActionsVisibility() {
    const bulkActionsBar = document.getElementById('bulkActionsBar');
    if (bulkActionsBar) {
      if (this.selectedJobs.size > 0) {
        bulkActionsBar.classList.add('visible');
      } else {
        bulkActionsBar.classList.remove('visible');
      }
    }
  }
  renderStats() {
    const container = document.getElementById('statsContainer');
    if (!container) return;

    try {
      const maxCount = Math.max(...Object.values(this.stats.by_status || {}));

      container.innerHTML = [
        { key: 'pending', label: 'Pendientes', icon: '⏳' },
        { key: 'running', label: 'En Ejecución', icon: '⚡' },
        { key: 'completed', label: 'Completados', icon: '✅' },
        { key: 'failed', label: 'Fallidos', icon: '❌' },
        { key: 'cancelled', label: 'Cancelados', icon: '🚫' }
      ].map((status) => {
        const count = this.stats.by_status?.[status.key] || 0;
        const percentage = maxCount > 0 ? (count / maxCount) * 100 : 0;
        return `
          <div class="stat-card">
            <div class="stat-icon">${status.icon}</div>
            <div class="stat-content">
              <div class="stat-label">${status.label}</div>
              <div class="stat-value">${count}</div>
            </div>
            <div class="stat-progress">
              <div class="stat-progress-bar" style="width: ${percentage}%"></div>
            </div>
          </div>
        `;
      }).join('');
    } catch (error) {
      console.error('Error rendering stats:', error);
      container.innerHTML = '<p style="color: #ef4444;">Error rendering stats</p>';
    }
  }

  renderJobs() {
    const container = document.getElementById('jobsContainer');
    const emptyState = document.getElementById('emptyState');
    const loadingState = document.getElementById('loadingState');

    if (!container) return;

    // Hide loading state
    if (loadingState) loadingState.style.display = 'none';

    if (this.filteredJobs.length === 0 && this.jobs.length === 0) {
      // No jobs at all
      container.innerHTML = '';
      emptyState?.classList.add('visible');
      return;
    }

    if (this.filteredJobs.length === 0 && this.jobs.length > 0) {
      // Jobs exist but filters don't match
      emptyState?.classList.remove('visible');
      container.innerHTML = `
        <div class="no-results">
          <h3>No se encontraron resultados</h3>
          <p>No hay jobs que coincidan con los filtros seleccionados.</p>
          <button onclick="document.getElementById('statusFilter').value=''; document.getElementById('typeFilter').value=''; document.getElementById('searchInput').value=''; jobsManager.searchQuery=''; jobsManager.applyFiltersAndSearch();"
            class="btn-primary">
            Limpiar filtros
          </button>
        </div>
      `;
      return;
    }

    emptyState?.classList.remove('visible');
    container.innerHTML = this.filteredJobs.map(job => this.renderJobCard(job)).join('');
  }

  renderJobCard(job) {
    const statusColors = {
      pending: 'status-pending',
      running: 'status-running',
      completed: 'status-completed',
      failed: 'status-failed',
      cancelled: 'status-cancelled'
    };

    const statusColor = statusColors[job.status] || 'status-cancelled';
    const createdAt = new Date(job.created_at).toLocaleString('es-ES', { 
      year: 'numeric', month: 'short', day: 'numeric', 
      hour: '2-digit', minute: '2-digit' 
    });
    const updatedAt = job.updated_at ? new Date(job.updated_at).toLocaleString('es-ES', { 
      year: 'numeric', month: 'short', day: 'numeric', 
      hour: '2-digit', minute: '2-digit' 
    }) : '';
    const progressWidth = Math.min(job.progress_percentage || 0, 100);
    const isSelected = this.selectedJobs.has(job.id);

    return `
      <div class="job-card">
        <input
          type="checkbox"
          class="job-checkbox"
          data-job-id="${job.id}"
          ${isSelected ? 'checked' : ''}
          onchange="jobsManager.toggleJobSelection(${job.id})"
        >

        <div class="job-header">
          <div class="job-info">
            <div class="job-title-row">
              <h3 class="job-title">${job.name}</h3>
              <span class="status-badge ${statusColor}">
                ${this.getStatusLabel(job.status)}
              </span>
            </div>
            <p class="job-description">${job.description || 'Sin descripción'}</p>
          </div>

          <div class="job-actions">
            <button onclick="event.stopPropagation(); this.nextElementSibling.classList.toggle('visible')" class="actions-trigger">
              <svg fill="currentColor" viewBox="0 0 20 20">
                <path d="M10 6a2 2 0 110-4 2 2 0 010 4zM10 12a2 2 0 110-4 2 2 0 010 4zM10 18a2 2 0 110-4 2 2 0 010 4z"/>
              </svg>
            </button>

            <div class="actions-menu">
              <button onclick="event.stopPropagation(); jobsManager.viewJobDetails(${job.id})">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M15 12a3 3 0 11-6 0 3 3 0 016 0z"/>
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z"/>
                </svg>
                Ver detalles
              </button>
              ${job.status === 'running' ? `
                <button onclick="event.stopPropagation(); jobsManager.cancelJob(${job.id})" class="danger">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-2.5L13.732 4c-.77-.833-1.964-.833-2.732 0L3.732 16.5c-.77.833.192 2.5 1.732 2.5z"/>
                  </svg>
                  Cancelar job
                </button>
              ` : ''}
              ${job.status === 'failed' ? `
                <button onclick="event.stopPropagation(); jobsManager.retryJob(${job.id})" class="primary">
                  <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                  </svg>
                  Reintentar
                </button>
              ` : ''}
              <button onclick="event.stopPropagation(); jobsManager.deleteJob(${job.id})" class="danger">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 7l-.867 12.142A2 2 0 0116.138 21H7.862a2 2 0 01-1.995-1.858L5 7m5 4v6m4-6v6m1-10V4a1 1 0 00-1-1h-4a1 1 0 00-1 1v3M4 7h16"/>
                </svg>
                Eliminar
              </button>
            </div>
          </div>
        </div>

        <div class="job-progress">
          <div class="progress-header">
            <span class="progress-label">Progreso del trabajo</span>
            <span class="progress-percent">${progressWidth}%</span>
          </div>
          <div class="progress-bar-container">
            <div class="progress-bar" style="width: ${progressWidth}%"></div>
          </div>
        </div>

        <div class="job-metrics">
          <div class="metric-card total">
            <div class="metric-value">${job.total_steps || 0}</div>
            <div class="metric-label">Total</div>
          </div>
          <div class="metric-card completed">
            <div class="metric-value">${job.completed_steps || 0}</div>
            <div class="metric-label">Completados</div>
          </div>
          <div class="metric-card failed">
            <div class="metric-value">${job.failed_steps || 0}</div>
            <div class="metric-label">Fallidos</div>
          </div>
        </div>

        <div class="job-footer">
          <div class="job-timestamps">
            <div class="timestamp">
              <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M8 7V3m8 4V3m-9 8h10M5 21h14a2 2 0 002-2V7a2 2 0 00-2-2H5a2 2 0 00-2 2v12a2 2 0 002 2z"/>
              </svg>
              <span>${createdAt}</span>
            </div>
            ${updatedAt ? `
              <div class="timestamp">
                <svg fill="none" stroke="currentColor" viewBox="0 0 24 24">
                  <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M4 4v5h.582m15.356 2A8.001 8.001 0 004.582 9m0 0H9m11 11v-5h-.581m0 0a8.003 8.003 0 01-15.357-2m15.357 2H15"/>
                </svg>
                <span>${updatedAt}</span>
              </div>
            ` : ''}
          </div>
          <div class="job-id">#${job.id}</div>
        </div>

        <div onclick="window.location.href='/job/${job.id}'" class="job-clickable"></div>
      </div>
    `;
  }

  getStatusLabel(status) {
    const labels = {
      pending: 'Pendiente',
      running: 'En ejecución',
      completed: 'Completado',
      failed: 'Fallido',
      cancelled: 'Cancelado'
    };
    return labels[status] || status;
  }

  async handleCreateJob(event) {
    event.preventDefault();

    const name = document.getElementById('jobName')?.value || '';
    const description = document.getElementById('jobDescription')?.value || '';
    const domainsText = document.getElementById('jobDomains')?.value || '';

    // Parse domains
    const domains = domainsText
      .split('\n')
      .map(d => d.trim())
      .filter(d => d.length > 0);

    if (domains.length === 0) {
      this.showNotification('Debes ingresar al menos un dominio', 'error');
      return;
    }

    try {
      this.setLoading(true);
      const response = await window.API.jobs.createBatchScraping({
        domains,
        name,
        description,
        createdBy: 'user'
      });

      if (response.success) {
        this.hideCreateModal();
        document.getElementById('createJobForm')?.reset();
        this.showNotification('Job creado exitosamente', 'success');
        // Redirect to job detail
        window.location.href = `/job/${response.job.id}`;
      } else {
        this.showNotification(response.message || 'Error creando job', 'error');
      }
    } catch (error) {
      console.error('Error creating job:', error);
      this.showNotification('Error creando job', 'error');
    } finally {
      this.setLoading(false);
    }
  }

  showCreateModal() {
    const modal = document.getElementById('createJobModal');
    if (modal) {
      modal.classList.add('visible');
      // Don't set display manually - let CSS handle it
      setTimeout(() => document.getElementById('jobName')?.focus(), 100);
    }
  }

  hideCreateModal() {
    const modal = document.getElementById('createJobModal');
    if (modal) {
      modal.classList.remove('visible');
      // Don't set display manually - let CSS handle it
      document.getElementById('createJobForm')?.reset();
    }
  }

  showJobActions(jobId) {
    // TODO: Implement job actions menu (cancel, retry, delete)
    console.log('Show actions for job:', jobId);
  }

  async viewJobDetails(jobId) {
    window.location.href = `/job/${jobId}`;
  }

  async cancelJob(jobId) {
    if (!confirm('¿Estás seguro de que quieres cancelar este job?')) return;

    try {
      const response = await window.API.jobs.cancel(jobId);
      if (response.success) {
        this.showNotification('Job cancelado exitosamente', 'success');
        await this.refreshData();
      } else {
        this.showNotification(response.message || 'Error cancelando job', 'error');
      }
    } catch (error) {
      console.error('Error canceling job:', error);
      this.showNotification('Error cancelando job', 'error');
    }
  }

  async retryJob(jobId) {
    if (!confirm('¿Estás seguro de que quieres reintentar este job?')) return;

    try {
      const response = await window.API.jobs.retry(jobId);
      if (response.success) {
        this.showNotification('Job reintentado exitosamente', 'success');
        await this.refreshData();
      } else {
        this.showNotification(response.message || 'Error reintentando job', 'error');
      }
    } catch (error) {
      console.error('Error retrying job:', error);
      this.showNotification('Error reintentando job', 'error');
    }
  }

  async deleteJob(jobId) {
    if (!confirm('¿Estás seguro de que quieres eliminar este job? Esta acción no se puede deshacer.')) return;

    try {
      const response = await window.API.jobs.delete(jobId);
      if (response.success) {
        this.showNotification('Job eliminado exitosamente', 'success');
        await this.refreshData();
      } else {
        this.showNotification(response.message || 'Error eliminando job', 'error');
      }
    } catch (error) {
      console.error('Error deleting job:', error);
      this.showNotification('Error eliminando job', 'error');
    }
  }

  async applyFilters() {
    await this.applyFiltersAndSearch();
  }

  toggleJobSelection(jobId) {
    const checkbox = document.querySelector(`[data-job-id="${jobId}"]`);
    if (checkbox.checked) {
      this.selectedJobs.add(jobId);
    } else {
      this.selectedJobs.delete(jobId);
    }
    this.updateSelectedCount();
  }

  updateSelectedCount() {
    const selectedCount = document.getElementById('selectedCount');
    if (selectedCount) {
      const count = this.selectedJobs.size;
      selectedCount.innerHTML = `
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 5H7a2 2 0 00-2 2v12a2 2 0 002 2h10a2 2 0 002-2V7a2 2 0 00-2-2h-2M9 5a2 2 0 002 2h2a2 2 0 002-2M9 5a2 2 0 012-2h2a2 2 0 012 2m-6 9l2 2 4-4"/>
        </svg>
        ${count} job${count !== 1 ? 's' : ''} seleccionado${count !== 1 ? 's' : ''}
      `;
    }
  }

  selectAllJobs() {
    this.filteredJobs.forEach(job => {
      this.selectedJobs.add(job.id);
    });

    // Update all checkboxes
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
      checkbox.checked = true;
    });

    this.updateSelectedCount();
  }

  clearSelection() {
    this.selectedJobs.clear();

    // Update all checkboxes
    document.querySelectorAll('.job-checkbox').forEach(checkbox => {
      checkbox.checked = false;
    });

    this.updateSelectedCount();
  }

  async bulkCancelJobs() {
    if (this.selectedJobs.size === 0) {
      this.showNotification('No hay jobs seleccionados', 'error');
      return;
    }

    if (!confirm(`¿Estás seguro de que quieres cancelar ${this.selectedJobs.size} job${this.selectedJobs.size !== 1 ? 's' : ''}?`)) return;

    let successCount = 0;
    let errorCount = 0;

    for (const jobId of this.selectedJobs) {
      try {
        const response = await window.API.jobs.cancel(jobId);
        if (response.success) {
          successCount++;
        } else {
          errorCount++;
        }
      } catch (error) {
        console.error(`Error canceling job ${jobId}:`, error);
        errorCount++;
      }
    }

    this.clearSelection();
    this.showNotification(`Cancelados: ${successCount}, Errores: ${errorCount}`, successCount > 0 ? 'success' : 'error');
    await this.refreshData();
  }

  async bulkRetryJobs() {
    if (this.selectedJobs.size === 0) {
      this.showNotification('No hay jobs seleccionados', 'error');
      return;
    }

    if (!confirm(`¿Estás seguro de que quieres reintentar ${this.selectedJobs.size} job${this.selectedJobs.size !== 1 ? 's' : ''}?`)) return;

    let successCount = 0;
    let errorCount = 0;

    for (const jobId of this.selectedJobs) {
      try {
        const response = await window.API.jobs.retry(jobId);
        if (response.success) {
          successCount++;
        } else {
          errorCount++;
        }
      } catch (error) {
        console.error(`Error retrying job ${jobId}:`, error);
        errorCount++;
      }
    }

    this.clearSelection();
    this.showNotification(`Reintentados: ${successCount}, Errores: ${errorCount}`, successCount > 0 ? 'success' : 'error');
    await this.refreshData();
  }

  async bulkDeleteJobs() {
    if (this.selectedJobs.size === 0) {
      this.showNotification('No hay jobs seleccionados', 'error');
      return;
    }

    if (!confirm(`¿Estás seguro de que quieres eliminar ${this.selectedJobs.size} job${this.selectedJobs.size !== 1 ? 's' : ''}? Esta acción no se puede deshacer.`)) return;

    let successCount = 0;
    let errorCount = 0;

    for (const jobId of this.selectedJobs) {
      try {
        const response = await window.API.jobs.delete(jobId);
        if (response.success) {
          successCount++;
        } else {
          errorCount++;
        }
      } catch (error) {
        console.error(`Error deleting job ${jobId}:`, error);
        errorCount++;
      }
    }

    this.clearSelection();
    this.showNotification(`Eliminados: ${successCount}, Errores: ${errorCount}`, successCount > 0 ? 'success' : 'error');
    await this.refreshData();
  }

  async refreshData() {
    await this.loadData();
  }

  startAutoRefresh() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }

    this.refreshInterval = setInterval(() => {
      const hasRunningJobs = this.jobs.some(job => job.status === 'running' || job.status === 'pending');
      if (hasRunningJobs) {
        this.refreshData();
      }
    }, 5000);
  }

  setLoading(loading) {
    this.isLoading = loading;
    const loadingState = document.getElementById('loadingState');
    if (loadingState) {
      loadingState.style.display = loading ? 'block' : 'none';
    }
  }

  showNotification(message, type = 'info') {
    // Create toast notification
    const toastId = 'toast-' + Date.now();
    const colors = {
      success: 'bg-emerald-500',
      error: 'bg-red-500',
      warning: 'bg-orange-500',
      info: 'bg-blue-500'
    };
    
    const icons = {
      success: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M9 12l2 2 4-4m6 2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
      error: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 14l2-2m0 0l2-2m-2 2l-2-2m2 2l2 2m7-2a9 9 0 11-18 0 9 9 0 0118 0z"/>',
      warning: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M12 9v2m0 4h.01m-6.938 4h13.856c1.54 0 2.502-1.667 1.732-3l-6.928-12c-.77-1.333-2.694-1.333-3.464 0L3.34 16c-.77 1.333.192 3 1.732 3z"/>',
      info: '<path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M13 16h-1v-4h-1m1-4h.01M21 12a9 9 0 11-18 0 9 9 0 0118 0z"/>'
    };

    const toast = document.createElement('div');
    toast.id = toastId;
    toast.className = `fixed top-4 right-4 ${colors[type] || colors.info} text-white px-6 py-4 rounded-lg shadow-2xl flex items-center gap-3 max-w-md z-50 animate-slideIn`;
    toast.innerHTML = `
      <svg class="w-6 h-6 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
        ${icons[type] || icons.info}
      </svg>
      <span class="font-medium">${message}</span>
      <button onclick="this.parentElement.remove()" class="ml-2 hover:bg-white/20 rounded p-1 transition-colors">
        <svg class="w-5 h-5" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"/>
        </svg>
      </button>
    `;

    document.body.appendChild(toast);

    // Auto remove after 5 seconds
    setTimeout(() => {
      const el = document.getElementById(toastId);
      if (el) {
        el.style.animation = 'slideOut 0.3s ease-out';
        setTimeout(() => el.remove(), 300);
      }
    }, 5000);
  }

  destroy() {
    if (this.refreshInterval) {
      clearInterval(this.refreshInterval);
    }
  }
}

// Initialize when DOM is ready
let jobsManager;
document.addEventListener('DOMContentLoaded', () => {
  jobsManager = new JobsManager();
});

// Cleanup on page unload
window.addEventListener('beforeunload', () => {
  if (jobsManager) {
    jobsManager.destroy();
  }
});
