from uuid import uuid4
import pandas as pd
import streamlit as st

from services import tramites as api
from documents.tramites import generar_respuesta


def tramites_page():
    if not (api.gestor() or api.puede_solicitar()):
        st.error("Este módulo no está habilitado para tu cuenta.")
        return
    st.title("Trámites")
    st.caption("Solicitudes de expedientes · seguimiento, oficios y documentos recibidos.")
    gestor = api.gestor()
    with st.expander("Registrar solicitud de otra USAER o CAM" if gestor else "Solicitar expedientes", expanded=True):
        identificador = st.session_state.setdefault("tramite_nuevo_id", uuid4().hex)
        alumnos = pd.DataFrame()
        if not gestor:
            try:
                alumnos = api.alumnos_solicitables().fillna("")
            except Exception:
                st.error("No se pudieron consultar tus alumnos. Reintenta en un momento.")
                return
        with st.form("nuevo_tramite_" + identificador):
            if gestor:
                origen = st.text_input("USAER o CAM que solicita")
                nombres = st.text_area("Alumno(s) o expediente(s) requeridos")
                referencia = st.text_input("Número y fecha del oficio recibido (opcional)")
                ids = []
            else:
                registros = {str(r["ID_Alumno"]): r for r in alumnos.to_dict("records")}
                ids = st.multiselect("Alumnos asignados a tu cuenta", list(registros),
                    format_func=lambda i: f"{registros[i].get('Nombre_Completo', registros[i].get('Nombre', ''))} · {i}")
                origen, nombres, referencia = "", "", ""
            solicitud = st.text_area("¿Qué necesitas y para qué?", max_chars=4000)
            crear = st.form_submit_button("Registrar solicitud" if gestor else "Enviar solicitud a Trabajo Social", type="primary", width="stretch")
        if crear:
            try:
                row = api.crear_solicitud("Externa" if gestor else "Interna", solicitud, identificador, ids, origen, nombres, referencia)
                st.session_state["tramite_activo"] = row["ID_Tramite"]
                st.session_state.pop("tramite_nuevo_id", None)
                st.success("Solicitud registrada. El padrón no se modificó.")
            except (ValueError, PermissionError) as exc:
                st.info(str(exc))
            except Exception:
                st.error("No se pudo registrar la solicitud. Reintenta sin volver a crearla.")
    if st.button("Actualizar solicitudes", width="stretch"):
        st.rerun()
    try:
        rows = api.solicitudes()
    except Exception:
        st.error("No se pudo consultar el control de solicitudes.")
        return
    if not rows:
        st.caption("Aún no hay solicitudes.")
        return
    if gestor:
        tipo = st.selectbox("Mostrar solicitudes", ["Todas", "Interna", "Externa"])
        rows = [r for r in rows if tipo == "Todas" or r["Tipo"] == tipo]
    if not rows:
        st.caption("No hay solicitudes de este tipo.")
        return
    tabla = pd.DataFrame(rows)
    columnas = [c for c in ("Fecha", "Solicitante", "Tipo", "Origen", "Escuela", "Alumnos", "Estado", "Folio") if c in tabla]
    st.dataframe(tabla[columnas], hide_index=True, width="stretch")
    keys = [r["ID_Tramite"] for r in rows]
    activo = st.session_state.get("tramite_activo")
    elegido = st.selectbox("Abrir solicitud", keys, index=keys.index(activo) if activo in keys else 0,
        format_func=lambda k: next(f"{r['Fecha'][:10]} · {r['Alumnos']} · {r['Estado']}" for r in rows if r["ID_Tramite"] == k))
    row = next(r for r in rows if r["ID_Tramite"] == elegido)
    st.write(row["Solicitud"])
    if row.get("Seguimiento"):
        st.caption("Seguimiento: " + row["Seguimiento"])
    if gestor:
        with st.form("seguimiento_" + elegido + row["Revision"]):
            estado = st.selectbox("Estado", api.ESTADOS, index=api.ESTADOS.index(row["Estado"]))
            nota = st.text_area("Seguimiento", value=row.get("Seguimiento", ""))
            if st.form_submit_button("Guardar seguimiento", type="primary"):
                try:
                    api.actualizar(elegido, row["Revision"], estado, nota)
                    st.rerun()
                except (ValueError, PermissionError) as exc:
                    st.info(str(exc))
                except Exception:
                    st.error("No se pudo guardar el seguimiento.")
        with st.expander("Oficio de respuesta"):
            st.caption("Usa el control central de folios. Se prepara para revisión y firma de Dirección; no se envía automáticamente.")
            with st.form("respuesta_" + elegido):
                destinatario = st.text_input("Destinatario y cargo", value=row["Origen"])
                cuerpo = st.text_area("Respuesta", max_chars=4000, height=160)
                emitir = st.form_submit_button("Preparar oficio y asignar folio", disabled=bool(row.get("ID_Oficio")), type="primary")
            if emitir:
                try:
                    oficio = api.emitir_respuesta(elegido, destinatario, cuerpo)
                    st.session_state["tramite_oficio_" + elegido] = oficio
                    st.success("Oficio registrado para firma. Conserva el mismo folio al descargarlo nuevamente.")
                except (ValueError, PermissionError) as exc:
                    st.info(str(exc))
                except Exception:
                    st.error("No se pudo completar la respuesta. Reintenta: se recuperará el folio si ya fue registrado.")
        with st.expander("Cargar oficio recibido o acuse firmado"):
            tipo_documento = st.selectbox("Documento", ["Oficio recibido", "Acuse de recibido"], key="tipo_adjunto_" + elegido)
            archivos = st.file_uploader("Fotos o imágenes (JPG, PNG o WEBP; hasta 5 MB cada una)", type=["jpg", "jpeg", "png", "webp"], accept_multiple_files=True, key="adjuntos_" + elegido)
            if st.button("Guardar documentos en esta solicitud", disabled=not archivos, key="guardar_adjuntos_" + elegido):
                try:
                    with st.spinner("Guardando documentos..."):
                        for archivo in archivos:
                            api.guardar_imagen(elegido, tipo_documento, archivo.name, archivo.getvalue())
                    st.success("Documentos guardados. Los archivos repetidos no se duplican.")
                except (ValueError, PermissionError) as exc:
                    st.info(str(exc))
                except Exception:
                    st.error("No se completó la carga. Puedes reintentar sin duplicar los archivos guardados.")
    # Recuperar siempre del registro central permite cerrar sesión y descargar después.
    try:
        if row.get("ID_Oficio") or st.session_state.get("tramite_oficio_" + elegido):
            oficio = api.oficio_guardado(elegido)
            st.download_button(f"Descargar respuesta · folio {int(oficio['Folio']):03d}", generar_respuesta(oficio),
                               f"Respuesta_expedientes_{int(oficio['Folio']):03d}.pdf", "application/pdf", key="descarga_respuesta_" + elegido)
        adjuntos = api.adjuntos(elegido)
        if adjuntos:
            with st.expander("Documentos de esta solicitud"):
                for a in adjuntos:
                    st.caption(a["Tipo"] + " · " + a["Nombre"])
                    if st.button("Ver y descargar", key="abrir_adjunto_" + a["ID_Adjunto"]):
                        st.session_state["adjunto_abierto"] = (elegido, a["ID_Adjunto"])
                    if st.session_state.get("adjunto_abierto") == (elegido, a["ID_Adjunto"]):
                        data = api.descargar_imagen(elegido, a["ID_Adjunto"])
                        st.image(data, width="stretch")
                        st.download_button("Descargar imagen", data, a["Nombre"], a["Mime"], key="archivo_" + a["ID_Adjunto"])
    except Exception:
        st.caption("No se pudieron recuperar los documentos. La solicitud se conserva.")
