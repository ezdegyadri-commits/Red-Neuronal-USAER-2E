// Almacenamiento por pestaña, cifrado por el servidor. Sin URLs ni contraseñas.
export default function mount(component) {
  const host = component.parentElement, d = component.data || {};
  const emit = data => component.setStateValue('evento', {...data, nonce: Date.now() + '-' + Math.random()});
  const access = 'usaer:acceso:v1', owner = 'usaer:cuenta:v1';
  try {
    if (d.borrar) {
      sessionStorage.removeItem(access);
      sessionStorage.removeItem(owner);
      // El borrador cifrado queda disponible sólo a su misma cuenta durante 12 h.
      if (!host.__cleared) { host.__cleared = true; emit({accion:'borrado'}); }
      return;
    }
    host.__cleared = false;
    if (d.token) {
      sessionStorage.setItem(access, d.token);
      sessionStorage.setItem(owner, d.cuenta);
    }
    if (d.cuenta && host.__draftOwner !== d.cuenta) {
      host.__draftOwner = d.cuenta;
      const saved = sessionStorage.getItem('usaer:borrador:' + d.cuenta);
      if (saved && !d.tiene_borrador) { emit({accion:'borrador', borrador:saved}); return; }
    }
    if (d.borrador && d.cuenta) sessionStorage.setItem('usaer:borrador:' + d.cuenta, d.borrador);
    if (!d.token && !d.cuenta && !host.__read) {
      host.__read = true;
      const token = sessionStorage.getItem(access), cuenta = sessionStorage.getItem(owner);
      if (token) emit({accion:'recuperar', token, borrador:sessionStorage.getItem('usaer:borrador:' + cuenta)});
    }
  } catch (_) {
    if (!host.__storageError) { host.__storageError = true; emit({accion:'sin_respaldo'}); }
  }
}
