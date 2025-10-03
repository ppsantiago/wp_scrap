// static/js/components/modal.js
window.App = window.App || {};
window.App.initModal = function () {
  const $backdrop = $("#domainFormModal");
  const $modal = $("#modal-domainForm");
  if (!$backdrop.length || !$modal.length) return;

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

  $backdrop.on("click", close);
  $modal.on("click", function (e) {
    e.stopPropagation();
  });
};
