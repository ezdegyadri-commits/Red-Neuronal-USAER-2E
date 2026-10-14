// Prueba unitaria del protocolo del componente; no controla un navegador real.
import fs from 'node:fs';
import vm from 'node:vm';
import assert from 'node:assert/strict';
class Element {
  constructor(tag){this.tag=tag;this.children=[];this.dataset={};this.events={};this.style={};this.textContent='';this.innerText='';}
  append(...items){this.children.push(...items)}
  replaceChildren(...items){this.children=items}
  setAttribute(k,v){this[k]=v}
  addEventListener(k,fn){this.events[k]=fn}
  get lastChild(){return this.children.at(-1)}
  get isContentEditable(){return this.contentEditable==='true'}
  querySelectorAll(){return this.children.flatMap(c=>[c,...c.querySelectorAll()]).filter(c=>c.dataset.cell)}
  focus(){}
}
const roots={page:new Element('article'),tools:new Element('div'),status:new Element('div')};
const messages=[],listeners={};let timer;
const parent={postMessage:(message,origin)=>messages.push({message,origin})};
const document={referrer:'http://localhost:8607/',documentElement:{scrollHeight:500},activeElement:null,getElementById:k=>roots[k],createElement:tag=>new Element(tag)};
const window={addEventListener:(name,fn)=>listeners[name]=fn};
const context={document,window,parent,location:{origin:'http://localhost:8607'},URL,
  ResizeObserver:class{observe(){}},setTimeout:fn=>{timer=fn;return 1},clearTimeout:()=>{},queueMicrotask:fn=>fn(),confirm:()=>true};
vm.runInNewContext(fs.readFileSync('ui/planeacion_papel_component/index.html','utf8').match(/<script>([\s\S]*?)<\/script>/)[1],context);
const spec=(huella,value='')=>({documento:'ficticio',huella,titulo:'Formato ficticio',header:[['Zona','Servicio']],
  tables:[{id:'dosificacion',headers:['Actividades'],rows:[[{id:'c0',label:'Actividades',value,editable:true}]],add:false,delete:false}],textos:[],cells:{c0:{editable:true}},firma:'Especialista',vobo:'Dirección'});
const receive=(hoja,aceptado=false)=>listeners.message({source:parent,origin:'http://localhost:8607',data:{type:'streamlit:render',args:{hoja,aceptado}}});
listeners.message({source:{},origin:'http://localhost:8607',data:{type:'streamlit:render',args:{hoja:spec('ataque')}}});
assert.equal(roots.page.children.length,0);
receive(spec('h1','<script>texto literal</script>'));
let cell=roots.page.querySelectorAll()[0];assert.equal(cell.textContent,'<script>texto literal</script>');
cell.innerText='Actividad ficticia editada';cell.events.input();timer();
const guardar=roots.tools.children.find(e=>e.textContent==='Guardar cambios de la hoja');guardar.events.click();
const sent=()=>messages.filter(m=>m.message.type==='streamlit:setComponentValue');
assert.equal(sent().length,1);assert.equal(sent()[0].message.value.accion,'autoguardar');
receive(spec('h2','Actividad ficticia editada'),true);
assert.equal(sent().length,2);assert.equal(sent()[1].message.value.accion,'guardar');
assert.equal(sent()[1].message.value.huella,'h2');assert.equal(Object.keys(sent()[1].message.value.cambios).length,0);
receive(spec('h3','Actividad ficticia editada'),true);
cell=roots.page.querySelectorAll()[0];cell.innerText='No perder este texto';cell.events.input();
receive(spec('version-ajena','No sustituir'),false);
assert.equal(roots.page.querySelectorAll()[0].innerText,'No perder este texto');
assert.match(roots.status.textContent,/Respalda/);
let warned=false;listeners.beforeunload({preventDefault:()=>{warned=true}});assert.equal(warned,true);
assert.equal(messages.every(m=>m.origin==='http://localhost:8607'),true);
console.log('Editor de papel: origen, texto literal, autoguardado, guardado en cola, versión obsoleta y aviso de salida correctos.');
