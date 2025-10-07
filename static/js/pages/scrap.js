// static/js/pages/scrap.js
// Maneja la creación de jobs de scraping individual desde la vista /scrap

(function () {
  $(function () {
    const $form = $("#singleScrapForm");
    if (!$form.length) return;

    const $domainInput = $("#singleScrapDomain");
    const $feedback = $("#singleScrapFeedback");
    const $submitButton = $form.find('button[type="submit"]');
    let isSubmitting = false;

    const setFeedback = (message, type = "info") => {
      const colors = {
        success: "#15803d",
        error: "#dc2626",
        info: "#2563eb",
      };
      $feedback.css("color", colors[type] || colors.info);
      $feedback.html(message || "");
    };

    const cleanDomain = (value) =>
      value
        .trim()
        .replace(/^https?:\/\//i, "")
        .replace(/\/$/, "");

    $form.on("submit", async (event) => {
      event.preventDefault();
      if (isSubmitting) return;

      const rawDomain = ($domainInput.val() || "").toString();
      const domain = cleanDomain(rawDomain);

      if (!domain) {
        setFeedback("Ingresa un dominio para continuar.", "error");
        return;
      }

      const isValid =
        window.Utils && typeof window.Utils.validateDomain === "function"
          ? window.Utils.validateDomain(domain)
          : /^(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}$/i.test(domain);

      if (!isValid) {
        setFeedback(
          "Formato de dominio inválido. Ejemplo esperado: ejemplo.com",
          "error"
        );
        return;
      }

      if (!window.API || !window.API.jobs || !window.API.jobs.createSingleScraping) {
        setFeedback("API no disponible en este momento.", "error");
        return;
      }

      try {
        isSubmitting = true;
        $submitButton.prop("disabled", true).addClass("is-loading");
        setFeedback("Creando job de scraping...", "info");

        const response = await window.API.jobs.createSingleScraping(
          domain,
          null,
          `Scraping individual para ${domain}`,
          "web"
        );

        if (response && response.success && response.job) {
          const jobId = response.job.id;
          setFeedback(
            `Job creado correctamente (#${jobId}). Redirigiendo al detalle...`,
            "success"
          );
          $form[0].reset();

          setTimeout(() => {
            window.location.href = `/job/${jobId}`;
          }, 1200);
        } else {
          const message =
            (response && response.message) ||
            "No se pudo crear el job. Intenta nuevamente.";
          setFeedback(message, "error");
        }
      } catch (error) {
        const message =
          error?.message || "Ocurrió un error creando el job.";
        setFeedback(message, "error");
      } finally {
        isSubmitting = false;
        $submitButton.prop("disabled", false).removeClass("is-loading");
      }
    });
  });
})();
