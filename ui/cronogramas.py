"""Interfaz del generador mensual de cronogramas para el equipo especialista."""

from __future__ import annotations

import json
import calendar
import re
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

import pandas as pd
import streamlit as st

from documents.cronogramas import generar_cronograma_pdf
from services.cronogramas import (
    DIAS_INHABILES,
    cargar_agenda,
    cargar_agenda_global,
    fechas_habiles,
    guardar_agenda,
    perfil_especialista,
)
from services.horarios import avisar_maestras_apoyo
from utils.text import normalizar_texto


MESES = (
    "enero", "febrero", "marzo", "abril", "mayo", "junio",
    "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre",
)
ESCUELA_JUNTA = "Junta General (Sede)"

# Los archivos permanecen privados en Drive y se comparten solo como lector
# con la cuenta de servicio; estos IDs no habilitan acceso sin ese permiso.
FIRMAS_DRIVE_DEFAULT = {
    "Abril de María Chable Ríos": "1JunTJoYJjpee64GMRcetX9AZWHVh6hgU",
    "María José Cupul Realpozo": "1hpwXpje0nHXGQwVjExJJRcGVngiicN_I",
    "Marilyn Pérez Lizama": "1vdNwkZVdbWAz5c-A5s6uQUcEeGMBauxZ",
    "Elmy Lucelly Puerto Gone": "1icDrDeguMexU2htThzNsIRn_ADaVXJBW",
    "Diego Peralta Torres": "119Q5blPGYQb4FvSf5HzYfsy97bOXnOQD",
    "Psic. Edgar Adrián Yam Briceño MD": "1a817fqYg3Dc5IfPwZYXibfAMH8LeVpS0",
}


def _mes_actual() -> date:
    return datetime.now(ZoneInfo("America/Mexico_City")).date().replace(day=1)


def _meses_disponibles():
    actual = _mes_actual()
    opciones = []
    for desplazamiento in range(-12, 19):
        numero = actual.year * 12 + actual.month - 1 + desplazamiento
        anio, mes_cero = divmod(numero, 12)
        mes = mes_cero + 1
        llave = f"{anio:04d}-{mes:02d}"
        opciones.append((llave, f"{MESES[mes - 1].capitalize()} {anio}"))
    return opciones


@st.cache_data(ttl=3600, show_spinner=False)
def _firma_drive(firma_id: str) -> bytes | None:
    if not firma_id:
        return None
    from data.google import service_account_drive_service
    return service_account_drive_service().files().get_media(fileId=firma_id).execute()


def _firma_drive_segura(firma_id: str) -> bytes | None:
    try:
        return _firma_drive(firma_id) if firma_id else None
    except Exception:
        return None


def _recursos_firma(perfil: dict):
    """Carga firmas opcionales de Drive sin incluir identificadores en el código fuente."""
    firmas = st.secrets.get("CRONOGRAMAS_FIRMAS", FIRMAS_DRIVE_DEFAULT)
    if isinstance(firmas, str):
        try:
            firmas = json.loads(firmas)
        except json.JSONDecodeError:
            firmas = {}
    clave = re.sub(r"[^A-Z0-9]+", "_", perfil["nombre"].upper()).strip("_")
    firma_id = str(firmas.get(perfil["nombre"], firmas.get(clave, ""))).strip() if hasattr(firmas, "get") else ""
    firma_especialista = _firma_drive_segura(firma_id)

    sello_id = str(st.secrets.get("CRONOGRAMAS_SELLO_ID", "")).strip()
    firma_direccion_id = str(st.secrets.get("CRONOGRAMAS_FIRMA_DIRECCION_ID", "")).strip()
    firma_direccion = _firma_drive_segura(firma_direccion_id)
    sello = _firma_drive_segura(sello_id)
    if firma_direccion is None:
        try:
            firma_direccion = (Path(__file__).resolve().parents[1] / "firma.png").read_bytes()
        except OSError:
            pass
    if sello is None:
        try:
            sello = (Path(__file__).resolve().parents[1] / "sello.png").read_bytes()
        except OSError:
            pass
    return firma_especialista, firma_direccion, sello



