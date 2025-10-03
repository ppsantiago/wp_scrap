// Basic modal logic using jQuery
$(function () {
  const $backdrop = $("#modal-backdrop");
  const $modal = $("#modal");
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

  // Temporary: prevent form submission
  $("#contactForm").on("submit", function (e) {
    e.preventDefault();
    // No action for now
    close();
  });
});
