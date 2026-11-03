"""Activar la base central sin descartar documentos o trabajos pendientes."""
import threading,importlib,sys
import streamlit as st
from data.origen_operativo import usar_sql
VERSION='SG1'
_lock=threading.RLock()
_aplicada=False

def preparar():
    global _aplicada
    from data import repository as repo
    with _lock:
        # También sustituye la función que conservaba el módulo importado antes
        # del despliegue. Los métodos existentes resuelven este global al llamarse.
        repo.usar_sql=usar_sql
        if not _aplicada:
            from data import google,acceso_usuarios
            names=('connections','service_account_client','personal_responses_connection','drive_oauth_google_client','retry_google','read_sheet','read_personal_responses','df_sheet','clear_cache','worksheet','ensure_sheet','ensure_headers','append_dict','google_append_rows_raw','google_append_raw','next_numeric_id')
            old={name:getattr(google,name,None) for name in names}
            if getattr(google,'VERSION_PERSISTENCIA',None)!=VERSION:importlib.reload(google)
            if getattr(acceso_usuarios,'VERSION_PERSISTENCIA',None)!=VERSION:importlib.reload(acceso_usuarios)
            for key,module in tuple(sys.modules.items()):
                if module is None or not key.startswith(('data.','services.','ui.')):continue
                for name,value in old.items():
                    if value is not None and getattr(module,name,None) is value:setattr(module,name,getattr(google,name))
            from ui import auth
            auth.usuarios=repo.usuarios=acceso_usuarios.usuarios
            for modname,attribute in [('services.planeacion','_hoja'),('services.planeacion','_versiones'),('services.epp','hoja'),('services.cronogramas','_worksheet'),('data.passkeys','registry_sheet')]:
                module=sys.modules.get(modname);fn=getattr(module,attribute,None) if module else None
                if callable(getattr(fn,'clear',None)):fn.clear()
            for modname in ('services.planeacion_estabilidad','services.planeacion','services.epp','services.cronogramas','services.archivo_expediente'):
                module=sys.modules.get(modname)
                if module is not None:importlib.reload(module)
            google.clear_cache()
            repo.clear_alumnos_cache()
            _aplicada=True
    state=st.session_state
    if state.get('_operacion_activada')!=VERSION:
        # Solo una proyección de lectura. Nunca _doc, _value, _cola, _pending,
        # _trabajo_io, eventos, selecciones, filtros ni credenciales de sesión.
        for key in list(state):
            if key.startswith('_padron_autorizado_'):state.pop(key,None)
        state['_operacion_activada']=VERSION
