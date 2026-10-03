export default function(component) {
  const words = component.data.words;
  const known = new Set(words);
  const rank = new Map(words.map((word, index) => [word, index]));
  const ignored = new Set();
  const controls = new Map();
  const letters = 'abcdefghijklmnñopqrstuvwxyzáéíóúü';
  const tokens = /[a-záéíóúüñ]+/giu;
  const excluded = /contraseña|password|usuario|curp|cct|correo|email|url|folio|clave|identificador/i;
  function candidates(word) {
    const found = new Set();
    const add = value => { if (known.has(value)) found.add(value); };
    for (let i=0; i<=word.length; i++) {
      add(word.slice(0,i)+word.slice(i+1));
      if (i < word.length-1) add(word.slice(0,i)+word[i+1]+word[i]+word.slice(i+2));
      for (const letter of letters) {
        add(word.slice(0,i)+letter+word.slice(i));
        if (i<word.length) add(word.slice(0,i)+letter+word.slice(i+1));
      }
    }
    return [...found].sort((a,b)=>rank.get(a)-rank.get(b)).slice(0,5);
  }
  function scan() {
    for (const field of document.querySelectorAll('textarea, input[type="text"]')) {
      if (field.disabled || field.readOnly || excluded.test(field.getAttribute('aria-label') || field.placeholder || '')) continue;
      field.setAttribute('lang','es'); field.setAttribute('spellcheck','true');
      if (controls.has(field)) {
        const state = controls.get(field);
        if (!state.details.isConnected && state.holder.isConnected) state.holder.append(state.details);
        continue;
      }
      const holder = field.closest('[data-testid="stTextArea"], [data-testid="stTextInput"]');
      if (!holder) continue;
      const details = document.createElement('details'); details.style.cssText='font-size:13px;margin:4px 0 10px;color:#526a72';
      const summary = document.createElement('summary'); summary.textContent='Revisar escritura';
      const panel = document.createElement('div'); panel.style.cssText='white-space:pre-wrap;line-height:1.6;padding:8px;background:#fff;border:1px solid #d5e2e4;border-radius:6px';
      details.append(summary,panel); holder.append(details);
      let timer;
      function render() {
        if (!details.open) return;
        panel.replaceChildren();
        const text = field.value; let end = 0;
        for (const match of text.matchAll(tokens)) {
          panel.append(document.createTextNode(text.slice(end, match.index)));
          const word = match[0], lower = word.toLocaleLowerCase('es');
          if (known.has(lower) || ignored.has(lower) || lower.length < 3 || lower.length > 32) {
            panel.append(document.createTextNode(word));
          } else {
            const mark = document.createElement('button'); mark.type='button'; mark.textContent=word;
            mark.style.cssText='border:0;padding:0;background:transparent;color:#a32648;text-decoration:underline wavy #a32648;font:inherit;cursor:pointer';
            mark.title='Posible error; los nombres propios pueden estar bien';
            mark.addEventListener('click', () => {
              const menu = document.createElement('span'); menu.style.cssText='display:inline-flex;gap:4px;flex-wrap:wrap;padding:4px;background:#eaf5f5';
              for (const suggestion of candidates(lower)) {
                const option=document.createElement('button'); option.type='button'; option.textContent=suggestion;
                option.addEventListener('click', () => {
                  if (field.value !== text) { render(); return; }
                  const replacement = word[0] === word[0].toUpperCase() ? suggestion[0].toUpperCase()+suggestion.slice(1) : suggestion;
                  const prototype = field.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
                  Object.getOwnPropertyDescriptor(prototype,'value').set.call(field,text.slice(0,match.index)+replacement+text.slice(match.index+word.length));
                  field.dispatchEvent(new Event('input',{bubbles:true}));
                  field.dispatchEvent(new Event('change',{bubbles:true}));
                  field.focus(); field.blur(); render();
                }); menu.append(option);
              }
              const skip=document.createElement('button'); skip.type='button'; skip.textContent='Está bien escrito';
              skip.addEventListener('click',()=>{ignored.add(lower);render();}); menu.append(skip); mark.replaceWith(menu);
            }); panel.append(mark);
          }
          end=match.index+word.length;
        }
        panel.append(document.createTextNode(text.slice(end)));
        if (!text.trim()) panel.textContent='Escribe en el campo para revisar.';
      }
      const changed=()=>{clearTimeout(timer);timer=setTimeout(render,300);};
      field.addEventListener('input',changed); details.addEventListener('toggle',render);
      controls.set(field,{holder,details,changed,clear:()=>clearTimeout(timer)});
    }
    for (const [field, state] of controls) if (!field.isConnected) {state.clear();controls.delete(field);}
  }
  scan();
  const observer=new MutationObserver(scan); observer.observe(document.body,{childList:true,subtree:true});
  return () => {observer.disconnect();for(const [field,state] of controls){state.clear();field.removeEventListener('input',state.changed);state.details.remove();}controls.clear();};
}
