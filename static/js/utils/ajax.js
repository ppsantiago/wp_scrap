// static/js/utils/ajax.js
window.Utils = window.Utils || {};
window.Utils.makeAjaxCall = async function (url, data) {
  try {
    return await $.ajax({
      url: `${url}?${new URLSearchParams(data)}`,
      method: "GET",
    });
  } catch (error) {
    return { error: error.responseText || error.message };
  }
};
