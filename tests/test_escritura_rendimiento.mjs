import fs from 'node:fs';
import assert from 'node:assert/strict';
const source=fs.readFileSync('ui/escritura.js','utf8');
const {default:mount}=await import('data:text/javascript;base64,'+Buffer.from(source).toString('base64'));
let scans=0,observe,frames=new Map(),serial=0;
const nodes=new Map();
class Element {
  constructor(){this.style={};this.children=[];}
  set id(value){this._id=value;nodes.set(value,this);} get id(){return this._id;}
  append(...items){this.children.push(...items);}
  addEventListener(){}
  remove(){nodes.delete(this.id);for(const child of this.children)child.remove?.();}
}
globalThis.document={body:new Element(),getElementById:id=>nodes.get(id)||null,
  createElement:()=>new Element(),querySelectorAll(){scans++;return [];}};
globalThis.MutationObserver=class {constructor(fn){observe=fn;}observe(){}disconnect(){}};
globalThis.requestAnimationFrame=fn=>{frames.set(++serial,fn);return serial;};
globalThis.cancelAnimationFrame=id=>frames.delete(id);
const events=[],host={};
const component={parentElement:host,data:{words:['usaer','planeación']},setStateValue:(k,v)=>events.push(v)};
let cleanup=mount(component);
assert.ok(nodes.has('usaer-master-spellcheck-wrap'));
assert.equal(events.at(-1).tipo,'diccionario_listo');
const dictionary=globalThis.__usaer_diccionario_es_v1;
for(let i=0;i<200;i++)observe();
assert.equal(frames.size,1);assert.equal(scans,1);
for(const fn of frames.values())fn();frames.clear();assert.equal(scans,2);
cleanup();
assert.ok(!nodes.has('usaer-master-spellcheck-wrap'));
component.data={};cleanup=mount(component);
assert.equal(globalThis.__usaer_diccionario_es_v1,dictionary);assert(dictionary.known.has('planeación'));
cleanup();delete globalThis.__usaer_diccionario_es_v1;
mount(component);assert.equal(events.at(-1).tipo,'pedir_diccionario');
console.log('OK: diccionario reutilizado, 200 mutaciones agrupadas en una revisión y recuperación tras recarga.');
