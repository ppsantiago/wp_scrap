// static/js/pages/report_detail.js
// Report detail page logic

window.App = window.App || {};

let reportId = null;
let trustedContactState = {
  options: { emails: [], phones: [] },
  selected: { email: null, phone: null },
};

window.App.initReportDetail = async function(id) {
  reportId = id;
  await Promise.all([loadReportData(), loadTrustedContactSection()]);
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
  const pages = response.pages || [];

  const esc = (v) =>
    v === null || v === undefined || v === ""
      ? "-"
      : String(v).replace(/[&<>]/g, (s) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[s]));

  const links = seo.links || {};
  const images = seo.images || {};
  const imgByMime = images.byMime || {};
  const imgByExt = images.byExt || {};

  const mimeList = Object.keys(imgByMime).length
    ? `<ul>${Object.entries(imgByMime).map(([k,v]) => `<li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>` 
    : "-";

  const extList = Object.keys(imgByExt).length
    ? `<ul>${Object.entries(imgByExt).map(([k,v]) => `<li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>` 
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
          <div class="info-item"><span class="info-label">Cantidad de H1:</span> <span class="info-value">${esc(seo.h1Count)}</span></div>
          <div class="info-item"><span class="info-label">Canonical:</span> <span class="info-value">${esc(seo.canonical)}</span></div>
          <div class="info-item"><span class="info-label">Robots:</span> <span class="info-value">${esc(seo.robots)}</span></div>
          <div class="info-item"><span class="info-label">Conteo de palabras:</span> <span class="info-value">${esc(seo.wordCount)}</span></div>
        </div>
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
  const secH = (security.headers || {});

  const byTypeRows = Object.entries(byType).map(([k,v]) =>
    `<tr><td>${esc(k)}</td><td>${esc(v.count)}</td><td>${esc(v.bytes)}</td></tr>` 
  ).join("");

  const reqImgMime = (req.images_by_mime || {});
  const reqImgExt  = (req.images_by_ext  || {});
  const reqMimeList = Object.keys(reqImgMime).length
    ? `<ul>${Object.entries(reqImgMime).map(([k,v]) => `<li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`  : "-";
  const reqExtList = Object.keys(reqImgExt).length
    ? `<ul>${Object.entries(reqImgExt).map(([k,v]) => `<li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`  : "-";

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
        ` : ''}

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

  // Site data if available
  if (site && Object.keys(site).length > 0) {
    const list = (arr) =>
      Array.isArray(arr) && arr.length
        ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>` 
        : "-";
    const socials = site.socials || {};
    const socialsHtml = Object.keys(socials).length
      ? `<ul>${Object.entries(socials).map(([k, v]) => `<li><strong>${esc(k)}:</strong> ${v.map(esc).join(", ")}</li>`).join("")}</ul>` 
      : "-";

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
          </div>

          ${site.integrations ? `
          <div class="info-section">
            <h5>Integraciones</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Analytics:</span> <div class="info-value">${list(site.integrations.analytics)}</div></div>
              <div class="info-item"><span class="info-label">Pixels:</span> <div class="info-value">${list(site.integrations.pixels)}</div></div>
            </div>
          </div>
          ` : ''}

          ${site.wp ? `
          <div class="info-section">
            <h5>WordPress</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Tema:</span> <span class="info-value">${esc(site.wp.theme || "-")}</span></div>
              <div class="info-item"><span class="info-label">REST API:</span> <span class="info-value">${esc(site.wp.rest_api)}</span></div>
              <div class="info-item"><span class="info-label">Plugins:</span> <div class="info-value">${list(site.wp.plugins)}</div></div>
            </div>
          </div>
          ` : ''}
        </div>
      </div>`;
  }

  // Pages table if available
  if (Array.isArray(pages) && pages.length > 0) {
    const rows = pages.slice(0, 20).map((p) => `
      <tr>
        <td>${esc(p.url)}</td>
        <td>${esc(p.status)}</td>
        <td>${esc((p.emails_found || []).join(", "))}</td>
        <td>${esc((p.phones_found || []).join(", "))}</td>
        <td>${esc(p.forms_count)}</td>
      </tr>`).join("");
    
    html += `
      <div class="card">
        <div class="card-header">
          <h4>📄 Muestra de Páginas</h4>
        </div>
        <div class="card-body">
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>URL</th><th>HTTP</th><th>Emails</th><th>Teléfonos</th><th>Forms</th></tr></thead>
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
