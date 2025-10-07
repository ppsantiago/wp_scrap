// static/js/pages/report_detail.js
// Report detail page logic

window.App = window.App || {};

let reportId = null;
let trustedContactState = {
  options: { emails: [], phones: [] },
  selected: { email: null, phone: null },
};

const IA_REPORT_TYPES = {
  technical: {
    buttonSelector: '[data-report-type="technical"]',
    icon: '🧑🏽‍💻',
    label: 'Generar reporte técnico',
  },
  commercial: {
    buttonSelector: '[data-report-type="commercial"]',
    icon: '📊',
    label: 'Generar reporte comercial',
  },
  deliverable: {
    buttonSelector: '[data-report-type="deliverable"]',
    icon: '📄',
    label: 'Generar reporte entregable',
  },
};

let iaState = {
  isLoading: false,
  type: null,
  controller: null,
};

window.App.initReportDetail = async function(id) {
  reportId = id;
  await Promise.all([loadReportData(), loadTrustedContactSection()]);
  initIaReportButtons();
};

/**
 * Load report data with comments
 */
async function loadReportData() {
  const container = document.getElementById('report-data-container');
  const commentsContainer = document.getElementById('report-comments-container');
  
  if (!container) return;

  try {
    container.innerHTML = '<div class="loading">Cargando reporte...</div>';

    const response = await window.API.reports.getWithComments(reportId, 'frontend');

    // Render report data using existing domainForm logic
    const reportHtml = renderReportData(response);
    container.innerHTML = reportHtml;

    setupReportAccordion(container);

    // Initialize comments if container exists
    if (commentsContainer) {
      window.App.initComments('report-comments-container', 'report', reportId);
    }
  } catch (error) {
    console.error('Error loading report:', error);
    container.innerHTML = '<div class="error-message">Error al cargar reporte. Por favor intenta de nuevo.</div>';
  }
}

function initIaReportButtons() {
  const container = document.getElementById('report-ia-container');
  const wrapper = document.querySelector('.gerenate-report-container');
  if (!container || !wrapper) return;

  ensureMarkdownRenderer();

  Object.entries(IA_REPORT_TYPES).forEach(([type, config]) => {
    const button = wrapper.querySelector(config.buttonSelector);
    if (!button) return;

    button.addEventListener('click', () => handleIaGeneration(type, config, container, button));
  });

  const forceRefreshToggle = createForceRefreshToggle();
  container.insertAdjacentElement('beforebegin', forceRefreshToggle);
}

function createForceRefreshToggle() {
  const wrapper = document.createElement('div');
  wrapper.className = 'ia-force-refresh';
  wrapper.innerHTML = `
    <label class="ia-force-refresh__label">
      <input type="checkbox" id="ia-force-refresh-checkbox" />
      Forzar nueva generación (ignorar cache)
    </label>
  `;
  return wrapper;
}

function ensureMarkdownRenderer() {
  const hasMarked = typeof window.marked === 'function';
  if (hasMarked) return;

  if (!document.getElementById('marked-js')) {
    const script = document.createElement('script');
    script.id = 'marked-js';
    script.src = 'https://cdn.jsdelivr.net/npm/marked/marked.min.js';
    script.async = true;
    script.onerror = () => {
      console.error('No se pudo cargar marked.js para renderizar Markdown.');
    };
    document.head.appendChild(script);
  }
}

function getForceRefreshValue() {
  const checkbox = document.getElementById('ia-force-refresh-checkbox');
  return checkbox ? checkbox.checked : false;
}

