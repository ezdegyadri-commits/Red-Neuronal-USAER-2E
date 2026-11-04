const encoder = new TextEncoder();
const decoder = new TextDecoder();
const vigencia = 24 * 60 * 60 * 1000;

function base64(bytes) {
  let texto = '';
  for (const byte of bytes) texto += String.fromCharCode(byte);
  return btoa(texto);
}
const bytes = texto => Uint8Array.from(atob(texto), c => c.charCodeAt(0));

async function huella(texto) {
  const digest = await crypto.subtle.digest('SHA-256', encoder.encode(texto));
  return Array.from(new Uint8Array(digest), b => b.toString(16).padStart(2, '0')).join('');
}

export async function abrirBoveda(cuenta, frase) {
  if (!window.isSecureContext || !navigator.locks) throw new Error('La bóveda requiere HTTPS y un navegador compatible.');
  if (frase.trim().length < 20) throw new Error('Usa una frase de recuperación de al menos 20 caracteres.');
  const prefijo = 'usaer-boveda-v1-' + await huella(cuenta);
  const observado = new Map();
  const base = await crypto.subtle.importKey('raw', encoder.encode(frase), 'PBKDF2', false, ['deriveKey']);

  async function cifrar(clave, ubicacion, valor) {
    const iv = crypto.getRandomValues(new Uint8Array(12));
    const resultado = await crypto.subtle.encrypt(
      { name: 'AES-GCM', iv, additionalData: encoder.encode(ubicacion) },
      clave, encoder.encode(JSON.stringify(valor))
    );
    return { iv: base64(iv), cifrado: base64(new Uint8Array(resultado)) };
  }

  async function descifrar(clave, ubicacion, registro) {
    const resultado = await crypto.subtle.decrypt(
      { name: 'AES-GCM', iv: bytes(registro.iv), additionalData: encoder.encode(ubicacion) },
      clave, bytes(registro.cifrado)
    );
    return JSON.parse(decoder.decode(resultado));
  }

  const llave = await navigator.locks.request(prefijo, async () => {
    const texto = localStorage.getItem(prefijo);
    const existente = texto ? JSON.parse(texto) : null;
    const sal = existente ? bytes(existente.sal) : crypto.getRandomValues(new Uint8Array(16));
    const clave = await crypto.subtle.deriveKey(
      { name: 'PBKDF2', hash: 'SHA-256', salt: sal, iterations: 600000 },
      base, { name: 'AES-GCM', length: 256 }, false, ['encrypt', 'decrypt']
    );
    if (existente) {
      try {
        if (await descifrar(clave, prefijo, existente) !== 'usaer-v1') throw new Error();
      } catch (_) {
        throw new Error('La frase no abre esta bóveda.');
      }
    } else {
      localStorage.setItem(prefijo, JSON.stringify({ sal: base64(sal), ...await cifrar(clave, prefijo, 'usaer-v1') }));
    }
    return clave;
  });

  async function operar(celda, accion, valor) {
    const ubicacion = prefijo + ':' + await huella(celda);
    return navigator.locks.request(ubicacion, async () => {
      const texto = localStorage.getItem(ubicacion);
      if (accion === 'leer') {
        observado.set(ubicacion, texto);
        if (!texto) return null;
        const registro = JSON.parse(texto);
        if (registro.caduca <= Date.now()) {
          localStorage.removeItem(ubicacion);
          observado.set(ubicacion, null);
          return null;
        }
        return descifrar(llave, ubicacion, registro);
      }
      if (texto !== observado.get(ubicacion)) throw new Error('La copia cifrada cambió en otra pestaña. Reabre la guía.');
      if (accion === 'borrar') {
        localStorage.removeItem(ubicacion);
        observado.set(ubicacion, null);
      } else {
        const registro = { caduca: Date.now() + vigencia, ...await cifrar(llave, ubicacion, valor) };
        const nuevo = JSON.stringify(registro);
        localStorage.setItem(ubicacion, nuevo);
        observado.set(ubicacion, nuevo);
      }
    });
  }
  return {
    leer: celda => operar(celda, 'leer'),
    guardar: (celda, valor) => operar(celda, 'guardar', valor),
    borrar: celda => operar(celda, 'borrar'),
  };
}
