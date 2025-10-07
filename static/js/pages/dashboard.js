// static/js/pages/dashboard.js
// Dashboard page logic

window.App = window.App || {};

window.App.initDashboard = async function() {
  await loadStatistics();
  await loadRecentDomains();
  await loadRecentComments();
};

/**
 * Load general statistics
 */
async function loadStatistics() {
  const statsContainer = document.getElementById('stats-container');
  if (!statsContainer) return;

  try {
    statsContainer.innerHTML = '<div class="loading">Cargando estadísticas...</div>';

    const stats = await window.API.statistics.getGeneral();
    const commentStats = await window.API.comments.getStatistics();

    const html = `
      <div class="stats-grid">
        <div class="stat-card">
          <div class="stat-value">${stats.total_domains || 0}</div>
          <div class="stat-label">Dominios</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.total_reports || 0}</div>
          <div class="stat-label">Análisis</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${commentStats.statistics?.active_comments || 0}</div>
          <div class="stat-label">Comentarios</div>
        </div>
        <div class="stat-card">
          <div class="stat-value">${stats.success_rate ? Math.round(stats.success_rate) : 0}%</div>
          <div class="stat-label">Tasa Éxito</div>
        </div>
      </div>
    `;

    statsContainer.innerHTML = html;
  } catch (error) {
    console.error('Error loading statistics:', error);
    statsContainer.innerHTML = '<div class="error-message">Error al cargar estadísticas</div>';
  }
}

/**
 * Load recent domains
 */
async function loadRecentDomains() {
  const domainsContainer = document.getElementById('recent-domains-container');
  if (!domainsContainer) return;

  try {
    domainsContainer.innerHTML = '<div class="loading">Cargando dominios recientes...</div>';

    const response = await window.API.domains.list(10, 0);
    const domains = response.domains || [];

    if (domains.length === 0) {
      domainsContainer.innerHTML = '<p class="no-comments">No hay dominios analizados aún.</p>';
      return;
    }

    const rows = domains.map(domain => `
      <tr class="domain-row">
        <td><a href="/domain/${encodeURIComponent(domain.domain)}" class="domain-link">${escapeHtml(domain.domain)}</a></td>
        <td><span class="status-badge status-${domain.status}">${domain.status}</span></td>
        <td>${domain.total_reports || 0}</td>
        <td>${formatDate(domain.last_scraped_at)}</td>
      </tr>
    `).join('');

    const html = `
      <table class="table domain-table">
        <thead>
          <tr>
            <th>Dominio</th>
            <th>Estado</th>
            <th>Reportes</th>
            <th>Último Análisis</th>
          </tr>
        </thead>
        <tbody>
          ${rows}
        </tbody>
      </table>
      <div style="text-align: center; margin-top: 16px;">
        <a href="/domains" class="btn-primary">Ver todos los dominios</a>
      </div>
    `;

    domainsContainer.innerHTML = html;
  } catch (error) {
    console.error('Error loading recent domains:', error);
    domainsContainer.innerHTML = '<div class="error-message">Error al cargar dominios</div>';
  }
}

/**
 * Load recent comments
 */
async function loadRecentComments() {
  const commentsContainer = document.getElementById('recent-comments-container');
  if (!commentsContainer) return;

  try {
    commentsContainer.innerHTML = '<div class="loading">Cargando comentarios recientes...</div>';

    const response = await window.API.comments.getRecent(10);
    const comments = response.comments || [];

    if (comments.length === 0) {
      commentsContainer.innerHTML = '<p class="no-comments">No hay comentarios aún.</p>';
      return;
    }

    const html = comments.map(comment => {
      const entityUrl = getCommentEntityUrl(comment);
      const entityLabel = getCommentEntityLabel(comment);
      return `
        <div class="comment" data-comment-id="${comment.id}">
          <div class="comment-header">
            <div class="comment-author">
              <strong>${escapeHtml(comment.author)}</strong>
              <span class="comment-time">${getTimeAgo(comment.created_at)}</span>
            </div>
          </div>
          <div class="comment-content">${escapeHtml(comment.content)}</div>
          <div class="comment-actions">
            <span class="comment-indicator">
              ${comment.content_type === 'domain' ? '🌐' : '📄'} 
              ${entityLabel}
            </span>
            ${entityUrl ? `<a class="btn-link" href="${entityUrl}">Ver detalle</a>` : ''}
          </div>
        </div>
      `;
    }).join('');

    commentsContainer.innerHTML = html;
  } catch (error) {
    console.error('Error loading recent comments:', error);
    commentsContainer.innerHTML = '<div class="error-message">Error al cargar comentarios</div>';
  }
}

function getCommentEntityUrl(comment) {
  if (!comment) {
    return null;
  }

  if (comment.entity && comment.entity.url) {
    return comment.entity.url;
  }

  if (!comment.content_type) {
    return null;
  }

  if (comment.content_type === 'domain') {
    if (!comment.domain || !comment.domain.domain) {
      return null;
    }
    return `/domain/${encodeURIComponent(comment.domain.domain)}`;
  }

  if (comment.content_type === 'report') {
    if (!comment.report || !comment.report.id) {
      return null;
    }
    return `/report/${comment.report.id}`;
  }

  return null;
}

function getCommentEntityLabel(comment) {
  if (!comment) {
    return '';
  }

  if (comment.entity && comment.entity.label) {
    return comment.entity.label;
  }

  return comment.content_type || '';
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
    day: 'numeric'
  });
}

/**
 * Helper: Get time ago
 */
function getTimeAgo(timestamp) {
  if (!timestamp) return '';
  
  const date = new Date(timestamp);
  const now = new Date();
  const seconds = Math.floor((now - date) / 1000);

  const intervals = {
    año: 31536000,
    mes: 2592000,
    semana: 604800,
    día: 86400,
    hora: 3600,
    minuto: 60
  };

  for (const [name, value] of Object.entries(intervals)) {
    const count = Math.floor(seconds / value);
    if (count >= 1) {
      return `hace ${count} ${name}${count !== 1 ? (name === 'mes' ? 'es' : 's') : ''}`;
    }
  }

  return 'hace un momento';
}
