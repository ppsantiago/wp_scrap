// static/js/pages/domains.js
// Domains list page logic

window.App = window.App || {};

let currentPage = 0;
const PAGE_SIZE = 20;
let totalDomains = 0;

window.App.initDomainsList = async function() {
  await loadDomains();
  setupFilters();
  setupPagination();
};

/**
 * Load domains list
 */
async function loadDomains(offset = 0) {
  const container = document.getElementById('domains-list-container');
  if (!container) return;

  try {
    container.innerHTML = '<div class="loading">Cargando dominios...</div>';

    currentPage = Math.max(0, Math.floor(offset / PAGE_SIZE));

    const response = await window.API.domains.list(PAGE_SIZE, offset);
    const domains = response.domains || [];
    totalDomains = response.total || 0;

    if (domains.length === 0 && offset > 0) {
      const newOffset = Math.max(0, offset - PAGE_SIZE);
      if (newOffset !== offset) {
        await loadDomains(newOffset);
        return;
      }
    }

    if (domains.length === 0 && offset === 0) {
      container.innerHTML = `
        <div class="no-comments">
          <p>No hay dominios analizados aún.</p>
          <a href="/scrap" class="btn-primary" style="margin-top: 16px;">Analizar Primer Dominio</a>
        </div>
      `;
      updatePaginationInfo();
      return;
    }

    const rowsHtml = domains.map((domain, index) => `
      <tr class="domain-row" onclick="window.location.href='/domain/${encodeURIComponent(domain.domain)}'">
        <td>${offset + index + 1}</td>
        <td><a href="/domain/${encodeURIComponent(domain.domain)}" class="domain-link">${escapeHtml(domain.domain)}</a></td>
        <td><span class="status-badge status-${domain.status}">${domain.status}</span></td>
        <td>${domain.total_reports || 0}</td>
        <td>${formatDate(domain.first_scraped_at)}</td>
        <td>${formatDate(domain.last_scraped_at)}</td>
        <td class="actions-cell">
          <button class="btn-secondary btn-danger btn-delete-domain" data-domain="${encodeURIComponent(domain.domain)}">Eliminar</button>
        </td>
      </tr>
    `).join('');

    const html = `
      <table class="table domain-table">
        <thead>
          <tr>
            <th>#</th>
            <th>Dominio</th>
            <th>Estado</th>
            <th>Reportes</th>
            <th>Primer Análisis</th>
            <th>Último Análisis</th>
            <th>Acciones</th>
          </tr>
        </thead>
        <tbody>
          ${rowsHtml}
        </tbody>
      </table>
    `;

    container.innerHTML = html;
    updatePaginationInfo();
    attachDeleteHandlers();
  } catch (error) {
    console.error('Error loading domains:', error);
    container.innerHTML = '<div class="error-message">Error al cargar dominios. Por favor intenta de nuevo.</div>';
  }
}
/**
 * Setup pagination
 */
function setupPagination() {
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');

  if (prevBtn) {
    prevBtn.addEventListener('click', () => {
      if (currentPage > 0) {
        currentPage--;
        loadDomains(currentPage * PAGE_SIZE);
      }
    });
  }

  if (nextBtn) {
    nextBtn.addEventListener('click', () => {
      if ((currentPage + 1) * PAGE_SIZE < totalDomains) {
        currentPage++;
        loadDomains(currentPage * PAGE_SIZE);
      }
    });
  }
}

/**
 * Update pagination info
 */
function updatePaginationInfo() {
  const prevBtn = document.getElementById('prev-page-btn');
  const nextBtn = document.getElementById('next-page-btn');
  const paginationInfo = document.getElementById('pagination-info');

  if (prevBtn) prevBtn.disabled = currentPage === 0;
  if (nextBtn) nextBtn.disabled = (currentPage + 1) * PAGE_SIZE >= totalDomains;

  if (paginationInfo) {
    const start = currentPage * PAGE_SIZE + 1;
    const end = Math.min((currentPage + 1) * PAGE_SIZE, totalDomains);
    paginationInfo.textContent = `Mostrando ${start}-${end} de ${totalDomains}`;
  }
}

function attachDeleteHandlers() {
  const buttons = document.querySelectorAll('.btn-delete-domain');
  buttons.forEach((button) => {
    button.addEventListener('click', async (event) => {
      event.preventDefault();
      event.stopPropagation();

      const domainName = decodeURIComponent(button.dataset.domain || '');
      if (!domainName) return;

      const confirmed = window.confirm(`¿Eliminar el dominio "${domainName}" y todos sus reportes asociados?`);
      if (!confirmed) {
        return;
      }

      const originalText = button.textContent;
      button.disabled = true;
      button.textContent = 'Eliminando...';

      try {
        await window.API.domains.delete(domainName);
        await loadDomains(currentPage * PAGE_SIZE);
      } catch (error) {
        console.error('Error deleting domain:', error);
        alert('No se pudo eliminar el dominio. Intenta nuevamente.');
        button.disabled = false;
        button.textContent = originalText;
      }
    });
  });
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
