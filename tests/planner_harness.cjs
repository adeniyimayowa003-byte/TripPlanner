/* Execute the real planner asset with small observable DOM stand-ins. */
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
class Element {
  constructor(tag = 'div', value = '') { this.tagName = tag.toUpperCase(); this.value = value; this.children = []; this.attrs = {}; this.listeners = {}; this.checked = false; this.disabled = false; this._text = ''; }
  get textContent() { return this._text + this.children.map(x => x.textContent).join(''); }
  set textContent(value) { this._text = String(value); this.children = []; }
  setAttribute(key, value) { this.attrs[key] = String(value); }
  getAttribute(key) { return this.attrs[key] ?? null; }
  removeAttribute(key) { delete this.attrs[key]; }
  appendChild(child) { this.children.push(child); return child; }
  append(...children) { this.children.push(...children); }
  replaceChildren(...children) { this.children = children; this._text = ''; }
  addEventListener(event, fn) { (this.listeners[event] ||= []).push(fn); }
  querySelectorAll(selector) {
    const all = this.children.flatMap(x => [x, ...x.querySelectorAll(selector)]);
    if (selector.includes('input')) return all.filter(x => x.tagName === 'INPUT' && (!selector.includes(':checked') || x.checked));
    return all.filter(x => x.tagName === 'OPTION');
  }
  get options() { return this.children; }
}
const ids = ['destination','days','budget','daily-allowance','preview-help','budget-help','budget-currency','preview-currency','interest-options','pace','destination-data','currency-change-help','currency_context'];
const nodes = Object.fromEntries(ids.map(id => [id, new Element()]));
nodes.destination.value = input.destination || '';
nodes.days.value = input.days || '3'; nodes.budget.value = input.budget || '';
nodes.pace.value = input.pace || '';
nodes.currency_context.value = 'signed-context-sentinel';
nodes['destination-data'].textContent = JSON.stringify(input.config || {});
for (const interest of input.interests || []) { const el = new Element('input', interest); el.checked = true; nodes['interest-options'].appendChild(el); }
if (input.pending) nodes['confirm-currency-change'] = new Element('input');
for (const id of input.missing || []) delete nodes[id];
const document = { getElementById: id => nodes[id] || null, createElement: tag => new Element(tag) };
const errors = []; const forbidden = () => { throw new Error('Planner must not use network or storage'); };
const context = vm.createContext({document, console, fetch:forbidden, localStorage:{setItem:forbidden,getItem:forbidden}, window:{location:{assign:forbidden}}});
try { vm.runInContext(fs.readFileSync(process.argv[2], 'utf8'), context, {timeout:1000}); } catch (error) { errors.push(String(error)); }
for (const action of input.actions || []) {
  const node = nodes[action.id]; if (!node) throw new Error('Missing action node');
  if ('value' in action) node.value = action.value;
  if ('checked' in action) node.checked = action.checked;
  for (const fn of node.listeners[action.event || 'input'] || []) { try { fn(); } catch(error) { errors.push(String(error)); } }
}
process.stdout.write(JSON.stringify({errors, preview:nodes['daily-allowance']?.textContent, help:nodes['preview-help']?.textContent,
  budget:nodes.budget?.value, attrs:nodes.budget?.attrs, currency:nodes['budget-currency']?.textContent,
  notice:nodes['currency-change-help']?.textContent, token:nodes.currency_context?.value,
  interests:nodes['interest-options']?.querySelectorAll('input').map(x=>({value:x.value,checked:x.checked})), pace:nodes.pace?.value}));
