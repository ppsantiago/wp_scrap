// static/js/utils/validation.js
window.Utils = window.Utils || {};
window.Utils.validateDomain = function (domain) {
  return (
    typeof domain === "string" &&
    domain.trim().length > 0 &&
    domain.includes(".")
  );
};
