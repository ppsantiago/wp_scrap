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
        $result.html(`<p><strong>${response.domain}</strong> - Código de estado: <code>${response.status_code}</code></p>`);
      } else {
        const msg = response && response.error ? response.error : "Error desconocido";
        $result.html(`<p>Error: ${msg}</p>`);
      }
    } catch (error) {
      $result.html(`<p>Error en la solicitud: ${error.responseText || error.message}</p>`);
    }
  });
};
