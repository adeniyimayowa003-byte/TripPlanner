/* Test-only DOM/storage stand-ins. Theme decisions belong to the real script. */
"use strict";

const fs = require("node:fs");
const vm = require("node:vm");

const input = JSON.parse(fs.readFileSync(0, "utf8"));
const source = fs.readFileSync(process.argv[2], "utf8");
const operations = [];
const errors = [];
const missing = new Set(input.missing || []);
let readyState = input.readyState || "loading";
let headerAvailable = readyState !== "loading";
let fault = {
  getter: Boolean(input.getterThrows),
  read: Boolean(input.readThrows),
  write: Boolean(input.writeThrows),
};
const values = new Map([
  ["tripplanner.draft", "unrelated draft sentinel"],
  ["other.preference", "leave this alone"],
]);
if (Object.hasOwn(input, "stored") && input.stored !== null) {
  values.set("tripplanner.appearance", input.stored);
}

function log(kind, detail = {}) { operations.push({ kind, ...detail }); }

function makeElement(id, initial = {}) {
  const listeners = new Map();
  const attrs = { id, ...initial };
  let text = "";
  let value = id === "appearance" ? "system" : "unfinished trip field";
  let hidden = id === "appearance-control";
  let disabled = id === "appearance";
  if (hidden) attrs.hidden = "";
  if (disabled) attrs.disabled = "";
  function bindingCount() {
    return (elements.appearance?._listeners.get("change") || []).length;
  }
  const element = {
    id,
    tagName: id === "appearance" ? "SELECT" : "DIV",
    _listeners: listeners,
    getAttribute(name) { return Object.hasOwn(attrs, name) ? String(attrs[name]) : null; },
    hasAttribute(name) { return Object.hasOwn(attrs, name); },
    setAttribute(name, next) {
      attrs[name] = String(next);
      if (name === "hidden") hidden = true;
      if (name === "disabled") disabled = true;
      log("attribute", { id, name, value: String(next) });
    },
    removeAttribute(name) {
      delete attrs[name];
      if (name === "hidden") {
        hidden = false;
        log("availability", { id, property: "hidden", value: false, bindings: bindingCount() });
      }
      if (name === "disabled") {
        disabled = false;
        log("availability", { id, property: "disabled", value: false, bindings: bindingCount() });
      }
    },
    addEventListener(type, callback) {
      listeners.set(type, [...(listeners.get(type) || []), callback]);
      log("listener", { id, type });
    },
    removeEventListener(type, callback) {
      listeners.set(type, (listeners.get(type) || []).filter(item => item !== callback));
    },
    closest(selector) {
      if (selector === "form") return null;
      if (["#appearance-control", ".appearance-control", "[data-appearance-control]"].includes(selector)) {
        return missing.has("appearance-control") ? null : elements["appearance-control"];
      }
      return null;
    },
    focus() { log("focus", { id }); },
    blur() { log("blur", { id }); },
    submit() { log("submit", { id }); },
    requestSubmit() { log("submit", { id }); },
    scrollIntoView() { log("scroll", { id }); },
    appendChild() { log("html-mutation", { id }); },
    replaceChildren() { log("html-mutation", { id }); },
    classList: {
      add(...tokens) { log("class-mutation", { id, tokens }); },
      remove(...tokens) { log("class-mutation", { id, tokens }); },
      toggle(...tokens) { log("class-mutation", { id, tokens }); },
    },
  };
  Object.defineProperties(element, {
    value: {
      get() {
        if (!id.startsWith("appearance")) log("trip-field-read", { id });
        return value;
      },
      set(next) {
        value = next;
        log(id === "appearance" ? "selection" : "trip-field-write", { id, value: next });
      },
    },
    hidden: {
      get() { return hidden; },
      set(next) {
        hidden = Boolean(next);
        if (hidden) attrs.hidden = "";
        else delete attrs.hidden;
        log("availability", { id, property: "hidden", value: hidden, bindings: bindingCount() });
      },
    },
    disabled: {
      get() { return disabled; },
      set(next) {
        disabled = Boolean(next);
        if (disabled) attrs.disabled = "";
        else delete attrs.disabled;
        log("availability", { id, property: "disabled", value: disabled, bindings: bindingCount() });
      },
    },
    textContent: {
      get() { return text; },
      set(next) { text = String(next); log("text", { id, value: text }); },
    },
    innerHTML: {
      get() { return ""; },
      set(next) { log("html-mutation", { id, value: String(next) }); },
    },
    parentElement: { get() { return id === "appearance" ? elements["appearance-control"] : null; } },
  });
  element.dataset = new Proxy({}, {
    get(_target, key) {
      const attr = `data-${String(key).replace(/[A-Z]/g, item => `-${item.toLowerCase()}`)}`;
      return attrs[attr];
    },
    set(_target, key, next) {
      const attr = `data-${String(key).replace(/[A-Z]/g, item => `-${item.toLowerCase()}`)}`;
      element.setAttribute(attr, next);
      return true;
    },
  });
  return element;
}

