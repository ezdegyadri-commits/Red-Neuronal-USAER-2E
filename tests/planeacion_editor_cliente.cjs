// Contrato del cliente con DOM y reloj ficticios: sin navegador ni datos reales.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../ui/planeacion_papel_component/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function fixture(backup) {
  const nodes = new Map(), listeners = {}, timers = new Map(), messages = [], cache = new Map(backup || []);
  let sequence = 0;
  class Element {
    constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.handlers = {}; this._text = ''; }
    set id(v) { this._id = v; nodes.set(v, this); } get id() { return this._id; }
    set textContent(v) { this._text = v; this.children = []; } get textContent() { return this._text + this.children.map(c => c.textContent || '').join(''); }
    get innerText() { return this.textContent; }
    append(...items) { for (const c of items) { this.children.push(c); if (c && typeof c === 'object') c.parentElement = this; } }
    replaceChildren() { this.children = []; this._text = ''; }
    setAttribute(k, v) { this[k] = v; }
    addEventListener(type, fn) { this.handlers[type] = fn; }
    querySelectorAll(selector) {
      const all = this.children.flatMap(c => c instanceof Element ? [c, ...c.querySelectorAll('*')] : []);
      return all.filter(c => selector === '*' || selector === '[data-cell]' && c.dataset.cell || selector.toUpperCase() === c.tagName);
    }
    focus() {} scrollIntoView() {} click() { this.handlers.click?.({}); }
  }
  const root = new Element('article'); root.id = 'page';
  const tools = new Element('div'); tools.id = 'tools';
  const status = new Element('div'); status.id = 'status';
  const parent = { postMessage: m => messages.push(m) };
  const document = { referrer: 'https://usaer.test/', activeElement: null, documentElement: { scrollHeight: 220 },
    getElementById: id => nodes.get(id), createElement: tag => new Element(tag) };
  const context = { document, parent, location: { origin: 'https://usaer.test' }, URL, Blob, console,
    sessionStorage: { getItem: k => cache.get(k) || null, setItem: (k,v) => cache.set(k,v), removeItem: k => cache.delete(k) },
    setTimeout: (fn, delay) => { const id = ++sequence; timers.set(id, { fn, delay }); return id; }, clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => { const id = ++sequence; timers.set(id, { fn, delay, interval: true }); return id; }, clearInterval: id => timers.delete(id),
    queueMicrotask: fn => fn(), ResizeObserver: class { observe() {} },
    window: { addEventListener: (type, fn) => { listeners[type] = fn; } } };
  vm.runInNewContext(script, context);
  function render(hoja, extra = {}, source = parent) { listeners.message({source, origin:'https://usaer.test', data:{type:'streamlit:render', args:{hoja,...extra}}}); }
  function tick(delay) { const pending = [...timers]; for (const [id,t] of pending) if (t.delay === delay && timers.has(id)) { if (!t.interval) timers.delete(id); t.fn(); } }
  function input(value, id='c0') { const e=nodes.get('celda-'+id); e.textContent=value; e.handlers.input({}); root.handlers.input?.({}); }
  const events = () => messages.filter(m => m.type === 'streamlit:setComponentValue').map(m => m.value);
  return { nodes, root, tools, status, render, tick, input, events, messages, cache, listeners };
}
function hoja(value='', fingerprint='base') {
  const a={id:'c0',value,label:'Actividad',editable:true}, b={id:'c1',value:'Sin valorar',label:'Valoración',editable:true,opciones:['Sin valorar','Logrado']};
  return {documento:'ficticio',cache_id:'ficticio',huella:fingerprint,titulo:'Formato ficticio',header:[['Escuela ficticia']],
    tables:[{id:'actividades',headers:['Actividad','Valoración'],rows:[[a,b]]}],textos:[],
    cells:{c0:{...a,target:['tabla','actividad',0,'texto']},c1:{...b,target:['escala',0,'Valoración']}}};
}

