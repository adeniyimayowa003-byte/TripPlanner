/* DOM-only privacy hygiene. No history, network calls or persistent storage. */
(function () {
  "use strict";
  function clearPrivateView() {
    document.querySelectorAll("[data-assistant-private]").forEach(function (node) {
      node.replaceChildren();
    });
    document.querySelectorAll("textarea").forEach(function (node) { node.value = ""; });
    document.querySelectorAll('input[type="checkbox"]').forEach(function (node) { node.checked = false; });
  }
  window.addEventListener("pagehide", clearPrivateView);
  window.addEventListener("pageshow", function (event) {
    if (event.persisted) clearPrivateView();
  });
}());
