import assert from 'node:assert/strict';
import fs from 'node:fs';
import vm from 'node:vm';
const js=fs.readFileSync(new URL('../ui/interacciones_rapidas.js',import.meta.url),'utf8').replace('export default function','function mount');
let handler,observe,busy=false,frame,serial=0;const timers=new Map(),micro=[];
const style={remove(){this.removed=true;}};
const doc={head:{append(){}},body:{},createElement:()=>style,querySelector:()=>busy?{}:null,
 addEventListener:(type,fn)=>handler=fn,removeEventListener:()=>handler=null};
const button={disabled:false,isConnected:true,attrs:{},setAttribute(k,v){this.attrs[k]=v;},removeAttribute(k){delete this.attrs[k];},closest:()=>({})};
const event=()=>({target:{closest:()=>button},preventDefault(){this.prevented=true;},stopImmediatePropagation(){this.stopped=true;}});
const ctx={Map,queueMicrotask:fn=>micro.push(fn),setTimeout:fn=>{timers.set(++serial,fn);return serial;},clearTimeout:id=>timers.delete(id),
 requestAnimationFrame:fn=>{frame=fn;return 1;},cancelAnimationFrame:()=>{},MutationObserver:class{constructor(fn){observe=fn;}observe(){}disconnect(){}}};
vm.runInNewContext(js+';this.mount=mount;',ctx);
const cleanup=ctx.mount({parentElement:{ownerDocument:doc}});
const first=event();handler(first);assert.equal(first.prevented,undefined);assert.equal(button.attrs['aria-busy'],'true');
assert.equal(button.attrs['aria-disabled'],'true');
const twice=event();handler(twice);assert.equal(twice.stopped,true);
busy=true;observe();frame();assert.equal(button.attrs['aria-disabled'],'true');
busy=false;observe();frame();assert.equal(button.disabled,false);assert.equal(button.attrs['aria-busy'],undefined);
handler(event());for(const fn of timers.values())fn();assert.equal(button.disabled,false);
button.disabled=true;cleanup();assert.equal(button.disabled,true);
assert.equal(handler,null);assert.equal(style.removed,true);
console.log('Botones globales: feedback local, antirrebote, liberación y limpieza aprobados.');
