/* Progressive enhancement: server validation and signed review remain authoritative. */
(() => {
  "use strict";
  const get = id => document.getElementById(id);
  const destination = get("destination"), days = get("days"), budget = get("budget");
  const preview = get("daily-allowance"), help = get("preview-help"), data = get("destination-data");
  if (!destination || !days || !budget || !preview || !help || !data) return;
  let config;
  try { config = JSON.parse(data.textContent); } catch { return; }
  const interests = get("interest-options"), pace = get("pace"), confirmation = get("confirm-currency-change");
  let previous = config[destination.value]?.currency || null;
  let requiresReview = Boolean(confirmation), needsServerReview = false;
  function text(id, value) { const node = get(id); if (node) node.textContent = value; }
  function updatePreview() {
    const city = config[destination.value];
    preview.textContent = "—";
    if (!city) { help.textContent = "Choose a destination, then enter your days and allowance."; return; }
    const factor = city.precision === 0 ? 1 : 100;
    const raw = budget.value.trim(), rawDays = days.value.trim();
    const valid = (factor === 1 ? /^[0-9]+$/ : /^[0-9]+(?:\.[0-9]{1,2})?$/).test(raw);
    const [whole, fraction = ""] = raw.split(".");
    const minor = valid ? Number(whole) * factor + (factor === 1 ? 0 : Number(fraction.padEnd(2,"0"))) : 0;
    const count = /^[0-9]+$/.test(rawDays) ? Number(rawDays) : 0;
    if (needsServerReview || (requiresReview && !confirmation?.checked)) {
      help.textContent = "Review your amount in the new currency before continuing."; return;
    }
    if (!valid || !Number.isSafeInteger(minor) || minor < 1 || minor > city.maximum_minor || !Number.isInteger(count) || count < 1 || count > 14) {
      help.textContent = "Enter valid days and an allowance in " + city.currency + "."; return;
    }
    const daily = Math.floor(minor / count) + (2 * (minor % count) >= count ? 1 : 0);
    preview.textContent = city.currency + " " + (factor === 1 ? String(daily) : String(Math.floor(daily/100)) + "." + String(daily%100).padStart(2,"0"));
    help.textContent = "Approximate display only. Each idea is checked against your exact allowance after submission.";
  }
  function updateOptions(city) {
    if (interests) {
      const selected = new Set(Array.from(interests.querySelectorAll("input:checked"), node => node.value));
      interests.replaceChildren();
      for (const [index, value] of city.interests.entries()) {
        const label = document.createElement("label"), input = document.createElement("input"), span = document.createElement("span");
        label.className = "interest-option"; input.type = "checkbox"; input.name = "interests";
        input.id = "interest-" + (index+1); input.value = value; input.checked = selected.has(value);
        label.setAttribute("for", input.id); span.textContent = value.replaceAll("-"," ");
        label.append(input,span); interests.appendChild(label);
      }
    }
    if (pace) {
      const selected = pace.value; pace.replaceChildren();
      for (const value of ["", ...city.paces]) {
        const option = document.createElement("option"); option.value = value; option.textContent = value || "No preference";
        pace.appendChild(option);
      }
      pace.value = city.paces.includes(selected) ? selected : "";
    }
  }
  function changeDestination() {
    const city = config[destination.value];
    if (!city) { updatePreview(); return; }
    if (previous && previous !== city.currency && budget.value.trim()) {
      requiresReview = true; needsServerReview = true;
      if (confirmation) { confirmation.checked = false; confirmation.disabled = true; }
      text("currency-change-help", "Currency changed to " + city.currency + ". Review the amount on submission; no conversion is performed. Unsupported interests and pace choices have been cleared.");
    }
    previous = city.currency;
    const whole = city.precision === 0;
    for (const [key,value] of Object.entries({min:whole?"1":"0.01",step:whole?"1":"0.01",max:String(city.maximum_minor/(whole?1:100)),inputmode:whole?"numeric":"decimal"})) budget.setAttribute(key,value);
    text("budget-currency",city.currency); text("preview-currency",city.currency);
    text("budget-help","Total " + city.currency + " per person for all days. " + (whole ? "Use whole amounts." : "Use up to two decimal places."));
    updateOptions(city); updatePreview();
  }
  destination.addEventListener("change",changeDestination);
  days.addEventListener("input",updatePreview); budget.addEventListener("input",updatePreview);
  if (confirmation) confirmation.addEventListener("change",updatePreview);
  updatePreview();
})();
