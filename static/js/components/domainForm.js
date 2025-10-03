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

    if (!window.Utils || !window.Utils.validateDomain || !window.Utils.validateDomain(trimmedDomain)) {
      alert("Por favor, ingresa un dominio válido, como 'example.com'.");
      return;
    }

    const $result = $("#domainResult");
    $result.html("<p>Cargando...</p>").show();

    try {
      const makeAjaxCall = window.Utils && window.Utils.makeAjaxCall;
      const response = makeAjaxCall
        ? await makeAjaxCall("/check-domain", { domain: trimmedDomain })
        : await $.ajax({ url: `/check-domain?domain=${encodeURIComponent(trimmedDomain)}`, method: "GET" });

      if (response && response.success) {
        const seo = response.seo || {};
        const esc = (v) => (v === null || v === undefined || v === "" ? "-" : String(v).replace(/[&<>]/g, s => ({"&":"&amp;","<":"&lt;",">":"&gt;"}[s])));
        const links = seo.links || {};
        const images = seo.images || {};
        const seoHtml = `
          <div class="seo-summary">
            <p><strong>${esc(response.domain)}</strong> - Código de estado: <code>${esc(response.status_code)}</code></p>
            <h4>SEO</h4>
            <ul>
              <li><strong>Título:</strong> ${esc(seo.title)}</li>
              <li><strong>Meta descripción:</strong> ${esc(seo.metaDescription)}</li>
              <li><strong>Cantidad de H1:</strong> ${esc(seo.h1Count)}</li>
              <li><strong>Canonical:</strong> ${esc(seo.canonical)}</li>
              <li><strong>Robots:</strong> ${esc(seo.robots)}</li>
              <li><strong>Conteo de palabras:</strong> ${esc(seo.wordCount)}</li>
              <li><strong>Links:</strong> total ${esc(links.total)}, internos ${esc(links.internal)}, externos ${esc(links.external)}, nofollow ${esc(links.nofollow)}</li>
              <li><strong>Imágenes:</strong> total ${esc(images.total)}, sin alt ${esc(images.withoutAlt)}</li>
            </ul>
          </div>`;
        $result.html(seoHtml);
      } else {
        const msg = response && response.error ? response.error : "Error desconocido";
        $result.html(`<p>Error: ${msg}</p>`);
      }
    } catch (error) {
      $result.html(`<p>Error en la solicitud: ${error.responseText || error.message}</p>`);
    }
  });
};