async function handleIaGeneration(type, config, container, button) {
  if (!reportId || iaState.isLoading) {
    return;
  }

  resetIaState();
  iaState.isLoading = true;
  iaState.type = type;

  const forceRefresh = getForceRefreshValue();
  const existingContent = container.innerHTML;
  container.innerHTML = renderIaLoading(config, forceRefresh);
  button.disabled = true;

  try {
    const result = await window.API.reports.generateIa(reportId, {
      type,
      force_refresh: forceRefresh,
    });

    renderIaMarkdown(container, result);
    window.App?.notifications?.success?.('Reporte IA generado correctamente.');
  } catch (error) {
    console.error('Error generating AI report:', error);
    container.innerHTML = renderIaError(error, config, existingContent);
    window.App?.notifications?.error?.('Error generando reporte IA.');
  } finally {
    iaState.isLoading = false;
    iaState.type = null;
    button.disabled = false;
  }
}

function resetIaState() {
  if (iaState.controller) {
    try {
      iaState.controller.abort();
    } catch (err) {
      // ignore abort errors
    }
  }
  iaState.controller = null;
}

function renderIaLoading(config, forceRefresh) {
  const refreshLabel = forceRefresh ? ' (forzando nueva ejecución)' : '';
  return `
    <div class="ia-report ia-report--loading">
      <div class="ia-report__spinner"></div>
      <p>${config.icon} Generando ${config.label.toLowerCase()}${refreshLabel}...</p>
    </div>
  `;
}

function renderIaMarkdown(container, result) {
  const markdown = result?.markdown || '';
  const generatedAt = result?.generated_at ? new Date(result.generated_at) : null;
  const cached = result?.cached ? '<span class="ia-report__badge ia-report__badge--cached">Cache</span>' : '';

  if (!markdown) {
    container.innerHTML = '<div class="ia-report ia-report--empty">No se recibió contenido generado.</div>';
    return;
  }

  let htmlContent = markdown;
  if (typeof window.marked === 'function') {
    htmlContent = window.marked.parse(markdown, { breaks: true, gfm: true });
  }

  container.innerHTML = `
    <div class="ia-report">
      <div class="ia-report__meta">
        ${cached}
        ${generatedAt ? `<span class="ia-report__timestamp">Generado: ${generatedAt.toLocaleString()}</span>` : ''}
        ${result?.tokens_used ? `<span class="ia-report__token">Tokens: ${result.tokens_used}</span>` : ''}
        ${result?.duration_ms ? `<span class="ia-report__duration">Duración: ${result.duration_ms} ms</span>` : ''}
      </div>
      <div class="ia-report__content js-ia-report-content">${htmlContent}</div>
      <div class="ia-report__actions">
        <button type="button" class="btn btn-secondary" data-ia-copy>Copiar Markdown</button>
        <button type="button" class="btn btn-secondary" data-ia-download>Descargar .md</button>
      </div>
    </div>
  `;

  bindIaContentActions(container, markdown);
}

function renderIaError(error, config, fallbackContent) {
  const message = extractErrorMessage(error) || 'Error desconocido.';
  return `
    <div class="ia-report ia-report--error">
      <p>${config.icon} ${config.label}</p>
      <p class="ia-report__error">${sanitize(message)}</p>
      <button type="button" class="btn btn-secondary" data-ia-retry>Intentar de nuevo</button>
      <button type="button" class="btn btn-tertiary" data-ia-show-previous>Ver contenido previo</button>
    </div>
    <div class="ia-report ia-report--previous" hidden>${fallbackContent}</div>
  `;
}

function bindIaContentActions(container, markdown) {
  const content = container.querySelector('.js-ia-report-content');
  const copyBtn = container.querySelector('[data-ia-copy]');
  const downloadBtn = container.querySelector('[data-ia-download]');

  if (copyBtn) {
    copyBtn.addEventListener('click', async () => {
      try {
        await navigator.clipboard.writeText(markdown);
        window.App?.notifications?.success?.('Markdown copiado al portapapeles.');
      } catch (err) {
        console.warn('No se pudo copiar Markdown:', err);
        window.App?.notifications?.error?.('No se pudo copiar el Markdown.');
      }
    });
  }

  if (downloadBtn) {
    downloadBtn.addEventListener('click', () => {
      const blob = new Blob([markdown], { type: 'text/markdown;charset=utf-8' });
      const url = URL.createObjectURL(blob);
      const link = document.createElement('a');
      link.href = url;
      const today = new Date();
      link.download = `reporte-ia-${iaState.type || 'general'}-${today.toISOString().split('T')[0]}.md`;
      document.body.appendChild(link);
      link.click();
      document.body.removeChild(link);
      URL.revokeObjectURL(url);
    });
  }
}

