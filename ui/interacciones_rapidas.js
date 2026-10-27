// Una delegación para todos los botones nativos; no envía textos ni peticiones.
export default function(component) {
  const doc=component.parentElement.ownerDocument, active=new Map();
  const style=doc.createElement('style');
  style.textContent='button[data-usaer-pending="true"]{opacity:.75;cursor:progress;pointer-events:none}button[data-usaer-pending="true"]::after{content:"";width:12px;height:12px;border:2px solid currentColor;border-right-color:transparent;border-radius:50%;display:inline-block;margin-left:8px;animation:usaer-wait .8s linear infinite}@keyframes usaer-wait{to{transform:rotate(360deg)}}@media(prefers-reduced-motion:reduce){button[data-usaer-pending="true"]::after{animation:none}}';
  doc.head.append(style);
  const release=b=>{const item=active.get(b);if(!item)return;clearTimeout(item.timer);active.delete(b);b.removeAttribute('aria-busy');b.removeAttribute('aria-disabled');b.removeAttribute('data-usaer-pending');};
  const running=()=>doc.querySelector('[data-testid="stApp"][data-test-script-state="running"]')!==null;
  const click=e=>{
    const b=e.target.closest?.('button');
    if(!b||!b.closest('[data-testid="stButton"], [data-testid="stFormSubmitButton"]'))return;
    if(active.has(b)){e.preventDefault();e.stopImmediatePropagation();return;}
    if(b.disabled)return;
    b.setAttribute('aria-busy','true');b.setAttribute('aria-disabled','true');b.setAttribute('data-usaer-pending','true');
    const item={seen:running(),timer:setTimeout(()=>release(b),15000)};active.set(b,item);
    // No se modifica disabled de React: sus permisos/validaciones siguen mandando.
    // CSS y captura bloquean los clics posteriores, incluido teclado.
  };
  let frame=null;
  const inspect=()=>{frame=null;const busy=running();for(const [b,item] of active){item.seen ||= busy;if(!b.isConnected||item.seen&&!busy)release(b);}};
  const observer=new MutationObserver(()=>{if(frame===null)frame=requestAnimationFrame(inspect);});
  observer.observe(doc.body,{attributes:true,attributeFilter:['data-test-script-state'],childList:true,subtree:true});
  doc.addEventListener('click',click,true);
  return ()=>{doc.removeEventListener('click',click,true);observer.disconnect();if(frame!==null)cancelAnimationFrame(frame);for(const b of active.keys())release(b);style.remove();};
}
