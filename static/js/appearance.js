/* Appearance is browser-local UI state, never part of a trip or saved snapshot. */
(function () {
  "use strict";

  const storageKey = "tripplanner.appearance";

  function isMode(value) {
    return value === "system" || value === "light" || value === "dark";
  }

  // This runs in the head, before the header exists and before styles load.
  // Accessing localStorage itself can throw, not only its get/set methods.
  const nativeMode = document.documentElement.getAttribute("data-native-appearance");
  const nativePreference = isMode(nativeMode);
  let chosenMode = nativePreference ? nativeMode : "system";
  if (!nativePreference) {
    try {
      const remembered = window.localStorage.getItem(storageKey);
      if (isMode(remembered)) chosenMode = remembered;
    } catch (error) {
      // CSS still follows the device when storage cannot be read.
    }
  }
  document.documentElement.setAttribute("data-appearance", chosenMode);

  function initializeControl() {
    const select = document.getElementById("appearance");
    const wrapper = document.getElementById("appearance-control");
    const fallback = document.getElementById("appearance-fallback");
    const status = document.getElementById("appearance-status");

    // Leave unavailable controls and fallback help alone if markup is missing.
    if (!select || !wrapper) return;

    select.value = chosenMode;
    select.addEventListener("change", function () {
      // A native select supplies these enums; reject unexpected scripted values.
      if (!isMode(select.value)) {
        select.value = chosenMode;
        return;
      }

      chosenMode = select.value;
      document.documentElement.setAttribute("data-appearance", chosenMode);

      if (nativePreference) {
        const selectedMode = chosenMode;
        const csrf = document.getElementById("desktop-csrf");
        // Only an enum crosses this guarded local endpoint; no native bridge.
        const failed = function () {
          if (status && chosenMode === selectedMode) {
            status.textContent = "Appearance changed for this page, but the app could not remember it.";
          }
        };
        if (!csrf) { failed(); return; }
        window.fetch("/_desktop/appearance", {
          method: "POST", credentials: "same-origin",
          headers: { "Content-Type": "application/json", "X-CSRF-Token": csrf.content },
          body: JSON.stringify({ appearance: selectedMode })
        }).then(function (response) {
          if (!response.ok) { failed(); return; }
          if (status && chosenMode === selectedMode) status.textContent = "";
        }).catch(failed);
        return;
      }

      // Persist only explicit choices. Reacquire storage so a failed read does
      // not prevent a later successful write (or conceal a later write failure).
      try {
        window.localStorage.setItem(storageKey, chosenMode);
        if (status) status.textContent = "";
      } catch (error) {
        if (status) {
          status.textContent = "Appearance changed for this page, but your browser could not remember it.";
        }
      }
    });

    // Reveal only after a working handler is installed: progressive enhancement.
    select.disabled = false;
    wrapper.hidden = false;
    if (fallback) fallback.hidden = true;
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", initializeControl, { once: true });
  } else {
    initializeControl();
  }
})();