const elements = {};
for (const id of ["html", "appearance", "appearance-control", "appearance-fallback", "appearance-status", "body", "budget", "trip_name", "trip-form"]) {
  elements[id] = makeElement(id);
}
const root = elements.html;
const documentListeners = new Map();
const windowListeners = new Map();
function getElement(id) {
  if (!id.startsWith("appearance") && id !== "html") log("unrelated-query", { id });
  return headerAvailable && !missing.has(id) ? elements[id] || null : null;
}
const document = {
  documentElement: root,
  body: elements.body,
  get readyState() { return readyState; },
  get activeElement() { return elements.appearance; },
  getElementById: getElement,
  querySelector(selector) {
    if (["html", ":root"].includes(selector)) return root;
    if (selector.startsWith("#")) return getElement(selector.slice(1));
    if (selector === "[data-appearance-control]" || selector === ".appearance-control") return getElement("appearance-control");
    log("unrelated-query", { selector });
    return null;
  },
  querySelectorAll(selector) { log("unrelated-query", { selector }); return []; },
  addEventListener(type, callback) {
    documentListeners.set(type, [...(documentListeners.get(type) || []), callback]);
    log("document-listener", { type });
  },
  removeEventListener(type, callback) {
    documentListeners.set(type, (documentListeners.get(type) || []).filter(item => item !== callback));
  },
  createElement(tag) { log("html-mutation", { tag }); return makeElement("created"); },
  write(...args) { log("html-mutation", { args }); },
};
const storage = {
  getItem(key) {
    log("storage-read", { key });
    if (fault.read) throw new Error("PRIVATE READ EXCEPTION DETAILS");
    return values.has(key) ? values.get(key) : null;
  },
  setItem(key, value) {
    log("storage-write", { key, value: String(value), failed: fault.write });
    if (fault.write) throw new Error("PRIVATE WRITE EXCEPTION DETAILS");
    values.set(String(key), String(value));
  },
  removeItem(key) { log("storage-remove", { key }); values.delete(key); },
  clear() { log("storage-clear"); values.clear(); },
};
const location = new Proxy({ href: "http://example.test/plan?unfinished=true" }, {
  set(_target, key, value) { log("navigation", { key, value }); return true; },
  get(target, key) {
    if (["assign", "replace", "reload"].includes(key)) return (...args) => log("navigation", { key, args });
    return target[key];
  },
});
const context = {
  document,
  console: { log() {}, warn() {}, error(...args) { log("console-error", { args }); } },
  navigator: { sendBeacon(...args) { log("network", { args }); } },
  addEventListener(type, callback) {
    windowListeners.set(type, [...(windowListeners.get(type) || []), callback]);
    log("window-listener", { type });
  },
  fetch(...args) { log("network", { args }); return Promise.reject(new Error("No network in test harness")); },
  XMLHttpRequest: function () { log("network", { api: "XMLHttpRequest" }); },
  open(...args) { log("navigation", { args }); },
  scrollTo(...args) { log("scroll", { args }); },
  scrollBy(...args) { log("scroll", { args }); },
  setTimeout() { throw new Error("Use DOMContentLoaded rather than an unbounded timer in appearance initialization."); },
  location,
};
Object.defineProperty(context, "location", {
  get() { return location; },
  set(value) { log("navigation", { key: "window.location", value }); },
});
Object.defineProperty(document, "location", {
  get() { return location; },
  set(value) { log("navigation", { key: "document.location", value }); },
});
Object.defineProperty(context, "localStorage", {
  get() {
    log("storage-getter", { failed: fault.getter });
    if (fault.getter) throw new Error("PRIVATE GETTER EXCEPTION DETAILS");
    return storage;
  },
});
// A separate ordinary window stand-in preserves throwing getter semantics.
// Node's contextified-global proxy otherwise suppresses a host accessor error.
context.window = Object.create(context);
context.window.window = context.window;
context.window.self = context.window;
context.self = context.window;
vm.createContext(context);
const snapshots = [];
function take(stage) {
  snapshots.push({
    stage,
    mode: root.getAttribute("data-appearance"),
    selected: elements.appearance.value,
    disabled: elements.appearance.disabled,
    hidden: elements["appearance-control"].hidden,
    fallbackHidden: elements["appearance-fallback"].hidden,
    status: elements["appearance-status"].textContent,
    bindings: (elements.appearance._listeners.get("change") || []).length,
    operations: operations.length,
    values: Object.fromEntries(values),
  });
}
function bounded(code, filename) {
  try { vm.runInContext(code, context, { timeout: 300, filename }); }
  catch (error) { errors.push({ stage: filename, message: error.message, name: error.name }); }
}
bounded(source, process.argv[2]);
take("early");
if (input.domReady !== false && readyState === "loading") {
  headerAvailable = true;
  readyState = "interactive";
  context.__readyCallbacks = documentListeners.get("DOMContentLoaded") || [];
  context.__readyWindowCallbacks = windowListeners.get("DOMContentLoaded") || [];
  bounded("for (const callback of __readyCallbacks) callback({ type: 'DOMContentLoaded', target: document }); for (const callback of __readyWindowCallbacks) callback({ type: 'DOMContentLoaded', target: document });", "DOMContentLoaded");
}
take("ready");
for (let index = 0; index < (input.steps || []).length; index++) {
  const step = input.steps[index];
  if (step.fault) fault = { ...fault, ...step.fault };
  if (Object.hasOwn(step, "select")) {
    elements.appearance.value = step.select;
    context.__changeCallbacks = elements.appearance._listeners.get("change") || [];
    context.__changeEvent = { type: "change", target: elements.appearance, currentTarget: elements.appearance };
    bounded("for (const callback of __changeCallbacks) callback.call(__changeEvent.target, __changeEvent);", `change-${index}`);
  }
  take(`step-${index}`);
}
process.stdout.write(JSON.stringify({ snapshots, operations, errors }));
