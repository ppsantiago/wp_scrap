// static/js/components/domainForm.js
window.App = window.App || {};
window.App.initDomainForm = function () {
  $("#domainForm").on("submit", async function (e) {
    e.preventDefault();
    const domainElement = $("#domainInput");
    if (!domainElement.length) {
      alert("Error: Elemento de dominio no encontrado.");
      return;
    }
    const domain = domainElement.val();
    if (typeof domain !== "string") {
      alert("Error: Valor del dominio no es válido.");
      return;
    }
    const trimmedDomain = domain.trim();

    if (
      !window.Utils ||
      !window.Utils.validateDomain ||
      !window.Utils.validateDomain(trimmedDomain)
    ) {
      alert("Por favor, ingresa un dominio válido, como 'example.com'.");
      return;
    }

    const $result = $("#domainResult");
    $result.html("<p>Cargando...</p>").show();

    try {
      const makeAjaxCall = window.Utils && window.Utils.makeAjaxCall;
      const response = makeAjaxCall
        ? await makeAjaxCall("/check-domain", { domain: trimmedDomain })
        : await $.ajax({
            url: `/check-domain?domain=${encodeURIComponent(trimmedDomain)}`,
            method: "GET",
          });

      if (response && response.success) {
  const seo = response.seo || {};
  const esc = (v) =>
    v === null || v === undefined || v === ""
      ? "-"
      : String(v).replace(/[&<>]/g, (s) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[s]));

  const links = seo.links || {};
  const images = seo.images || {};
  const imgByMime = images.byMime || {};
  const imgByExt = images.byExt || {};

  const mimeList = Object.keys(imgByMime).length
    ? `<ul>${Object.entries(imgByMime).map(([k,v]) => ` <li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>` 
    : "-";

  const extList = Object.keys(imgByExt).length
    ? `<ul>${Object.entries(imgByExt).map(([k,v]) => ` <li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>` 
    : "-";

  const seoHtml = `
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

  // Resumen del sitio (si viene)
  let siteHtml = "";
  if (response.site) {
    const s = response.site;
    const list = (arr) =>
      Array.isArray(arr) && arr.length
        ? `<ul>${arr.map((x) => ` <li>${esc(x)}</li>`).join("")}</ul>` 
        : "-";
    const socials = s.socials || {};
    const socialsHtml = Object.keys(socials).length
      ? `<ul>${Object.entries(socials).map(([k, v]) => ` <li><strong>${esc(k)}:</strong> ${v.map(esc).join(", ")}</li>`).join("")}</ul>` 
      : "-";

    siteHtml = `
      <div class="card">
        <div class="card-header">
          <h4>🌐 Resumen del Sitio</h4>
        </div>
        <div class="card-body">
          <div class="info-item"><span class="info-label">Páginas rastreadas:</span> <span class="info-value">${esc(s.pages_crawled)}</span></div>
          
          <div class="info-section">
            <h5>Contactos</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Emails:</span> <div class="info-value">${list(s.contacts?.emails)}</div></div>
              <div class="info-item"><span class="info-label">Teléfonos:</span> <div class="info-value">${list(s.contacts?.phones)}</div></div>
              <div class="info-item"><span class="info-label">WhatsApp:</span> <div class="info-value">${list(s.contacts?.whatsapp)}</div></div>
            </div>
          </div>

          <div class="info-section">
            <h5>Redes Sociales</h5>
            <div class="info-value">${socialsHtml}</div>
          </div>

          <div class="info-section">
            <h5>Formularios y Legal</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Formularios detectados:</span> <span class="info-value">${esc(s.forms_found)}</span></div>
              <div class="info-item"><span class="info-label">Páginas legales:</span> <div class="info-value">${list(s.legal_pages)}</div></div>
            </div>
          </div>

          <div class="info-section">
            <h5>Integraciones</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Analytics:</span> <div class="info-value">${list(s.integrations?.analytics)}</div></div>
              <div class="info-item"><span class="info-label">Pixels:</span> <div class="info-value">${list(s.integrations?.pixels)}</div></div>
            </div>
          </div>

          ${s.wp ? `
          <div class="info-section">
            <h5>WordPress</h5>
            <div class="info-grid">
              <div class="info-item"><span class="info-label">Tema:</span> <span class="info-value">${esc(s.wp.theme || "-")}</span></div>
              <div class="info-item"><span class="info-label">REST API:</span> <span class="info-value">${esc(s.wp.rest_api)}</span></div>
              <div class="info-item"><span class="info-label">Plugins:</span> <div class="info-value">${list(s.wp.plugins)}</div></div>
            </div>
          </div>
          ` : ''}
        </div>
      </div>`;
  }

  // Tabla de páginas (si viene)
  let pagesHtml = "";
  if (Array.isArray(response.pages) && response.pages.length) {
    const rows = response.pages.slice(0, 20).map((p) => `
      <tr>
        <td>${esc(p.url)}</td>
        <td>${esc(p.status)}</td>
        <td>${esc((p.emails_found || []).join(", "))}</td>
        <td>${esc((p.phones_found || []).join(", "))}</td>
        <td>${esc(p.forms_count)}</td>
      </tr>`).join("");
    pagesHtml = `
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

  // --- Técnicas & Seguridad ---
  const tech = response.tech || {};
  const req = tech.requests || {};
  const byType = req.by_type || {};
  const timing = tech.timing || {};
  const security = response.security || {};
  const secH = (security.headers || {});

  const byTypeRows = Object.entries(byType).map(([k,v]) =>
    `<tr><td>${esc(k)}</td><td>${esc(v.count)}</td><td>${esc(v.bytes)}</td></tr>` 
  ).join("");

  // NUEVO: formatos de imágenes en técnicas
  const reqImgMime = (req.images_by_mime || {});
  const reqImgExt  = (req.images_by_ext  || {});
  const reqMimeList = Object.keys(reqImgMime).length
    ? `<ul>${Object.entries(reqImgMime).map(([k,v]) => ` <li>${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`  : "-";
  const reqExtList = Object.keys(reqImgExt).length
    ? `<ul>${Object.entries(reqImgExt).map(([k,v]) => ` <li>.${esc(k)}: ${esc(v)}</li>`).join("")}</ul>`  : "-";

  const techHtml = `
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

        <div class="info-section">
          <h5>Requests por tipo</h5>
          <div style="overflow-x: auto;">
            <table class="table table-sm">
              <thead><tr><th>Tipo</th><th>#</th><th>Bytes</th></tr></thead>
              <tbody>${byTypeRows || ""}</tbody>
            </table>
          </div>
        </div>

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

  // Render final (una sola vez, sin sobrescribir lo ya agregado)
  $result.html(seoHtml + techHtml + siteHtml + pagesHtml);
} else {
  const msg = response && response.error ? response.error : "Error desconocido";
  $result.html(`<p>Error: ${msg}</p>` );
}
    } catch (error) {
      $result.html(
        `<p>Error en la solicitud: ${error.responseText || error.message}</p>`
      );
    }
  });
};