function extractErrorMessage(error) {
  if (!error) return null;
  if (typeof error === 'string') return error;
  if (error?.response?.data?.detail) return error.response.data.detail;
  if (error?.detail) return error.detail;
  if (error?.message) return error.message;
  return null;
}

function sanitize(text) {
  if (typeof text !== 'string') return '';
  return text.replace(/[&<>]/g, (s) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;' }[s] || s));
}

document.addEventListener('click', (event) => {
  const retryBtn = event.target.closest('[data-ia-retry]');
  if (retryBtn && iaState.type) {
    const container = document.getElementById('report-ia-container');
    const wrapper = document.querySelector('.gerenate-report-container');
    if (!container || !wrapper) return;

    const config = IA_REPORT_TYPES[iaState.type];
    if (!config) return;

    const button = wrapper.querySelector(config.buttonSelector);
    if (!button) return;

    handleIaGeneration(iaState.type, config, container, button);
  }

  const showPrevBtn = event.target.closest('[data-ia-show-previous]');
  if (showPrevBtn) {
    const previous = document.querySelector('.ia-report--previous');
    if (previous) {
      const hidden = previous.hasAttribute('hidden');
      if (hidden) {
        previous.removeAttribute('hidden');
        showPrevBtn.textContent = 'Ocultar contenido previo';
      } else {
        previous.setAttribute('hidden', 'hidden');
        showPrevBtn.textContent = 'Ver contenido previo';
      }
    }
  }
});

async function loadTrustedContactSection() {
  const container = document.getElementById('trusted-contact-container');
  if (!container) return;

  try {
    container.innerHTML = '<div class="loading">Procesando contactos...</div>';
    const data = await window.API.reports.getTrustedContact(reportId);

    trustedContactState.options = data.options || { emails: [], phones: [] };
    trustedContactState.selected = data.selected || { email: null, phone: null };

    container.innerHTML = renderTrustedContactForm(trustedContactState);
    bindTrustedContactEvents(container);
  } catch (error) {
    console.error('Error loading trusted contact info:', error);
    container.innerHTML = '<div class="error-message">No se pudieron cargar los contactos detectados.</div>';
  }
}

function renderTrustedContactForm(state) {
  const { options, selected } = state;

  const emailOptions = ['<option value="">Sin selección</option>']
    .concat((options.emails || []).map((email) => `
      <option value="${email}" ${selected?.email === email ? 'selected' : ''}>${email}</option>
    `)).join('');

  const phoneOptions = ['<option value="">Sin selección</option>']
    .concat((options.phones || []).map((phone) => `
      <option value="${phone}" ${selected?.phone === phone ? 'selected' : ''}>${phone}</option>
    `)).join('');

  const selectedSummary = selected && (selected.email || selected.phone)
    ? `<p class="trusted-contact-summary">Seleccionado: ${selected.email || '-'} | ${selected.phone || '-'}</p>`
    : '<p class="trusted-contact-summary">Seleccionado: Ninguno</p>';

  return `
    <form id="trusted-contact-form" class="trusted-contact-form">
      <div class="form-group">
        <label for="trusted-contact-email">Email</label>
        <select id="trusted-contact-email" name="email" class="form-control" ${options.emails?.length ? '' : 'disabled'}>
          ${emailOptions}
        </select>
        ${options.emails?.length ? '' : '<p class="help-text">No se detectaron emails.</p>'}
      </div>
      <div class="form-group">
        <label for="trusted-contact-phone">Teléfono</label>
        <select id="trusted-contact-phone" name="phone" class="form-control" ${options.phones?.length ? '' : 'disabled'}>
          ${phoneOptions}
        </select>
        ${options.phones?.length ? '' : '<p class="help-text">No se detectaron teléfonos.</p>'}
      </div>
      <div class="form-actions" style="margin-top: 16px;">
        <button type="button" class="btn btn-primary" id="trusted-contact-save">Guardar selección</button>
        <button type="button" class="btn btn-secondary" id="trusted-contact-clear">Limpiar</button>
      </div>
    </form>
    ${selectedSummary}
  `;
}

function bindTrustedContactEvents(container) {
  const form = container.querySelector('#trusted-contact-form');
  if (!form) return;

  const emailSelect = form.querySelector('#trusted-contact-email');
  const phoneSelect = form.querySelector('#trusted-contact-phone');
  const saveButton = form.querySelector('#trusted-contact-save');
  const clearButton = form.querySelector('#trusted-contact-clear');

  const setLoading = (isLoading) => {
    if (isLoading) {
      container.classList.add('is-loading');
      saveButton.disabled = true;
      clearButton.disabled = true;
    } else {
      container.classList.remove('is-loading');
      saveButton.disabled = false;
      clearButton.disabled = false;
    }
  };

  saveButton.addEventListener('click', async () => {
    try {
      setLoading(true);
      const payload = {
        email: emailSelect && emailSelect.value ? emailSelect.value : null,
        phone: phoneSelect && phoneSelect.value ? phoneSelect.value : null,
      };

      const response = await window.API.reports.setTrustedContact(reportId, payload);
      trustedContactState.selected = response.selected || { email: null, phone: null };
      await loadTrustedContactSection();
    } catch (error) {
      console.error('Error updating trusted contact:', error);
      container.innerHTML = '<div class="error-message">No se pudo guardar la selección. Intenta nuevamente.</div>';
    } finally {
      setLoading(false);
    }
  });

  clearButton.addEventListener('click', async () => {
    try {
      setLoading(true);
      const response = await window.API.reports.setTrustedContact(reportId, { email: null, phone: null });
      trustedContactState.selected = response.selected || { email: null, phone: null };
      await loadTrustedContactSection();
    } catch (error) {
      console.error('Error clearing trusted contact:', error);
      container.innerHTML = '<div class="error-message">No se pudo limpiar la selección. Intenta nuevamente.</div>';
    } finally {
      setLoading(false);
    }
  });
}

/**
 * Render report data (reusing domainForm display logic)
 */
function renderReportData(response) {
  const seo = response.seo || {};
  const tech = response.tech || {};
  const security = response.security || {};
  const site = response.site || {};
  const pages = Array.isArray(response.pages) ? response.pages : [];
  const business = site.business || {};
  const formsDetailed = Array.isArray(site.forms_detailed) ? site.forms_detailed : [];
  const ctaHighlights = Array.isArray(site.cta_highlights) ? site.cta_highlights : [];
  const teamContacts = Array.isArray(site.contacts?.team_contacts) ? site.contacts.team_contacts : [];
  const contactConfidence = site.contacts?.contact_confidence || {};

  const esc = (v) =>
    v === null || v === undefined || v === ""
      ? "-"
      : String(v).replace(/[&<>]/g, (s) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[s]));

  const list = (arr) =>
    Array.isArray(arr) && arr.length
      ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
      : "-";

  const listObj = (obj) =>
    obj && Object.keys(obj).length
      ? `<ul>${Object.entries(obj).map(([k, v]) => `<li><strong>${esc(k)}:</strong> ${esc(v)}</li>`).join("")}</ul>`
      : "-";

  const links = seo.links || {};
  const images = seo.images || {};
  const imgByMime = images.byMime || {};
  const imgByExt = images.byExt || {};
  const h1Count = seo.h1Count ?? seo.h1?.count;
  const h1Sample = seo.h1?.text ? `<p><em>${esc(seo.h1.text)}</em></p>` : "";

  const mimeList = Object.keys(imgByMime).length
    ? `<ul>${Object.entries(imgByMime).map(([k, v]) => `<li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`
    : "-";

  const extList = Object.keys(imgByExt).length
    ? `<ul>${Object.entries(imgByExt).map(([k, v]) => `<li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`
    : "-";

  let html = `
    <div class="results-header">
      <p><strong>${esc(response.domain)}</strong> - Código de estado: <code>${esc(response.status_code)}</code></p>
    </div>
    <div class="card">
      <div class="card-header">
        <h4>📊 SEO</h4>
      </div>
      <div class="card-body">
        <div class="info-grid">
          <div class="info-item"><span class="info-label">Título:</span> <span class="info-value">${esc(seo.title)}</span></div>
          <div class="info-item"><span class="info-label">Meta descripción:</span> <span class="info-value">${esc(seo.metaDescription)}</span></div>
          <div class="info-item"><span class="info-label">Cantidad de H1:</span> <span class="info-value">${esc(h1Count)}</span></div>
          <div class="info-item"><span class="info-label">Canonical:</span> <span class="info-value">${esc(seo.canonical)}</span></div>
          <div class="info-item"><span class="info-label">Robots:</span> <span class="info-value">${esc(seo.robots)}</span></div>
          <div class="info-item"><span class="info-label">Conteo de palabras:</span> <span class="info-value">${esc(seo.wordCount)}</span></div>
        </div>
        ${h1Sample}
        <div class="info-section">
          <h5>Enlaces</h5>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Total:</span> <span class="info-value">${esc(links.total)}</span></div>
            <div class="info-item"><span class="info-label">Internos:</span> <span class="info-value">${esc(links.internal)}</span></div>
            <div class="info-item"><span class="info-label">Externos:</span> <span class="info-value">${esc(links.external)}</span></div>
            <div class="info-item"><span class="info-label">Nofollow:</span> <span class="info-value">${esc(links.nofollow)}</span></div>
          </div>
        </div>
        <div class="info-section">
          <h5>Imágenes</h5>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Total:</span> <span class="info-value">${esc(images.total)}</span></div>
            <div class="info-item"><span class="info-label">Sin alt:</span> <span class="info-value">${esc(images.withoutAlt)}</span></div>
          </div>
          <div class="info-grid mt-2">
            <div class="info-item"><span class="info-label">Por MIME:</span> <div class="info-value">${mimeList}</div></div>
            <div class="info-item"><span class="info-label">Por extensión:</span> <div class="info-value">${extList}</div></div>
          </div>
        </div>
      </div>
    </div>`;

  // Technical data
  const req = tech.requests || {};
  const byType = req.by_type || {};
  const timing = tech.timing || {};
  const secH = security.headers || {};

  const byTypeRows = Object.entries(byType).map(([k, v]) =>
    `<tr><td>${esc(k)}</td><td>${esc(v.count)}</td><td>${esc(v.bytes)}</td></tr>`
  ).join("");

  const reqImgMime = req.images_by_mime || {};
  const reqImgExt = req.images_by_ext || {};
  const reqMimeList = Object.keys(reqImgMime).length
    ? `<ul>${Object.entries(reqImgMime).map(([k, v]) => `<li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`
    : "-";
  const reqExtList = Object.keys(reqImgExt).length
    ? `<ul>${Object.entries(reqImgExt).map(([k, v]) => `<li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`
    : "-";

  html += `
    <div class="card">
      <div class="card-header">
        <h4>⚙️ Información Técnica</h4>
      </div>
      <div class="card-body">
        <div class="info-section">
          <h5>Requests</h5>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Total de requests:</span> <span class="info-value">${esc(req.count || 0)}</span></div>
            <div class="info-item"><span class="info-label">Bytes totales:</span> <span class="info-value">${esc(req.total_bytes || 0)}</span></div>
            <div class="info-item"><span class="info-label">1ros bytes:</span> <span class="info-value">${esc(req.first_party_bytes || 0)}</span></div>
            <div class="info-item"><span class="info-label">3ros bytes:</span> <span class="info-value">${esc(req.third_party_bytes || 0)}</span></div>
          </div>
        </div>

        <div class="info-section">
          <h5>Timing (ms aprox)</h5>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">TTFB:</span> <span class="info-value">${esc(timing.ttfb)}</span></div>
            <div class="info-item"><span class="info-label">DCL:</span> <span class="info-value">${esc(timing.dcl)}</span></div>
            <div class="info-item"><span class="info-label">Load:</span> <span class="info-value">${esc(timing.load)}</span></div>
          </div>
        </div>

        ${byTypeRows ? `
        <div class="info-section">
          <h5>Requests por tipo</h5>
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>Tipo</th><th>#</th><th>Bytes</th></tr></thead>
              <tbody>${byTypeRows}</tbody>
            </table>
          </div>
        </div>
        ` : ""}

        <div class="info-section">
          <h5>Formatos de imágenes (red)</h5>
          <div class="info-grid">
            <div class="info-item"><span class="info-label">Por MIME:</span> <div class="info-value">${reqMimeList}</div></div>
            <div class="info-item"><span class="info-label">Por extensión:</span> <div class="info-value">${reqExtList}</div></div>
          </div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-header">
        <h4>🔒 Security Headers</h4>
      </div>
      <div class="card-body">
        <div class="info-grid">
          <div class="info-item"><span class="info-label">HSTS:</span> <span class="info-value">${esc(secH.hsts)}</span></div>
          <div class="info-item"><span class="info-label">CSP:</span> <span class="info-value">${esc(secH.csp)}</span></div>
          <div class="info-item"><span class="info-label">X-Frame-Options:</span> <span class="info-value">${esc(secH.xfo)}</span></div>
          <div class="info-item"><span class="info-label">X-Content-Type-Options:</span> <span class="info-value">${esc(secH.xcto)}</span></div>
        </div>
      </div>
    </div>`;

  if (site && Object.keys(site).length > 0) {
    const socials = site.socials || {};
    const socialsHtml = Object.keys(socials).length
      ? `<ul>${Object.entries(socials).map(([k, v]) => `<li><strong>${esc(k)}:</strong> ${v.map(esc).join(", ")}</li>`).join("")}</ul>`
      : "-";

    const personal = list(contactConfidence.personal);
    const generic = list(contactConfidence.generic);
    const confidenceHtml = personal === "-" && generic === "-"
      ? "-"
      : `
        <div class="info-grid">
          <div class="info-item"><span class="info-label">Personales:</span> <div class="info-value">${personal}</div></div>
          <div class="info-item"><span class="info-label">Genéricos:</span> <div class="info-value">${generic}</div></div>
        </div>`;

    const teamContactsHtml = teamContacts.length
      ? `<div style="overflow-x: auto;">
          <table class="table table-sm">
            <thead><tr><th>Nombre</th><th>Cargo</th><th>Email</th><th>Confianza</th><th>Teléfono</th><th>Perfiles</th><th>Fuente</th></tr></thead>
            <tbody>${teamContacts.slice(0, 25).map((tc) => `
              <tr>
                <td>${esc(tc.name)}</td>
                <td>${esc(tc.job_title)}</td>
                <td>${esc(tc.email)}</td>
                <td>${esc(tc.email_confidence)}</td>
                <td>${esc(tc.phone)}</td>
                <td>${Array.isArray(tc.social_profiles) && tc.social_profiles.length ? tc.social_profiles.map((sp) => `<a href="${esc(sp)}" target="_blank" rel="noopener">${esc(sp)}</a>`).join('<br>') : '-'}</td>
                <td>${esc(tc.source)}</td>
              </tr>
            `).join("")}</tbody>
          </table>
        </div>`
      : '<p class="muted">No se detectaron perfiles de equipo con schema Person.</p>';

    const formsIntegrationsList = list(site.integrations?.forms);

    html += `
      <div class="card">
        <div class="card-header">
          <h4>🌐 Resumen del Sitio</h4>
        </div>
        <div class="card-body">
          <div class="info-item"><span class="info-label">Páginas rastreadas:</span> <span class="info-value">${esc(site.pages_crawled)}</span></div>

          <div class="info-section">
            <h5>Contactos</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Emails:</span> <div class="info-value">${list(site.contacts?.emails)}</div></div>
              <div class="info-item"><span class="info-label">Teléfonos:</span> <div class="info-value">${list(site.contacts?.phones)}</div></div>
              <div class="info-item"><span class="info-label">WhatsApp:</span> <div class="info-value">${list(site.contacts?.whatsapp)}</div></div>
            </div>
            <div class="info-subsection">
              <h6>Confianza en Emails</h6>
              ${confidenceHtml}
            </div>
            <div class="info-subsection">
              <h6>Contactos del Equipo (schema Person)</h6>
              ${teamContactsHtml}
            </div>
          </div>

          <div class="info-section">
            <h5>Redes Sociales</h5>
            <div class="info-value">${socialsHtml}</div>
          </div>

          <div class="info-section">
            <h5>Formularios y Legal</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Formularios detectados:</span> <span class="info-value">${esc(site.forms_found)}</span></div>
              <div class="info-item"><span class="info-label">Páginas legales:</span> <div class="info-value">${list(site.legal_pages)}</div></div>
            </div>
            <div class="info-subsection">
              <h6>Integraciones de Formularios</h6>
              ${formsIntegrationsList}
            </div>
          </div>

          ${site.integrations ? `
          <div class="info-section">
            <h5>Integraciones de Analytics/Pixels</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Analytics:</span> <div class="info-value">${list(site.integrations.analytics)}</div></div>
              <div class="info-item"><span class="info-label">Pixels:</span> <div class="info-value">${list(site.integrations.pixels)}</div></div>
            </div>
          </div>
          ` : ""}

          ${site.wp ? `
          <div class="info-section">
            <h5>WordPress</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Tema:</span> <span class="info-value">${esc(site.wp.theme || "-")}</span></div>
              <div class="info-item"><span class="info-label">REST API:</span> <span class="info-value">${esc(site.wp.rest_api)}</span></div>
              <div class="info-item"><span class="info-label">Plugins:</span> <div class="info-value">${list(site.wp.plugins)}</div></div>
            </div>
          </div>
          ` : ""}
        </div>
      </div>`;
  }

  if (formsDetailed.length) {
    const formRows = formsDetailed.slice(0, 40).map((form) => {
      const inputs = Array.isArray(form.inputs)
        ? form.inputs.map((inp) => `${esc(inp.type)} ${esc(inp.name || "(sin name)")}${inp.required ? " *" : ""}`).join('<br>')
        : "-";
      const buttons = Array.isArray(form.buttons) && form.buttons.length ? form.buttons.map(esc).join('<br>') : "-";
      return `
        <tr>
          <td>${esc(form.page_type || "-")}</td>
          <td>${esc(form.page)}</td>
          <td>${esc(form.method)}</td>
          <td>${esc(form.action)}</td>
          <td>${inputs}</td>
          <td>${buttons}</td>
          <td>${esc(form.hasCaptcha)}</td>
          <td>${esc(form.integration)}</td>
        </tr>`;
    }).join("");

    html += `
      <div class="card">
        <div class="card-header">
          <h4>📝 Formularios detectados</h4>
        </div>
        <div class="card-body">
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>Tipo de página</th><th>URL</th><th>Método</th><th>Acción</th><th>Campos</th><th>Botones</th><th>CAPTCHA</th><th>Integración</th></tr></thead>
              <tbody>${formRows}</tbody>
            </table>
          </div>
        </div>
      </div>`;
  }

  if (ctaHighlights.length) {
    const ctaRows = ctaHighlights.slice(0, 40).map((cta) => `
      <tr>
        <td>${esc(cta.page_type)}</td>
        <td>${esc(cta.page)}</td>
        <td>${esc(cta.text)}</td>
        <td>${cta.href ? `<a href="${esc(cta.href)}" target="_blank" rel="noopener">${esc(cta.href)}</a>` : '-'}</td>
      </tr>`).join("");

    html += `
      <div class="card">
        <div class="card-header">
          <h4>🎯 CTA destacados</h4>
        </div>
        <div class="card-body">
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>Tipo de página</th><th>URL</th><th>Texto</th><th>Destino</th></tr></thead>
              <tbody>${ctaRows}</tbody>
            </table>
          </div>
        </div>
      </div>`;
  }

  if (business && Object.keys(business).length) {
    const businessSections = Object.entries(business).map(([key, values]) => `
      <div class="info-subsection">
        <h6>${esc(key)}</h6>
        ${list(values)}
      </div>
    `).join("");

    html += `
      <div class="card">
        <div class="card-header">
          <h4>🏢 Información de negocio</h4>
        </div>
        <div class="card-body">
          ${businessSections}
        </div>
      </div>`;
  }

  if (pages.length) {
    const rows = pages.slice(0, 40).map((p) => `
      <tr>
        <td>${esc(p.page_type || '-')}</td>
        <td>${esc(p.seed_type || '-')}</td>
        <td>${esc(p.url)}</td>
        <td>${esc(p.status)}</td>
        <td>${esc((p.emails_found || []).join(', '))}</td>
        <td>${esc((p.phones_found || []).join(', '))}</td>
        <td>${esc(p.forms_count)}</td>
        <td>${p.team_contacts && p.team_contacts.length ? p.team_contacts.map((tc) => esc(tc.name || tc.email || '-')).join('<br>') : '-'}</td>
      </tr>`).join("");

    html += `
      <div class="card">
        <div class="card-header">
          <h4>📄 Muestra de Páginas</h4>
        </div>
        <div class="card-body">
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>Tipo</th><th>Seed</th><th>URL</th><th>HTTP</th><th>Emails</th><th>Teléfonos</th><th>Forms</th><th>Team sample</th></tr></thead>
              <tbody>${rows}</tbody>
            </table>
          </div>
        </div>
      </div>`;
  }

  return html;
}

function setupReportAccordion(container) {
  const cards = Array.from(container.querySelectorAll('.card'));
  const toggleCards = cards.filter((card) =>
    card.querySelector('.card-header') && card.querySelector('.card-body')
  );

  if (!toggleCards.length) {
    return;
  }

  let expandedCard = null;

  const collapseCard = (card) => {
    const body = card.querySelector('.card-body');
    const header = card.querySelector('.card-header');
    if (!body || !header) return;
    body.style.display = 'none';
    card.classList.add('collapsed');
    card.setAttribute('data-expanded', 'false');
    header.setAttribute('aria-expanded', 'false');
  };

  const expandCard = (card) => {
    const body = card.querySelector('.card-body');
    const header = card.querySelector('.card-header');
    if (!body || !header) return;
    body.style.display = '';
    card.classList.remove('collapsed');
    card.setAttribute('data-expanded', 'true');
    header.setAttribute('aria-expanded', 'true');
  };

  toggleCards.forEach((card, index) => {
    const header = card.querySelector('.card-header');
    const body = card.querySelector('.card-body');
    if (!header || !body) {
      return;
    }

    header.classList.add('card-toggle-header');
    header.setAttribute('role', 'button');
    header.setAttribute('tabindex', '0');

    if (index === 0) {
      expandCard(card);
      expandedCard = card;
    } else {
      collapseCard(card);
    }

    const handleToggle = () => {
      if (expandedCard === card) {
        collapseCard(card);
        expandedCard = null;
        return;
      }

      if (expandedCard) {
        collapseCard(expandedCard);
      }

      expandCard(card);
      expandedCard = card;
    };

    header.addEventListener('click', handleToggle);
    header.addEventListener('keydown', (event) => {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        handleToggle();
      }
    });
  });
}
