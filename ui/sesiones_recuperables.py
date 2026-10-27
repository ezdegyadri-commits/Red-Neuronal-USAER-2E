"""Puente de sesión: restauración autorizada antes de presentar el acceso."""
from pathlib import Path
from weakref import WeakKeyDictionary
import hashlib
import json
import time
import streamlit as st
import streamlit.components.v2 as components
from streamlit.components.v2.get_bidi_component_manager import get_bidi_component_manager
from services.sesiones_recuperables import servicio, CAMPOS

_COMPONENTES = WeakKeyDictionary()


def _evento():
    # Registrar el estado bidireccional; su contenido se valida en recuperar().
    pass


def recuperar():
    datos = {'borrar': st.session_state.get('_sesion_borrar', False)}
    autenticado = st.session_state.get('autenticado')
    if autenticado:
        try:
            s = servicio()
            cuenta = st.session_state['usuario']
            if st.session_state.get('_sesion_emitir'):
                st.session_state['_sesion_token'] = s.emitir(cuenta)
                st.session_state['_sesion_emitir'] = False
            borrador = {k: st.session_state[k] for k in CAMPOS if k in st.session_state}
            firma=hashlib.sha256(json.dumps([cuenta,borrador],sort_keys=True,default=str,ensure_ascii=False).encode()).hexdigest()
            cache=st.session_state.get('_sesion_borrador_cifrado',{})
            if not st.session_state.get('_sesion_conservar_borrador') and (cache.get('firma')!=firma or time.monotonic()-cache.get('fecha',0)>1800):
                cache={'firma':firma,'fecha':time.monotonic(),'cifrado':s.proteger_borrador(cuenta,borrador)}
                st.session_state['_sesion_borrador_cifrado']=cache
            datos.update(token=st.session_state.get('_sesion_token', ''),
                cuenta=hashlib.sha256(cuenta.encode()).hexdigest(),
                borrador='' if st.session_state.get('_sesion_conservar_borrador') else cache['cifrado'],
                tiene_borrador=bool(borrador.get('evento_descripcion')))
        except Exception:
            # La recuperación es opcional; un fallo no impide el acceso normal.
            st.caption('No se confirmó la continuidad de esta pestaña. Guarda antes de recargar.')
    registro = get_bidi_component_manager()
    if registro not in _COMPONENTES:
        _COMPONENTES[registro] = components.component('usaer_continuidad_pestana_v1',
            html='<span aria-hidden="true"></span>', js=Path(__file__).with_name('sesion_component.js').read_text(encoding='utf-8'), isolate_styles=True)
    result = _COMPONENTES[registro](key='usaer_continuidad_pestana', data=datos, default={'evento':None}, on_evento_change=_evento, height=0)
    event = result.get('evento')
    if not event or event.get('nonce') == st.session_state.get('_sesion_evento'): return
    st.session_state['_sesion_evento'] = event.get('nonce')
    accion = event.get('accion')
    if accion == 'borrado': st.session_state.pop('_sesion_borrar', None); return
    if accion == 'sin_respaldo':
        st.warning('El navegador bloquea el respaldo por pestaña. Guarda antes de recargar.'); return
    try:
        s = servicio()
        if accion == 'recuperar' and not autenticado:
            user = s.recuperar(event.get('token'))
            from ui.auth import start_session
            start_session(user)
            st.session_state['_sesion_emitir'] = False
            st.session_state['_sesion_token'] = event['token']
        elif accion != 'borrador' or not autenticado: return
        if event.get('borrador'):
            try:
                restaurado = s.recuperar_borrador(st.session_state['usuario'], event['borrador'])
                if restaurado.get('evento_descripcion') or restaurado.get('evento_borradores_json'):
                    from services.padron_movimientos import visibles
                    from services.eventos_continuidad import filtrar_borrador
                    restaurado=filtrar_borrador(restaurado,visibles())
                if not st.session_state.get('evento_descripcion'):
                    st.session_state.update(restaurado)
                st.session_state.pop('_sesion_conservar_borrador',None)
            except ValueError:
                st.caption('El borrador de eventos ya no es recuperable. Los registros guardados se conservan.')
            except Exception:
                st.session_state['_sesion_conservar_borrador']=True
                st.caption('No se pudieron verificar los permisos del borrador. Su respaldo cifrado se conserva; vuelve a recargar cuando haya conexión.')
        st.rerun()
    except Exception:
        st.session_state['_sesion_borrar'] = True
        st.info('Vuelve a ingresar para continuar. No se han eliminado registros.')
        st.rerun()
