// App entrypoint: initialize modular components
$(function () {
  if (window.App && typeof window.App.initModal === "function") {
    window.App.initModal();
  }
  if (window.App && typeof window.App.initDomainForm === "function") {
    window.App.initDomainForm();
  }
});
