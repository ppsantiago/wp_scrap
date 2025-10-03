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
            : String(v).replace(
                /[&<>]/g,
                (s) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;" }[s])
              );
        const links = seo.links || {};
        const images = seo.images || {};
        const seoHtml = `
          <div class="seo-summary">
            <p><strong>${esc(
              response.domain
            )}</strong> - Código de estado: <code>${esc(
          response.status_code
        )}</code></p>
            <h4>SEO</h4>
            <ul>
              <li><strong>Título:</strong> ${esc(seo.title)}</li>
              <li><strong>Meta descripción:</strong> ${esc(
                seo.metaDescription
              )}</li>
              <li><strong>Cantidad de H1:</strong> ${esc(seo.h1Count)}</li>
              <li><strong>Canonical:</strong> ${esc(seo.canonical)}</li>
              <li><strong>Robots:</strong> ${esc(seo.robots)}</li>
              <li><strong>Conteo de palabras:</strong> ${esc(
                seo.wordCount
              )}</li>
              <li><strong>Links:</strong> total ${esc(
                links.total
              )}, internos ${esc(links.internal)}, externos ${esc(
          links.external
        )}, nofollow ${esc(links.nofollow)}</li>
              <li><strong>Imágenes:</strong> total ${esc(
                images.total
              )}, sin alt ${esc(images.withoutAlt)}</li>
            </ul>
          </div>`;
        if (response.site) {
          const s = response.site;
          const list = (arr) =>
            Array.isArray(arr) && arr.length
              ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
              : "-";
          const socials = s.socials || {};
          const socialsHtml = Object.keys(socials).length
            ? `<ul>${Object.entries(socials)
                .map(
                  ([k, v]) =>
                    `<li><strong>${esc(k)}:</strong> ${v
                      .map(esc)
                      .join(", ")}</li>`
                )
                .join("")}</ul>`
            : "-";

          const siteHtml = `
              <h4>Resumen del sitio</h4>
              <ul>
                <li><strong>Páginas rastreadas:</strong> ${esc(
                  s.pages_crawled
                )}</li>
                <li><strong>Emails:</strong> ${list(s.contacts?.emails)}</li>
                <li><strong>Teléfonos:</strong> ${list(s.contacts?.phones)}</li>
                <li><strong>WhatsApp:</strong> ${list(
                  s.contacts?.whatsapp
                )}</li>
                <li><strong>Redes:</strong> ${socialsHtml}</li>
                <li><strong>Formularios detectados:</strong> ${esc(
                  s.forms_found
                )}</li>
                <li><strong>Páginas legales:</strong> ${list(
                  s.legal_pages
                )}</li>
                <li><strong>Integraciones (analytics):</strong> ${list(
                  s.integrations?.analytics
                )}</li>
                <li><strong>Pixels:</strong> ${list(
                  s.integrations?.pixels
                )}</li>
                <li><strong>WordPress:</strong> tema=${esc(
                  s.wp?.theme || "-"
                )}, plugins=${list(s.wp?.plugins)}, REST=${esc(
            s.wp?.rest_api
          )}</li>
              </ul>`;
          $result.append(siteHtml);
        }

        if (Array.isArray(response.pages) && response.pages.length) {
          const rows = response.pages
            .slice(0, 20)
            .map(
              (p) => `
              <tr>
                <td>${esc(p.url)}</td>
                <td>${esc(p.status)}</td>
                <td>${esc((p.emails_found || []).join(", "))}</td>
                <td>${esc((p.phones_found || []).join(", "))}</td>
                <td>${esc(p.forms_count)}</td>
              </tr>
            `
            )
            .join("");
          $result.append(`
              <h4>Muestra de páginas</h4>
              <table class="table table-sm">
                <thead><tr><th>URL</th><th>HTTP</th><th>Emails</th><th>Teléfonos</th><th>Forms</th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            `);
        }
        if (response.site) {
          const s = response.site;
          const list = (arr) =>
            Array.isArray(arr) && arr.length
              ? `<ul>${arr.map((x) => `<li>${esc(x)}</li>`).join("")}</ul>`
              : "-";
          const socials = s.socials || {};
          const socialsHtml = Object.keys(socials).length
            ? `<ul>${Object.entries(socials)
                .map(
                  ([k, v]) =>
                    `<li><strong>${esc(k)}:</strong> ${v
                      .map(esc)
                      .join(", ")}</li>`
                )
                .join("")}</ul>`
            : "-";

          const siteHtml = `
              <h4>Resumen del sitio</h4>
              <ul>
                <li><strong>Páginas rastreadas:</strong> ${esc(
                  s.pages_crawled
                )}</li>
                <li><strong>Emails:</strong> ${list(s.contacts?.emails)}</li>
                <li><strong>Teléfonos:</strong> ${list(s.contacts?.phones)}</li>
                <li><strong>WhatsApp:</strong> ${list(
                  s.contacts?.whatsapp
                )}</li>
                <li><strong>Redes:</strong> ${socialsHtml}</li>
                <li><strong>Formularios detectados:</strong> ${esc(
                  s.forms_found
                )}</li>
                <li><strong>Páginas legales:</strong> ${list(
                  s.legal_pages
                )}</li>
                <li><strong>Integraciones (analytics):</strong> ${list(
                  s.integrations?.analytics
                )}</li>
                <li><strong>Pixels:</strong> ${list(
                  s.integrations?.pixels
                )}</li>
                <li><strong>WordPress:</strong> tema=${esc(
                  s.wp?.theme || "-"
                )}, plugins=${list(s.wp?.plugins)}, REST=${esc(
            s.wp?.rest_api
          )}</li>
              </ul>`;
          $result.append(siteHtml);
        }

        if (Array.isArray(response.pages) && response.pages.length) {
          const rows = response.pages
            .slice(0, 20)
            .map(
              (p) => `
              <tr>
                <td>${esc(p.url)}</td>
                <td>${esc(p.status)}</td>
                <td>${esc((p.emails_found || []).join(", "))}</td>
                <td>${esc((p.phones_found || []).join(", "))}</td>
                <td>${esc(p.forms_count)}</td>
              </tr>
            `
            )
            .join("");
          $result.append(`
              <h4>Muestra de páginas</h4>
              <table class="table table-sm">
                <thead><tr><th>URL</th><th>HTTP</th><th>Emails</th><th>Teléfonos</th><th>Forms</th></tr></thead>
                <tbody>${rows}</tbody>
              </table>
            `);
        }
        $result.html(seoHtml);
      } else {
        const msg =
          response && response.error ? response.error : "Error desconocido";
        $result.html(`<p>Error: ${msg}</p>`);
      }
    } catch (error) {
      $result.html(
        `<p>Error en la solicitud: ${error.responseText || error.message}</p>`
      );
    }
  });
};
