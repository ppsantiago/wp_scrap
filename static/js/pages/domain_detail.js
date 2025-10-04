// static/js/pages/domain_detail.js
// Domain detail page logic

window.App = window.App || {};

let domainId = null;
let domainName = null;

window.App.initDomainDetail = async function(name) {
  domainName = name;
  await loadDomainInfo();
  await loadDomainHistory();
};

/**
 * Load domain information and comments
 */
async function loadDomainInfo() {
  const container = document.getElementById('domain-info-container');
  const commentsContainer = document.getElementById('domain-comments-container');
  
  if (!container) return;

  try {
    container.innerHTML = '<div class="loading">Cargando información del dominio...</div>';

    const response = await window.API.domains.getWithComments(domainName, false);
    domainId = response.id;

    const html = `
      <div class="info-grid">
        <div class="info-item">
          <span class="info-label">Dominio</span>
          <span class="info-value">${escapeHtml(response.domain)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Estado</span>
          <span class="info-value"><span class="status-badge status-${response.status}">${response.status}</span></span>
        </div>
        <div class="info-item">
          <span class="info-label">Total de Reportes</span>
          <span class="info-value">${response.total_reports || 0}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Primer Análisis</span>
          <span class="info-value">${formatDate(response.first_scraped_at)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Último Análisis</span>
          <span class="info-value">${formatDate(response.last_scraped_at)}</span>
        </div>
        <div class="info-item">
          <span class="info-label">Comentarios</span>
          <span class="info-value">${response.comments?.length || 0}</span>
        </div>
      </div>
    `;

    container.innerHTML = html;

    // Initialize comments component if container exists
    if (commentsContainer && domainId) {
      window.App.initComments('domain-comments-container', 'domain', domainId);
    }
  } catch (error) {
    console.error('Error loading domain info:', error);
    container.innerHTML = '<div class="error-message">Error al cargar información del dominio</div>';
  }
}

/**
 * Load domain history (reports)
 */
async function loadDomainHistory() {
  const container = document.getElementById('domain-history-container');
  if (!container) return;

  try {
    container.innerHTML = '<div class="loading">Cargando historial...</div>';

    const response = await window.API.domains.getHistory(domainName, 10, 0, false);
    const reports = response.reports || [];

    if (reports.length === 0) {
      container.innerHTML = '<div class="no-comments">No hay reportes disponibles para este dominio.</div>';
      return;
    }

    const rows = reports.map(report => `
      <tr class="domain-row" onclick="window.location.href='/report/${report.id}'">
        <td><a href="/report/${report.id}" class="domain-link">#${report.id}</a></td>
        <td>${formatDate(report.scraped_at)}</td>
        <td><code>${report.status_code || '-'}</code></td>
        <td>${report.success ? '✅' : '❌'}</td>
        <td>${report.metrics?.pages_crawled || 0}</td>
        <td>${report.metrics?.seo_word_count || 0}</td>
        <td>${report.metrics?.seo_links_total || 0}</td>
      </tr>
    `).join('');

    const html = `
      <table class="table table-sm">
        <thead>
          <tr>
            <th>ID</th>
            <th>Fecha</th>
            <th>HTTP</th>
            <th>Éxito</th>
            <th>Páginas</th>
            <th>Palabras</th>
            <th>Enlaces</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
    `;

    container.innerHTML = html;
  } catch (error) {
    console.error('Error loading domain history:', error);
    container.innerHTML = '<div class="error-message">Error al cargar historial</div>';
  }
}

/**
 * Helper: Escape HTML
 */
function escapeHtml(text) {
  if (!text) return '';
  const div = document.createElement('div');
  div.textContent = text;
  return div.innerHTML;
}

/**
 * Helper: Format date
 */
function formatDate(dateString) {
  if (!dateString) return '-';
  const date = new Date(dateString);
  return date.toLocaleDateString('es-ES', {
    year: 'numeric',
    month: 'short',
    day: 'numeric',
    hour: '2-digit',
    minute: '2-digit'
  });
}