def _calendario_mes(mes, guardadas, escuelas=None, prefijo="", lectura=False):
    """Calendario real con días oficiales bloqueados y escuelas del perfil."""
    anio, numero = map(int, mes.split("-"))
    agenda = []
    clave_borrador = f"{prefijo}_dias"
    if not lectura and clave_borrador not in st.session_state:
        st.session_state[clave_borrador] = {dia: dict(datos) for dia, datos in guardadas.items()}
    borrador = st.session_state.get(clave_borrador, {}) if not lectura else {}
    for col, etiqueta in zip(st.columns(7), ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")):
        col.markdown(f"**{etiqueta}**")
    for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(anio, numero):
        for col, fecha in zip(st.columns(7), semana):
            iso = fecha.isoformat()
            motivo = DIAS_INHABILES.get(iso, "Fin de semana" if fecha.weekday() >= 5 else "")
            fuera = fecha.month != numero
            with col:
                with st.container(border=True):
                    color = "#f4f6f8" if fuera else ("#fff0d4" if "Consejo Técnico" in motivo else "#f9dddd" if motivo else "#eaf5f4")
                    etiqueta = "" if fuera else str(fecha.day)
                    st.markdown(f"<div style='background:{color};border-radius:8px;padding:8px;text-align:right;font-weight:bold'>{etiqueta}</div>", unsafe_allow_html=True)
                    if fuera:
                        continue
                    if motivo:
                        st.caption(motivo)
                        continue
                    if lectura:
                        entradas = guardadas.get(iso, [])
                        for item in entradas:
                            st.text(str(item.get("Especialista", "")))
                            st.caption(str(item.get("Escuela", "")))
                            st.text(str(item.get("Actividad", "")))
                        if not entradas:
                            st.caption("Sin actividad")
                    else:
                        valor = borrador.get(iso, {})
                        st.text(valor.get("escuela", "") or "Sin actividad")
                        if valor.get("actividad"):
                            st.caption(valor["actividad"])
                        if st.button("Editar", key=f"{prefijo}_{iso}_editar", width="stretch"):
                            st.session_state[f"{prefijo}_fecha"] = iso
    if not lectura:
        st.markdown("### Editar un día")
        dias = [dia.isoformat() for dia in fechas_habiles(mes)]
        if not dias:
            return []
        fecha = st.selectbox("Día a editar", dias, key=f"{prefijo}_fecha",
                             format_func=lambda d: date.fromisoformat(d).strftime("%d/%m/%Y"))
        valor = borrador.get(fecha, {})
        opciones = ["", *(escuelas or []), ESCUELA_JUNTA]
        anterior = next((e for e in opciones if normalizar_texto(e) == normalizar_texto(valor.get("escuela", ""))), "")
        with st.form(f"{prefijo}_editar_{fecha}"):
            escuela = st.selectbox("Escuela o junta", opciones, index=opciones.index(anterior),
                                   format_func=lambda e: e or "Elegir escuela o junta",
                                   key=f"{prefijo}_{fecha}_escuela_amplia", width="stretch")
            actividad = st.text_area("Actividad del día", value=valor.get("actividad", ""), height=110,
                                     key=f"{prefijo}_{fecha}_actividad_amplia")
            destino = st.selectbox("Mover a otra fecha (opcional)", ["", *[d for d in dias if d != fecha]],
                                   format_func=lambda d: date.fromisoformat(d).strftime("%d/%m/%Y") if d else "Mantener esta fecha")
            aplicar = st.form_submit_button("Aplicar al calendario", type="primary")
            limpiar = st.form_submit_button("Dejar este día sin actividad")
        if aplicar or limpiar:
            if aplicar and destino and borrador.get(destino, {}).get("actividad"):
                st.warning("La fecha elegida ya tiene actividad. Elige otra para no reemplazarla.")
            elif aplicar and (not escuela or not actividad.strip()):
                st.info("Elige la escuela y escribe la actividad.")
            else:
                borrador.pop(fecha, None)
                if aplicar:
                    borrador[destino or fecha] = {"escuela": escuela, "actividad": actividad.strip()}
                st.session_state[clave_borrador] = borrador
                for sufijo in ("escuela_amplia", "actividad_amplia"):
                    st.session_state.pop(f"{prefijo}_{fecha}_{sufijo}", None)
                st.session_state.pop("cronograma_pdf", None)
                st.rerun()
        agenda = [{"fecha": d, **datos} for d, datos in sorted(borrador.items())]
    return agenda


def _perfil_profesional(perfil):
    """Usa únicamente títulos explícitos del directorio; nunca inventa grados."""
    from data import repository as repo
    resultado = dict(perfil)
    def identidad(nombre):
        return re.sub(r"^(PSIC|LIC|MTRA|MTRO|DRA|DR|COM|TS)\s+", "", normalizar_texto(nombre).replace(".", " ").strip()).strip()
    try:
        personal = repo.personal().fillna("")
        for row in personal.to_dict("records"):
            nombre = str(row.get("Nombre_Completo", "")).strip()
            if identidad(nombre) != identidad(perfil["nombre"]):
                continue
            campos = {normalizar_texto(k).replace("_", " "): str(v).strip() for k, v in row.items()}
            titulo = next((campos[k] for k in ("TITULO PROFESIONAL", "TITULO", "GRADO ACADEMICO") if campos.get(k)), "")
            resultado["nombre_profesional"] = f"{titulo} {nombre}" if titulo and not nombre.startswith(titulo) else nombre
            break
    except Exception:
        pass
    return resultado


def cronogramas_direccion():
    """Supervisión de las agendas sin crear ni modificar registros."""
    perfil = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    if not perfil or perfil["area"] != "Dirección":
        st.error("Consulta exclusiva de Dirección.")
        return
    st.subheader("Revisar cronogramas del equipo")
    meses = dict(_meses_disponibles())
    mes = st.selectbox("Mes a supervisar", list(meses), index=list(meses).index(_mes_actual().strftime("%Y-%m")),
                       format_func=meses.get, key="direccion_cronogramas_mes")
    clave = f"direccion_agenda_{mes}"
    if st.button("Actualizar cronogramas", key="direccion_actualizar_cronogramas"):
        cargar_agenda_global.clear()
    try:
        rows = cargar_agenda_global(mes)
    except Exception:
        st.warning("No se pudo consultar el calendario. Reintenta en un momento.")
        return
    nombres = sorted(set(FIRMAS_DRIVE_DEFAULT) | {r["Especialista"] for r in rows})
    nombre = st.selectbox("Integrante", ["Todo el equipo", *nombres], key="direccion_cronogramas_persona")
    escuela = st.selectbox("Escuela", ["Todas", *perfil["escuelas"], ESCUELA_JUNTA], key="direccion_cronogramas_escuela")
    filtradas = [r for r in rows if (nombre == "Todo el equipo" or r["Especialista"] == nombre)
                 and (escuela == "Todas" or normalizar_texto(r["Escuela"]) == normalizar_texto(escuela))]
    agrupadas = {}
    for row in filtradas:
        agrupadas.setdefault(row["Fecha"], []).append(row)
    _calendario_mes(mes, agrupadas, lectura=True)
    if filtradas:
        st.dataframe(pd.DataFrame(filtradas).drop(columns=["ID_Publicacion"], errors="ignore"), hide_index=True, width="stretch")
    if nombre != "Todo el equipo":
        originales = [r for r in rows if r["Especialista"] == nombre]
        if originales and st.button("Preparar PDF del cronograma", key="direccion_preparar_pdf"):
            autor = perfil_especialista(nombre, originales[-1].get("Área", "ESPECIALISTA"))
            if autor:
                firma, visto, sello = _recursos_firma(autor)
                contenido = generar_cronograma_pdf(_perfil_profesional(autor), meses[mes], [
                    {"fecha": date.fromisoformat(r["Fecha"]).strftime("%d/%m/%Y"),
                     "escuela": r["Escuela"], "actividad": r["Actividad"]} for r in originales
                ], firma, visto, sello)
                st.session_state["direccion_pdf_cronograma"] = (nombre, mes, contenido, json.dumps(originales, sort_keys=True))
        archivo = st.session_state.get("direccion_pdf_cronograma")
        if (isinstance(archivo, tuple) and len(archivo) == 4 and archivo[:2] == (nombre, mes)
                and archivo[3] == json.dumps(originales, sort_keys=True)):
            st.download_button("Descargar cronograma oficial", archivo[2], f"Cronograma_{nombre}_{mes}.pdf", "application/pdf",
                               key="direccion_descargar_cronograma")


def cronogramas_page():
    # Descarta avisos de la integración retirada, incluso en sesiones abiertas.
    for clave_drive in ("cronograma_pdf_drive_url", "cronograma_pdf_drive_aviso"):
        st.session_state.pop(clave_drive, None)
    nombre = str(st.session_state.get("nombre", "")).strip()
    rol = str(st.session_state.get("rol", "")).strip()
    perfil = perfil_especialista(nombre, rol)
    if not perfil:
        st.error("Este apartado es exclusivo para las cuentas autorizadas del equipo especialista y de Dirección.")
        return

    st.title("Cronograma mensual" if perfil["area"] != "Dirección" else "Cronograma de Dirección")
    st.caption(f"{perfil['nombre']} · {perfil['area']} · USAER 02-E")
    if perfil["area"] == "Dirección":
        st.write("Genera tu propio cronograma y consulta el calendario consolidado de todo el equipo. Al publicar, las maestras de apoyo de las escuelas incluidas reciben el aviso en Horarios de apoyo.")
    else:
        st.write("Edita cada día y guarda los cambios para actualizar el calendario de Dirección y los avisos de las maestras de apoyo.")

    meses = _meses_disponibles()
    llaves = [llave for llave, _ in meses]
    indice = llaves.index(_mes_actual().strftime("%Y-%m")) if _mes_actual().strftime("%Y-%m") in llaves else 12
    mes = st.selectbox(
        "Mes del cronograma",
        llaves,
        index=indice,
        format_func=lambda llave: next(etiqueta for valor, etiqueta in meses if valor == llave),
        key=f"cronograma_mes_{perfil['nombre']}",
    )
    fechas = fechas_habiles(mes)
    editor_key = f"cronograma_editor_{perfil['nombre']}_{mes}"

    try:
        clave_agenda = f"agenda_inicial_{perfil['nombre']}_{mes}"
        vigente = cargar_agenda(perfil["nombre"], mes)
        if clave_agenda not in st.session_state:
            st.session_state[clave_agenda] = vigente
        elif st.session_state[clave_agenda] != vigente:
            borrador = st.session_state.get(f"{editor_key}_dias", st.session_state[clave_agenda])
            if borrador == st.session_state[clave_agenda]:
                st.session_state[clave_agenda] = vigente
                for clave in list(st.session_state):
                    if clave.startswith(editor_key):
                        st.session_state.pop(clave, None)
                st.session_state.pop("cronograma_pdf", None)
            else:
                st.info("Hay cambios guardados desde otra sesión. Recarga el calendario para verlos; tu edición local sigue aquí.")
        agenda_guardada = st.session_state[clave_agenda]
    except Exception:
        st.error("No se pudo consultar el calendario. Inténtalo de nuevo en un momento.")
        return

    st.caption("Elige un día para editarlo. Rosa: inhábil · Amarillo: CTE. Al guardar, todos verán el calendario actualizado.")
    if st.button("Recargar calendario guardado", key=f"{editor_key}_recargar"):
        cargar_agenda.clear()
        st.session_state.pop(clave_agenda, None)
        for clave in list(st.session_state):
            if clave.startswith(editor_key):
                st.session_state.pop(clave, None)
        st.session_state.pop("cronograma_pdf", None)
        st.rerun()
    agenda = _calendario_mes(mes, agenda_guardada, perfil["escuelas"], editor_key)
    enviar = st.button("Guardar cambios y generar PDF", type="primary", width="stretch")

    if enviar:
        try:
            with st.spinner("Guardando la agenda y preparando el PDF..."):
                resultado = guardar_agenda(perfil["nombre"], perfil["area"], mes, perfil["escuelas"], agenda)
                st.session_state.pop(clave_agenda, None)
                st.session_state["cronograma_publicacion_pendiente"] = {
                    "id": resultado.get("publicacion_id", ""),
                    "especialista": perfil["nombre"],
                    "mes": mes,
                    "agenda": agenda,
                }
                try:
                    notificadas = avisar_maestras_apoyo(
                        resultado.get("publicacion_id", ""), perfil["nombre"], mes, agenda
                    )
                    aviso_notificaciones = (
                        f"Se avisó a {notificadas} maestra(s) de apoyo."
                        if notificadas else
                        "El cronograma se guardó; no se encontraron cuentas de maestras de apoyo asignadas a esas escuelas."
                    )
                    st.session_state["cronograma_publicacion_pendiente"] = None
                except Exception as aviso_exc:
                    aviso_notificaciones = "Calendario guardado. Falta enviar el aviso; puedes reintentarlo abajo."
                filas_pdf = [
                    {"fecha": date.fromisoformat(item["fecha"]).strftime("%d/%m/%Y"),
                     "escuela": item["escuela"], "actividad": item["actividad"]}
                    for item in agenda
                    if item["escuela"].strip() and item["actividad"].strip()
                ]
                firma_esp, firma_dir, sello = _recursos_firma(perfil)
                pdf_bytes = generar_cronograma_pdf(
                    _perfil_profesional(perfil), next(etiqueta for llave, etiqueta in meses if llave == mes),
                    filas_pdf, firma_esp, firma_dir, sello,
                )
                sello_tiempo = datetime.now(ZoneInfo("America/Mexico_City")).strftime("%Y%m%d_%H%M%S")
                nombre_archivo = f"Cronograma_{perfil['nombre']}_{mes}_{sello_tiempo}.pdf"
                st.session_state["cronograma_pdf"] = pdf_bytes
                st.session_state["cronograma_pdf_nombre"] = nombre_archivo
                st.session_state["cronograma_pdf_mes"] = mes
                st.session_state["cronograma_pdf_autor"] = perfil["nombre"]
                st.session_state["cronograma_pdf_publicacion"] = resultado.get("publicacion_id", "")
                st.session_state["cronograma_pdf_firma_especialista"] = bool(
                    firma_esp or (perfil["area"] == "Dirección" and firma_dir)
                )
                st.session_state["cronograma_pdf_mensaje"] = f"Cronograma guardado: {resultado['filas']} actividades."
                st.session_state["cronograma_pdf_aviso_historial"] = resultado.get("aviso", "")
                st.session_state["cronograma_pdf_aviso_notificaciones"] = aviso_notificaciones
            st.rerun()
        except Exception as exc:
            st.error(f"No se pudo completar el guardado del cronograma: {exc}")

    if (st.session_state.get("cronograma_pdf") and st.session_state.get("cronograma_pdf_mes") == mes
            and st.session_state.get("cronograma_pdf_autor") == perfil["nombre"]):
        try:
            vigentes = [r for r in cargar_agenda_global(mes) if r["Especialista"] == perfil["nombre"]]
            if not vigentes:
                st.session_state.pop("cronograma_pdf", None)
                st.info("Este mes está guardado sin actividades.")
                return
            if st.session_state.get("cronograma_pdf_publicacion") != vigentes[-1].get("ID_Publicacion"):
                st.session_state.pop("cronograma_pdf", None)
                st.info("Hay una versión más reciente. Recarga el calendario guardado para consultarla.")
                return
        except Exception:
            st.caption("No se pudo verificar la versión del PDF. Reintenta antes de descargar.")
            return
        st.success(st.session_state.get("cronograma_pdf_mensaje", "PDF generado."))
        if not st.session_state.get("cronograma_pdf_firma_especialista"):
            st.warning(
                "No está configurada la imagen de firma personal de esta cuenta. "
                "El PDF conserva el espacio para firma; el visto bueno y el sello se agregan "
                "si sus imágenes están disponibles en la configuración."
            )
        if st.session_state.get("cronograma_pdf_aviso_historial"):
            st.warning(st.session_state["cronograma_pdf_aviso_historial"])
        if st.session_state.get("cronograma_pdf_aviso_notificaciones"):
            st.info(st.session_state["cronograma_pdf_aviso_notificaciones"])
        pendiente = st.session_state.get("cronograma_publicacion_pendiente")
        if pendiente and pendiente.get("especialista") == perfil["nombre"]:
            if st.button("Reintentar aviso a maestras de apoyo", key="reintentar_aviso_cronograma"):
                try:
                    notificadas = avisar_maestras_apoyo(
                        pendiente["id"], pendiente["especialista"], pendiente["mes"], pendiente["agenda"]
                    )
                    st.session_state["cronograma_pdf_aviso_notificaciones"] = f"Aviso registrado para {notificadas} maestra(s) de apoyo."
                    st.session_state["cronograma_publicacion_pendiente"] = None
                    st.rerun()
                except Exception as exc:
                    st.error(f"No fue posible registrar los avisos: {exc}")
        st.download_button(
            "Descargar PDF oficial",
            data=st.session_state["cronograma_pdf"],
            file_name=st.session_state.get("cronograma_pdf_nombre", "Cronograma.pdf"),
            mime="application/pdf",
            type="primary",
            width="stretch",
        )

    if perfil["area"] != "Dirección":
        return
    with st.expander("Calendario de todo el equipo", expanded=True):
        st.caption("Consulta las actividades publicadas por especialistas y Dirección para el mes seleccionado.")
        if st.button("Consultar agenda global del mes", key="consultar_agenda_global"):
            try:
                global_rows = cargar_agenda_global(mes)
                st.session_state["cronograma_global"] = global_rows
                st.session_state["cronograma_global_mes"] = mes
            except Exception as exc:
                st.error(f"No se pudo consultar el calendario global: {exc}")
        if st.session_state.get("cronograma_global_mes") == mes:
            global_rows = st.session_state.get("cronograma_global", [])
            if global_rows:
                vista = pd.DataFrame(global_rows).drop(columns=["ID_Publicacion"], errors="ignore")
                vista["Fecha"] = pd.to_datetime(vista["Fecha"]).dt.strftime("%d/%m/%Y")
                st.dataframe(vista, hide_index=True, width="stretch")
            else:
                st.info("No hay actividades guardadas para este mes.")
