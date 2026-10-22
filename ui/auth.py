import hmac
import hashlib
import logging
import streamlit as st
from data.repository import usuarios
from services.asignaciones import escuelas_asignadas
from utils.text import normalizar_texto
from ui.mobile_install import installation_help
from ui.passkeys import login_passkey


def start_session(match):
    """Both login methods use the same server-side permissions and assignments."""
    nombre = str(match.get("Nombre", ""))
    rol = str(match.get("Rol", ""))
    escuelas = str(match.get("Escuelas_Permitidas", ""))
    oficiales = escuelas_asignadas(nombre, rol)
    if oficiales:
        escuelas = ",".join(oficiales)
    st.session_state.update({"autenticado": True, "usuario": str(match.get("Usuario", "")),
        "nombre": nombre, "rol": rol, "escuelas_permitidas": escuelas})
    st.session_state.pop("passkey_pending", None)
    st.session_state['_sesion_emitir'] = True
    st.session_state.pop('_sesion_borrar', None)


def login():
    with st.container(key="institutional_login"):
        _login_content()


def _login_content():
    st.markdown(
        "<div style='text-align:center;margin-bottom:1.6rem;'>"
        "<div class='badge' style='margin-bottom:0.6rem;'>Zona Escolar 001 · Yucatán</div>"
        "<h2 style='font-size:1.9rem;margin:0 0 0.35rem;letter-spacing:-0.025em;color:var(--bs-primary-dark);'>USAER 02-E</h2>"
        "<p style='color:var(--bs-secondary-color);font-size:0.92rem;margin:0;'>Plataforma institucional de gestión e intervención</p>"
        "</div>",
        unsafe_allow_html=True,
    )
    st.markdown("<div style='font-weight:600;font-size:1rem;color:var(--bs-primary-dark);margin-bottom:0.6rem;'>Acceso del equipo</div>", unsafe_allow_html=True)
    login_passkey(start_session)
    with st.form("login"):
        user = st.text_input("Usuario", placeholder="Tu usuario institucional")
        password = st.text_input("Contraseña", type="password", placeholder="••••••••")
        ok = st.form_submit_button("Ingresar a la plataforma", type="primary", use_container_width=True)
    if ok:
        try:df = usuarios()
        except Exception as exc:
            logging.getLogger(__name__).warning('autenticacion_lectura_error tipo=%s',type(exc).__name__)
            st.warning('La conexión de acceso está temporalmente ocupada. Vuelve a intentar; no se modificó tu cuenta.')
            return
        match = None
        if not df.empty:
            for _, r in df.iterrows():
                if hmac.compare_digest(str(r.get("Usuario", "")), user) and hmac.compare_digest(str(r.get("Password", "")), password):
                    match = r
                    break
        if match is None:
            st.error("Usuario o contraseña incorrectos.")
        else:
            start_session(match)
            st.rerun()
    installation_help()
    st.markdown("<p class='institution-footnote' style='text-align:center;'>USAER 02-E · Zona 001 · Yucatán<br>Información educativa de uso exclusivo del personal autorizado.</p>", unsafe_allow_html=True)


def logout(key="cerrar_sesion"):
    """Muestra un cierre de sesión en el contenedor actual."""
    if any(k.startswith('metas_') and k.endswith('_pending') and v for k,v in st.session_state.items()):
        from ui.metas_personales import proteger_salida
        if not proteger_salida(key):return
    prefix='planeacion_'+hashlib.sha256(str(st.session_state.get('usuario','')).encode()).hexdigest()[:12]
    pendientes=any(k.startswith(prefix) and k.endswith('_pending') and v for k,v in st.session_state.items())
    salir=False
    if pendientes:
        st.info('Hay cambios sin confirmación de guardado. Puedes seguir trabajando o abrir otra planeación. Antes de cerrar, confirma el guardado o descarga un respaldo.')
        from ui.planeacion_pendientes import pendientes as ediciones,controles_guardado
        for p in ediciones(prefix):
            doc=st.session_state[p+'_doc']
            st.caption(doc.get('datos',{}).get('Escuela regular','Planeación')+' · '+doc.get('formato',''))
            controles_guardado(p,key+'_'+p)
        salir=st.checkbox('Ya descargué mi respaldo; cerrar sin confirmación central',key=key+'_confirmar_pendientes')
        if st.button('Guardar cambios y cerrar sesión',key=key+'_guardar',use_container_width=True):
            from ui.planeacion import _guardar_edicion_pendiente
            claves=ediciones(prefix)
            if not claves:
                st.warning('Hay una edición pendiente que no se pudo identificar. Vuelve al formato abierto para recuperar el texto antes de cerrar.');return
            resultados=[]
            for p in claves:
                try:resultados.append(_guardar_edicion_pendiente(p))
                except Exception as exc:
                    from services.planeacion_guardado_estado import diagnostico
                    st.session_state[p+'_guardado_diagnostico']=diagnostico(exc)
                    resultados.append(False)
            if not all(resultados):
                st.warning('No se cerró la sesión: hay guardados sin confirmar. Consulta la causa y descarga cada respaldo antes de salir.');return
            _cerrar();return
    etiqueta='Cerrar sesión con respaldo descargado' if pendientes and salir else 'Cerrar sesión'
    if st.button(etiqueta, key=key, use_container_width=True,disabled=pendientes and not salir):
        _cerrar()


def _cerrar():
    token = st.session_state.get('_sesion_token')
    if token:
        try:
            from services.sesiones_recuperables import servicio
            servicio().cerrar(token, st.session_state.get('usuario', ''))
        except Exception:
            st.warning('No se confirmó la revocación del acceso. Intenta cerrar otra vez; no se descartó tu trabajo.')
            return
    st.session_state['_sesion_borrar'] = True
    st.session_state.pop('_sesion_token', None)
    st.session_state.pop('_sesion_emitir', None)
    st.session_state.pop('_sesion_conservar_borrador', None)
    from services.sesiones_recuperables import CAMPOS
    for campo in CAMPOS:
        st.session_state.pop(campo, None)
    for campo in [k for k in st.session_state if k.startswith('metas_')]:
        st.session_state.pop(campo,None)
    for k in [
            "autenticado",
            "nombre",
            "rol",
            "escuelas_permitidas",
            "selected_alumno",
            "usuario",
            "passkey_pending",
        ]:
        st.session_state.pop(k, None)
    st.rerun()
