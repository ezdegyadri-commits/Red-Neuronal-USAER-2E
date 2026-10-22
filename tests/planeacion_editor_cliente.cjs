// Contrato del cliente con DOM y reloj ficticios: sin navegador ni datos reales.
const assert = require('node:assert/strict');
const fs = require('node:fs');
const vm = require('node:vm');
const path = require('node:path');
const html = fs.readFileSync(path.join(__dirname, '../ui/planeacion_papel_component/index.html'), 'utf8');
const script = html.match(/<script>([\s\S]*?)<\/script>/)[1];
function fixture(backup, referrer='https://usaer.test/', native=false) {
  const nodes = new Map(), listeners = {}, timers = new Map(), messages = [], targets = [], cache = new Map(backup || []);
  let sequence = 0;
  class Element {
    constructor(tag) { this.tagName = tag.toUpperCase(); this.children = []; this.dataset = {}; this.style = {}; this.handlers = {}; this._text = ''; }
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
  const parent = { postMessage: (m,target) => {messages.push(m);targets.push({type:m.type,target});} };
  const document = { referrer, activeElement: null, documentElement: { scrollHeight: 220 },
    getElementById: id => nodes.get(id), createElement: tag => new Element(tag) };
  const context = { document, parent, location: { origin: 'https://usaer.test' }, URL, Blob, console,
    sessionStorage: { getItem: k => cache.get(k) || null, setItem: (k,v) => cache.set(k,v), removeItem: k => cache.delete(k) },
    setTimeout: (fn, delay) => { const id = ++sequence; timers.set(id, { fn, delay }); return id; }, clearTimeout: id => timers.delete(id),
    setInterval: (fn, delay) => { const id = ++sequence; timers.set(id, { fn, delay, interval: true }); return id; }, clearInterval: id => timers.delete(id),
    queueMicrotask: fn => fn(), ResizeObserver: class { observe() {} disconnect() {} },
    window: { addEventListener: (type, fn) => { listeners[type] = fn; },removeEventListener: type => { delete listeners[type]; } } };
  let component,host,cleanup;
  const cleanups=[];
  if(native){
    host={querySelector: selector=>nodes.get(selector.slice(1)),activeElement:null};
    component={parentElement:host,data:{},setStateValue:(name,value)=>messages.push({type:'streamlit:setComponentValue',value})};
    const adapter=fs.readFileSync(path.join(__dirname,'../ui/planeacion_papel_component/native.js'),'utf8')
      .replace('export default function mount','function mount').replace('/* USAER_RENDERER */',script);
    vm.runInNewContext(adapter+'\nthis.mountNative=mount;',context);
    cleanup=context.mountNative(component);cleanups.push(cleanup);
  }else vm.runInNewContext(script, context);
  function render(hoja, extra = {}, source = parent, origin='https://usaer.test') {
    if(native){component.data={hoja,...extra};cleanup=context.mountNative(component);cleanups.push(cleanup)}
    else listeners.message({source, origin, data:{type:'streamlit:render', args:{hoja,...extra}}});
  }
  function tick(delay) { const pending = [...timers]; for (const [id,t] of pending) if (t.delay === delay && timers.has(id)) { if (!t.interval) timers.delete(id); t.fn(); } }
  function input(value, id='c0') { const e=nodes.get('celda-'+id); e.textContent=value; e.handlers.input({}); root.handlers.input?.({}); }
  const events = () => messages.filter(m => m.type === 'streamlit:setComponentValue').map(m => m.value);
  return { nodes, root, tools, status, render, tick, input, events, messages, targets, cache, listeners, parent,
    dispose:()=>cleanup?.(),cleanups,timers };
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
// Barra breve y acciones inequívocas: guardar no es ayuda y descargar recoge el texto.
{
  const f=fixture();f.render(hoja());
  assert.deepEqual(f.tools.children.filter(e=>e.tagName==='BUTTON'&&e.className!=='navigation').map(e=>e.textContent),['Ayúdame a planear','Guardar planeación','Descargar']);
  assert.ok(f.tools.children.some(e=>e.tagName==='DETAILS'));
  f.input('Texto aún no enviado');f.tools.children.find(e=>e.textContent==='Descargar').click();
  assert.equal(f.events()[0].accion,'pdf');assert.equal(f.events()[0].cambios.c0,'Texto aún no enviado');
}
// Un acuse viejo no libera el envío. La espera permite editar y reintenta el MISMO nonce.
{
  const f=fixture(); f.render(hoja(),{guardado:'ayer'}); f.input('Primera edición'); f.tick(4000);
  const first=f.events()[0]; assert.equal(f.nodes.get('celda-c0').contentEditable,'true');
  f.render(hoja(),{aceptado:true,aceptado_nonce:'otro-envío',guardado:'ayer'});
  assert.equal(f.nodes.get('celda-c0').contentEditable,'true');
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
// Un proxy o referrer ausente no decide el destino de las ediciones.
for(const referrer of ['', 'https://contenedor.distinto.test/']) {
  const f=fixture(undefined,referrer);
  assert.equal(f.targets[0].target,'*');
  assert.ok(f.targets.every(t=>t.type!=='streamlit:setComponentValue'));
  f.render(hoja(),{},f.parent,'null');assert.equal(f.tools.children.length,0);
  f.render(hoja(),{},f.parent,'https://usaer.test');
  f.input('Solo al padre autenticado por origen');f.tick(4000);
  assert.equal(f.targets.find(t=>t.type==='streamlit:setComponentValue').target,'https://usaer.test');
  const count=f.tools.children.length;
  f.render(hoja('No aceptar','ajena'),{},f.parent,'https://otro.test');
  assert.equal(f.tools.children.length,count);
  assert.equal(f.nodes.get('celda-c0').innerText,'Solo al padre autenticado por origen');
}
// El adaptador nativo usa exactamente la misma hoja, pero sin marco ni handshake externo.
{
  const f=fixture(undefined,'https://contenedor.distinto.test/',true);
  f.render(hoja(),{guardado:'antes'});
  const controls=f.tools.children.length;
  f.input('Edición del formato integrado');f.tick(4000);
  assert.equal(f.events().length,1);const event=f.events()[0];
  f.render(hoja('Edición del formato integrado','nativa'),{aceptado_nonce:event.nonce,guardado:'confirmado'});
  assert.match(f.status.textContent,/Guardado confirmado/);
  assert.equal(f.nodes.get('celda-c0').innerText,'Edición del formato integrado');
  f.render(hoja('Edición del formato integrado','nativa'),{guardado:'confirmado'});
  assert.equal(f.tools.children.length,controls);assert.equal(f.events().length,1);
  assert.equal(f.cache.has('usaer-hoja:ficticio'),false);
  f.dispose();assert.equal(f.timers.size,0);assert.equal(f.listeners.beforeunload,undefined);
}
// Cleanup tardío de un efecto anterior no desmonta el editor actualizado.
{
  const f=fixture(undefined,'https://usaer.test/',true);
  f.render(hoja(),{guardado:'antes'});
  const nodo=f.nodes.get('celda-c0');f.input('Sigo escribiendo');
  f.render(hoja(),{guardado:'antes'});
  for(const cleanup of f.cleanups.slice(0,-1))cleanup();
  assert.equal(f.nodes.get('celda-c0'),nodo);
  assert.equal(nodo.innerText,'Sigo escribiendo');
  f.tick(4000);assert.equal(f.events().length,1);
  assert.equal(f.events()[0].cambios.c0,'Sigo escribiendo');
  assert.ok(f.cache.has('usaer-hoja:ficticio'));
  f.dispose();assert.equal(f.timers.size,0);
}
// Un aporte de otra área se actualiza durante el envío, sin sustituir el nodo
// activo ni el texto más reciente. Dos pestañas no comparten respaldo.
{
  const f=fixture(), otra=fixture();
  function compartida(apoyo){
    const spec=hoja();const c={id:'c2',value:apoyo,label:'Aprendizaje',editable:false,target:null};
    spec.cells.c2=c;spec.tables[0].rows[0].push(c);return spec;
  }
  f.render(compartida('Texto de apoyo inicial'));
  otra.render(compartida('Texto de apoyo inicial'));
  const nodo=f.nodes.get('celda-c0');
  f.input('Mi actividad');f.tick(4000);const envio=f.events()[0];
  f.input('Mi actividad mientras guarda');
  const actualizada=compartida('Apoyo acaba de guardar');actualizada.header[0][0]='Docente regular actualizado';
  f.render(actualizada,{guardado:'guardado de apoyo'});
  assert.equal(f.nodes.get('celda-c0'),nodo);
  assert.equal(nodo.innerText,'Mi actividad mientras guarda');
  assert.equal(f.nodes.get('celda-c2').innerText,'Apoyo acaba de guardar');
  assert.equal(f.nodes.get('encabezado-0-0').innerText,'Docente regular actualizado');
  assert.ok(f.cache.has('usaer-hoja:ficticio'));assert.equal(otra.cache.size,0);
  const confirmado=compartida('Apoyo acaba de guardar');confirmado.huella='propio-guardado';
  f.render(confirmado,{aceptado_nonce:envio.nonce,guardado:'mi guardado'});
  assert.equal(f.nodes.get('celda-c0'),nodo);
  assert.equal(nodo.innerText,'Mi actividad mientras guarda');
}
// Salir es una operación protegida: no se cambia documento durante su envío.
{
  const f=fixture();f.render(hoja());f.input('Antes de salir');
  f.tools.children.find(b=>b.textContent==='Regresar al inicio del módulo').click();
  assert.equal(f.events()[0].accion,'inicio');
  assert.equal(f.events()[0].cambios.c0,'Antes de salir');
  assert.equal(f.nodes.get('celda-c0').contentEditable,'false');
  f.tick(15000);assert.equal(f.events()[1].nonce,f.events()[0].nonce);
  assert.ok(f.cache.has('usaer-hoja:ficticio'));
}
// Un traslado/baja nunca reasigna el texto en vuelo al alumno que ocupa su fila.
{
  const f=fixture();const inicial=hoja();inicial.cells.c0.destinatario='A1';
  f.render(inicial);f.input('Actividad de A1');f.tick(4000);const envio=f.events()[0];
  f.input('Texto posterior de A1');const respaldo=f.cache.get('usaer-hoja:ficticio');
  const siguiente=hoja('Actividad de A2','otra-matricula');siguiente.cells.c0.destinatario='A2';
  f.render(siguiente,{aceptado_nonce:envio.nonce,guardado:'confirmado'});
  assert.equal(f.nodes.get('celda-c0').innerText,'Actividad de A2');
  assert.equal(f.cache.get('usaer-hoja:ficticio'),respaldo);
}
// Cerrar sesión antes de los cuatro segundos transmite el texto y detiene el
// clic. Sólo el acuse de guardado del servidor permite continuar el cierre.
{
  const f=fixture(undefined,undefined,true);f.render(hoja());f.input('Últimas palabras antes de cerrar');
  let bloqueado=0;
  const cerrar={textContent:'Cerrar sesión'};
  const evento=()=>({target:{closest:()=>cerrar},preventDefault:()=>bloqueado++,stopImmediatePropagation:()=>bloqueado++});
  f.listeners.click(evento());
  assert.equal(bloqueado,2);
  assert.equal(f.events()[0].accion,'guardar');assert.equal(f.events()[0].cambios.c0,'Últimas palabras antes de cerrar');
  const respaldo=JSON.parse(f.cache.get('usaer-hoja:ficticio'));
  assert.equal(respaldo.tipo,'usaer-texto-pendiente-v2');assert.equal(respaldo.celdas[0].valor,'Últimas palabras antes de cerrar');
  f.render(hoja('Últimas palabras antes de cerrar','nueva'),{aceptado_nonce:f.events()[0].nonce,guardado:'confirmado'});
  bloqueado=0;f.listeners.click(evento());assert.equal(bloqueado,0);
  f.dispose();assert.equal(f.listeners.click,undefined);
}
// La fecha conserva el calendario y el contrato de autoguardado dentro de su caja.
{
  const f=fixture(),h=hoja();
  const fecha={id:'c0',value:'23/10/2026',fecha_iso:'2026-10-23',tipo:'fecha',label:'Fecha derivación',editable:true};
  h.tables[0].rows[0][0]=fecha;h.cells.c0={...fecha,target:['guia','A1','Fecha derivación']};
  f.render(h);
  const input=f.nodes.get('celda-c0');
  assert.equal(input.parentElement.className,'date-cell');assert.equal(input.type,'date');
  assert.equal(input.value,'2026-10-23');input.value='2026-10-24';input.handlers.change();f.tick(1000);
  assert.equal(f.events()[0].cambios.c0,'2026-10-24');
  assert.match(html,/\.date-cell input\[type=date\][^{]*\{[^}]*min-width:0/);
}
console.log('Editor: escritura no bloqueante, sincronización por área, respaldo, fecha y navegación protegida aprobados.');
