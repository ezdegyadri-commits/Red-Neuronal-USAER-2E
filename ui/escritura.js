export default function(component) {
  const cacheKey='__usaer_diccionario_es_v1';
  let dictionary=globalThis[cacheKey];
  if (!dictionary && Array.isArray(component.data.words)) {
    const words=component.data.words;
    dictionary={known:new Set(words),rank:new Map(words.map((word,index)=>[word,index]))};
    globalThis[cacheKey]=dictionary;
  }
  const host=component.parentElement;
  if (!dictionary) {
    if (!host.__dictionaryRequested) {host.__dictionaryRequested=true;component.setStateValue('evento',{tipo:'pedir_diccionario'});}
    return;
  }
  host.__dictionaryRequested=false;
  if (Array.isArray(component.data.words)) component.setStateValue('evento',{tipo:'diccionario_listo'});
  const {known,rank}=dictionary;
  const ignored = new Set();
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

  function renderMaster(panel) {
    panel.replaceChildren();
    const header = document.createElement('div');
    header.style.cssText = 'display:flex;justify-content:space-between;align-items:center;border-bottom:1px solid #e0e0e0;padding-bottom:6px;margin-bottom:8px;font-weight:600;color:#0e4b52;';
    header.innerHTML = '<span>✏️ Revisión general de redacción</span>';
    const closeBtn = document.createElement('button');
    closeBtn.type = 'button';
    closeBtn.textContent = '✕';
    closeBtn.style.cssText = 'border:none;background:transparent;cursor:pointer;font-size:14px;color:#777;';
    closeBtn.addEventListener('click', () => { panel.style.display = 'none'; });
    header.append(closeBtn);
    panel.append(header);

    const editableFields = Array.from(document.querySelectorAll('textarea, input[type="text"]')).filter(f => !f.disabled && !f.readOnly && !excluded.test(f.getAttribute('aria-label') || f.placeholder || ''));
    let totalDudas = 0;

    for (const field of editableFields) {
      const text = field.value || '';
      if (!text.trim()) continue;
      const dudas = [];
      for (const match of text.matchAll(tokens)) {
        const word = match[0], lower = word.toLocaleLowerCase('es');
        if (!known.has(lower) && !ignored.has(lower) && lower.length >= 3 && lower.length <= 32) {
          dudas.push({word, lower, index: match.index});
        }
      }
      if (dudas.length > 0) {
        totalDudas += dudas.length;
        const fieldBlock = document.createElement('div');
        fieldBlock.style.cssText = 'margin-bottom:10px;padding:8px;background:#f8fbfc;border:1px solid #ddecfa;border-radius:6px;';
        const label = field.getAttribute('aria-label') || field.placeholder || 'Campo de texto';
        const title = document.createElement('div');
        title.style.cssText = 'font-weight:600;font-size:12px;color:#1d5f6f;margin-bottom:4px;';
        title.textContent = label.length > 40 ? label.slice(0, 40) + '…' : label;
        fieldBlock.append(title);

        for (const duda of dudas) {
          const row = document.createElement('div');
          row.style.cssText = 'display:flex;flex-wrap:wrap;align-items:center;gap:4px;margin-top:4px;font-size:12px;';
          const badWord = document.createElement('span');
          badWord.textContent = duda.word;
          badWord.style.cssText = 'color:#a32648;font-weight:600;text-decoration:underline wavy #a32648;';
          row.append(badWord, document.createTextNode(': '));

          const sugList = candidates(duda.lower);
          for (const sug of sugList) {
            const opt = document.createElement('button');
            opt.type = 'button';
            opt.textContent = sug;
            opt.style.cssText = 'padding:2px 6px;background:#e1f5fe;border:1px solid #b3e5fc;border-radius:4px;cursor:pointer;font-size:11px;color:#0277bd;';
            opt.addEventListener('click', () => {
              const current = field.value;
              const rep = duda.word[0] === duda.word[0].toUpperCase() ? sug[0].toUpperCase() + sug.slice(1) : sug;
              const proto = field.tagName === 'TEXTAREA' ? HTMLTextAreaElement.prototype : HTMLInputElement.prototype;
              Object.getOwnPropertyDescriptor(proto, 'value').set.call(field, current.slice(0, duda.index) + rep + current.slice(duda.index + duda.word.length));
              field.dispatchEvent(new Event('input', {bubbles: true}));
              field.dispatchEvent(new Event('change', {bubbles: true}));
              renderMaster(panel);
            });
            row.append(opt);
          }
          const skip = document.createElement('button');
          skip.type = 'button';
          skip.textContent = 'Ignorar';
          skip.style.cssText = 'padding:2px 6px;background:#eee;border:1px solid #ddd;border-radius:4px;cursor:pointer;font-size:11px;color:#555;';
          skip.addEventListener('click', () => {
            ignored.add(duda.lower);
            renderMaster(panel);
          });
          row.append(skip);
          fieldBlock.append(row);
        }
        panel.append(fieldBlock);
      }
    }

    if (totalDudas === 0) {
      const okMsg = document.createElement('div');
      okMsg.style.cssText = 'color:#2e7d32;font-weight:500;padding:12px 0;text-align:center;';
      okMsg.textContent = '✅ No se detectaron palabras dudosas en las redacciones de esta página.';
      panel.append(okMsg);
    }
  }

  function scan() {
    // 1. Limpieza estricta de cualquier <details> individual inyectado en campos
    for (const field of document.querySelectorAll('textarea, input[type="text"]')) {
      if (field.disabled || field.readOnly || excluded.test(field.getAttribute('aria-label') || field.placeholder || '')) continue;
      field.setAttribute('lang','es');
      field.setAttribute('spellcheck','true');

      const holder = field.closest('[data-testid="stTextArea"], [data-testid="stTextInput"]');
      if (holder) {
        holder.querySelectorAll('details').forEach(d => {
          const s = d.querySelector('summary');
          if (s && (s.textContent.includes('Revisar escritura') || s.textContent.includes('Revisar redacción'))) {
            d.remove();
          }
        });
      }
    }

    // 2. Un único botón maestro flotante para toda la página
    if (!document.getElementById('usaer-master-spellcheck-wrap') && document.body) {
      const wrap = document.createElement('div');
      wrap.id = 'usaer-master-spellcheck-wrap';
      wrap.style.cssText = 'position:fixed;bottom:20px;right:20px;z-index:99999;font-family:system-ui,-apple-system,sans-serif;';

      const panel = document.createElement('div');
      panel.id = 'usaer-master-spellcheck-panel';
      panel.style.cssText = 'display:none;position:absolute;bottom:46px;right:0;width:340px;max-height:420px;overflow-y:auto;background:#fff;border:1px solid #c7d8da;border-radius:10px;box-shadow:0 6px 24px rgba(0,0,0,0.18);padding:12px;';

      const btn = document.createElement('button');
      btn.id = 'usaer-master-spellcheck-btn';
      btn.type = 'button';
      btn.innerHTML = '✏️ Revisar redacción';
      btn.style.cssText = 'background:#004d40;color:#fff;border:none;border-radius:20px;padding:7px 14px;font-size:12px;font-weight:600;box-shadow:0 2px 8px rgba(0,0,0,0.2);cursor:pointer;display:flex;align-items:center;gap:4px;';
      btn.title = 'Revisar ortografía de todas las redacciones de la página';

      btn.addEventListener('click', (e) => {
        e.stopPropagation();
        const isOpen = panel.style.display !== 'none';
        if (isOpen) {
          panel.style.display = 'none';
        } else {
          panel.style.display = 'block';
          renderMaster(panel);
        }
      });

      wrap.append(panel, btn);
      document.body.append(wrap);
    }
  }

  scan();
  let frame = null;
  const observer = new MutationObserver(() => {
    if (frame === null) frame = requestAnimationFrame(() => { frame = null; scan(); });
  });
  if (document.body) {
    observer.observe(document.body, {childList: true, subtree: true});
  }

  return () => {
    observer.disconnect();
    if (frame !== null) cancelAnimationFrame(frame);
    const wrap = document.getElementById('usaer-master-spellcheck-wrap');
    if (wrap) wrap.remove();
  };
}