// El inicio no queda invisible y repite el saludo hasta recibir el formato.
{
  const f=fixture(); assert.match(html,/Preparando tu formato/);
  assert.ok(f.messages.some(m=>m.type==='streamlit:setFrameHeight'&&m.height>=180));
  f.tick(5000); assert.equal(f.messages.filter(m=>m.type==='streamlit:componentReady').length,2);
  f.render(hoja(),{},{}); assert.equal(f.tools.children.length,0); // Fuente ajena rechazada.
  f.render(hoja(),{guardado:'ayer'}); f.tick(5000);
  assert.equal(f.messages.filter(m=>m.type==='streamlit:componentReady').length,2);
  assert.ok(f.tools.children.some(b=>b.textContent==='Guardar planeación'));
}
// Un acuse viejo no libera el envío. La espera permite editar y reintenta el MISMO nonce.
{
  const f=fixture(); f.render(hoja(),{guardado:'ayer'}); f.input('Primera edición'); f.tick(4000);
  const first=f.events()[0]; assert.equal(f.nodes.get('celda-c0').contentEditable,'false');
  f.render(hoja(),{aceptado:true,aceptado_nonce:'otro-envío',guardado:'ayer'});
  assert.equal(f.nodes.get('celda-c0').contentEditable,'false');
  f.tick(15000); assert.equal(f.events()[1].nonce,first.nonce);
  assert.equal(f.nodes.get('celda-c0').contentEditable,'true');
  f.input('Texto escrito mientras esperaba'); f.tick(4000); assert.equal(f.events().length,2);
  f.render(hoja('Primera edición','segunda'),{aceptado_nonce:first.nonce,guardado:'ahora'});
  assert.equal(f.nodes.get('celda-c0').innerText,'Texto escrito mientras esperaba');
  assert.ok(f.cache.has('usaer-hoja:ficticio'));
  f.tick(4000); const next=f.events().at(-1);
  assert.notEqual(next.nonce,first.nonce); assert.equal(next.cambios.c0,'Texto escrito mientras esperaba');
  f.render(hoja(next.cambios.c0,'tercera'),{aceptado_nonce:next.nonce,guardado:''});
  assert.ok(f.cache.has('usaer-hoja:ficticio')); // Recibido NO significa persistido.
  let warned=false; f.listeners.beforeunload({preventDefault(){warned=true;}}); assert.equal(warned,true);
  f.render(hoja(next.cambios.c0,'tercera'),{aceptado_nonce:next.nonce,guardado:'confirmado'});
  assert.equal(f.cache.has('usaer-hoja:ficticio'),false);
  let prevented=false; f.listeners.beforeunload({preventDefault(){prevented=true;}}); assert.equal(prevented,false);
}
// Rechazos de validación no congelan el editor ni generan bucles de escritura.
{
  const f=fixture(); f.render(hoja()); f.input('Texto conservado'); f.tick(4000);
  const nonce=f.events()[0].nonce;
  f.render(hoja(),{rechazado:nonce,error:'Otra sesión cambió la hoja.'});
  assert.equal(f.nodes.get('celda-c0').contentEditable,'true'); assert.match(f.status.textContent,/conserv|sigue/);
  f.render(hoja(),{rechazado:nonce}); f.tick(15000); f.tick(4000);
  assert.equal(f.events().length,1); assert.ok(f.cache.has('usaer-hoja:ficticio'));
}
// La valoración restaurada se aplica al valor del selector, no a sus opciones.
{
  const f=fixture([['usaer-hoja:ficticio',JSON.stringify({huella:'base',cambios:{c1:'Logrado'}})]]);
  f.render(hoja()); assert.equal(f.nodes.get('celda-c1').value,'Logrado');
}
// Nunca se elimina ni aplica a ciegas un respaldo de una revisión diferente.
{
  const backup=JSON.stringify({huella:'otra',cambios:{c0:'No perder'}});
  const f=fixture([['usaer-hoja:ficticio',backup]]); f.render(hoja(),{guardado:'ahora'});
  assert.equal(f.cache.get('usaer-hoja:ficticio'),backup); assert.match(f.status.textContent,/otra revisión/);
}
console.log('Editor: 5 escenarios de carga, acuse, espera, rechazo y respaldo aprobados.');
