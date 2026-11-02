// Observable browser-image states; executes the production script unchanged.
const fs = require('node:fs');
const vm = require('node:vm');
const input = JSON.parse(fs.readFileSync(0, 'utf8'));
const images = input.images.map(spec => ({
  complete: spec.complete, naturalWidth: spec.width, hidden: false, src: '/static/sentinel.jpg',
  handlers: {}, addEventListener(name, fn) { this.handlers[name] = fn; }
}));
const errors = [];
const context = {document: {querySelectorAll() { return images; }}};
try {
  vm.runInNewContext(fs.readFileSync(process.argv[2], 'utf8'), context);
  for (const index of input.fail || []) images[index].handlers.error();
} catch(error) { errors.push(error.message); }
process.stdout.write(JSON.stringify({errors, images: images.map(img => ({hidden:img.hidden,src:img.src}))}));
