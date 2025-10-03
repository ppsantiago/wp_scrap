// Basic modal domain scrap form
$(function () {
  const $backdrop = $("#domainFormModal");
  const $modal = $("#modal-domainForm");
  const open = () => {
    $backdrop.addClass("is-open");
    $modal.addClass("is-open");
  };
  const close = () => {
    $backdrop.removeClass("is-open");
    $modal.removeClass("is-open");
  };

  $("#openModalBtn").on("click", function (e) {
    e.preventDefault();
    open();
  });

  $("[data-close-modal]").on("click", function (e) {
    e.preventDefault();
    close();
  });

  // Close when clicking backdrop
  $backdrop.on("click", function () {
    close();
  });

  // Prevent backdrop click when clicking inside modal
  $modal.on("click", function (e) {
    e.stopPropagation();
  });

  //

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
    if (!trimmedDomain) {
      alert("Por favor, ingresa un dominio válido.");
      return;
    }
    // Validación básica: debe contener un punto
    if (!trimmedDomain.includes(".")) {
      alert("Ingresa un dominio válido, como 'example.com'.");
      return;
    }

    const $result = $("#domainResult");
    $result.html("<p>Cargando...</p>").show();

    try {
      const response = await $.ajax({
        url: `/check-domain?domain=${encodeURIComponent(trimmedDomain)}`,
        method: "GET",
      });
      if (response.success) {
        $result.html(
          `<p><strong>${response.domain}</strong> - Código de estado: <code>${response.status_code}</code></p>`
        );
      } else {
        $result.html(`<p>Error: ${response.error}</p>`);
      }
    } catch (error) {
      $result.html(
        `<p>Error en la solicitud: ${error.responseText || error.message}</p>`
      );
    }
  });

  //
});
