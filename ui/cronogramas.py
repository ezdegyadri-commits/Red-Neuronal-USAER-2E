"""Interfaz del generador mensual de cronogramas para el equipo especialista."""

from __future__ import annotations

import json
import calendar
import re
import time
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
    meses_con_cronograma,
    perfil_especialista,
    lugares_cronograma,
)
from ui.calendario_eventos import eventos_mes, ventana_eventos, pendientes_mes
from services.horarios import avisar_maestras_apoyo
from services.borradores_cronogramas import cargar_borrador, guardar_borrador
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



def _respaldar_editor(prefijo):
    contexto = st.session_state.get(f"{prefijo}_respaldo")
    if not contexto:
        return
    nombre, mes = contexto
    dias = st.session_state.get(f"{prefijo}_dias", {})
    huella = json.dumps(dias, ensure_ascii=False, sort_keys=True)
    if st.session_state.get(f"{prefijo}_respaldado") == huella:
        return
    try:
        st.session_state[f"{prefijo}_respaldo_intento"] = time.monotonic()
        guardar_borrador(nombre, mes, dias)
        st.session_state[f"{prefijo}_respaldado"] = huella
        st.session_state.pop(f"{prefijo}_respaldo_pendiente", None)
    except Exception:
        st.session_state[f"{prefijo}_respaldo_pendiente"] = True


@st.fragment(run_every="60s")
def _estado_respaldo(prefijo):
    if (st.session_state.get(f"{prefijo}_respaldo_pendiente")
            and time.monotonic() - st.session_state.get(f"{prefijo}_respaldo_intento", -60) >= 60):
        _respaldar_editor(prefijo)
    if st.session_state.get(f"{prefijo}_respaldo_pendiente"):
        st.info("Respaldo pendiente. Mantén esta página abierta; reintentaremos automáticamente.")
    else:
        st.caption("Borrador respaldado al terminar de editar cada campo. Solo se publica al guardar el cronograma.")


@st.fragment(run_every="60s")
def _avisos_automaticos(perfil, mes):
    """La publicación central es la cola durable: recuperable en una sesión nueva."""
    key = f"cronograma_avisos_{perfil['nombre']}_{mes}"
    if time.monotonic() - st.session_state.get(key + "_intento", -60) < 60:
        return
    st.session_state[key + "_intento"] = time.monotonic()
    try:
        filas = [r for r in cargar_agenda_global(mes) if r["Especialista"] == perfil["nombre"]]
        if not filas:
            return
        publicacion = filas[-1].get("ID_Publicacion", "")
        if not publicacion or st.session_state.get(key + "_enviada") == publicacion:
            return
        avisar_maestras_apoyo(publicacion, perfil["nombre"], mes, [
            {"fecha": r["Fecha"], "escuela": r["Escuela"], "actividad": r["Actividad"]} for r in filas])
        st.session_state[key + "_enviada"] = publicacion
        st.session_state.pop("cronograma_publicacion_pendiente", None)
        st.session_state["cronograma_pdf_aviso_notificaciones"] = "Avisos registrados en la plataforma."
    except Exception:
        st.caption("El aviso sigue pendiente y se reintentará automáticamente. Tu calendario se conserva.")


def _actualizar_dia(prefijo, fecha):
    """Actualiza únicamente el borrador local; publicar exige el botón Guardar."""
    clave = f"{prefijo}_dias"
    dias = dict(st.session_state.get(clave, {}))
    escuela = st.session_state.get(f"{prefijo}_{fecha}_escuela", "")
    actividad = st.session_state.get(f"{prefijo}_{fecha}_actividad", "").strip()
    if escuela or actividad:
        dias[fecha] = {"escuela": escuela, "actividad": actividad}
    else:
        dias.pop(fecha, None)
    st.session_state[clave] = dias
    st.session_state.pop("cronograma_pdf", None)
    _respaldar_editor(prefijo)


def _mover_dia(prefijo, origen, destino):
    """No reemplaza una fecha ocupada ni escribe registros de producción."""
    dias = dict(st.session_state.get(f"{prefijo}_dias", {}))
    if not origen or not destino or origen == destino or origen not in dias:
        return
    if dias.get(destino, {}).get("escuela") or dias.get(destino, {}).get("actividad"):
        st.session_state[f"{prefijo}_error_mover"] = "La fecha elegida ya tiene actividad."
        return
    dias[destino] = dias.pop(origen)
    st.session_state[f"{prefijo}_dias"] = dias
    for fecha in (origen, destino):
        valor = dias.get(fecha, {})
        st.session_state[f"{prefijo}_{fecha}_escuela"] = valor.get("escuela", "")
        st.session_state[f"{prefijo}_{fecha}_actividad"] = valor.get("actividad", "")
    st.session_state.pop(f"{prefijo}_error_mover", None)
    st.session_state.pop("cronograma_pdf", None)
    _respaldar_editor(prefijo)


def _calendario_mes(mes, guardadas, escuelas=None, prefijo="", lectura=False, editable=True, lugares=None):
    """Campos dentro de cada día, sin botones de edición repetidos."""
    anio, numero = map(int, mes.split("-"))
    eventos = eventos_mes(mes)
    clave_borrador = f"{prefijo}_dias"
    if not lectura and clave_borrador not in st.session_state:
        st.session_state[clave_borrador] = {dia: dict(datos) for dia, datos in guardadas.items()}
    borrador = st.session_state.get(clave_borrador, {}) if not lectura else {}
    if not lectura:
        st.markdown("""
        <style>
        .stSelectbox [data-baseweb="select"] > div {height:auto;min-height:3rem;}
        .stSelectbox [data-baseweb="select"] > div > div:first-child {
            white-space:normal;overflow-wrap:break-word;text-overflow:clip;
        }
        [data-baseweb="popover"]:has([role="listbox"]) {
            min-width:min(420px,90vw);max-width:90vw;
        }
        [role="listbox"] [role="option"] {white-space:normal;height:auto;}
        [data-testid="stSelectboxVirtualDropdown"]:has([role="listbox"][aria-label="Escuela o junta"]) {
            width:min(400px,calc(100vw - 24px)) !important;
            max-width:calc(100vw - 24px);
        }
        [role="listbox"][aria-label="Escuela o junta"] [role="presentation"] {
            width:100% !important;
        }
        [role="listbox"][aria-label="Escuela o junta"] [role="option"] div {
            white-space:normal;text-overflow:clip;
        }
        </style>
        """, unsafe_allow_html=True)
    anchos = [0.55, 1, 1, 1, 1, 1, 0.55]
    for col, etiqueta in zip(st.columns(anchos), ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")):
        col.markdown(f"**{etiqueta}**")
    for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(anio, numero):
        for col, fecha in zip(st.columns(anchos), semana):
            iso = fecha.isoformat()
            motivo = DIAS_INHABILES.get(iso, "Fin de semana" if fecha.weekday() >= 5 else "")
            fuera = fecha.month != numero
            with col:
                with st.container(border=True):
                    color = "#f4f6f8" if fuera else ("#fff0d4" if "Consejo Técnico" in motivo else "#f9dddd" if motivo else "#eaf5f4")
                    etiqueta = "" if fuera else str(fecha.day)
                    st.markdown(f"<div style='background:{color};color:#183f46;border-radius:8px;padding:8px;text-align:right;font-weight:bold'>{etiqueta}</div>", unsafe_allow_html=True)
                    if fuera:
                        continue
                    ventana_eventos(iso, eventos)
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
                        opciones = ["", *(escuelas or []), *(lugares or [ESCUELA_JUNTA])]
                        anterior = next((e for e in opciones if normalizar_texto(e) == normalizar_texto(valor.get("escuela", ""))), "")
                        escuela = st.selectbox("Escuela o junta", opciones, index=opciones.index(anterior),
                            format_func=lambda e: "Junta · Sede USAER" if e == ESCUELA_JUNTA else e or "Elegir escuela",
                            key=f"{prefijo}_{iso}_escuela", disabled=not editable,
                            on_change=_actualizar_dia, args=(prefijo, iso), width="stretch")
                        if escuela:
                            # Nombre completo visible también en pantallas estrechas.
                            st.caption(escuela)
                        actividad = st.text_area("Actividad", value=valor.get("actividad", ""),
                            key=f"{prefijo}_{iso}_actividad", height=125, placeholder="¿Qué realizarás?",
                            disabled=not editable, on_change=_actualizar_dia, args=(prefijo, iso))
                        if escuela or actividad.strip():
                            borrador[iso] = {"escuela": escuela, "actividad": actividad.strip()}
                        else:
                            borrador.pop(iso, None)
    pendientes_mes(mes)
    if lectura:
        return []
    st.session_state[clave_borrador] = borrador
    if editable and borrador:
        with st.expander("Mover una actividad a otra fecha"):
            origen = st.selectbox("Actividad a mover", sorted(borrador),
                format_func=lambda d: date.fromisoformat(d).strftime("%d/%m/%Y"),
                key=f"{prefijo}_mover_origen")
            destinos = [d.isoformat() for d in fechas_habiles(mes) if d.isoformat() != origen]
            if destinos:
                destino = st.selectbox("Nueva fecha", destinos,
                    format_func=lambda d: date.fromisoformat(d).strftime("%d/%m/%Y"),
                    key=f"{prefijo}_mover_destino")
                st.button("Mover actividad", key=f"{prefijo}_mover",
                    on_click=_mover_dia, args=(prefijo, origen, destino))
                if st.session_state.get(f"{prefijo}_error_mover"):
                    st.info(st.session_state[f"{prefijo}_error_mover"])
    return [{"fecha": d, **datos} for d, datos in sorted(borrador.items())]


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


def _etiqueta_mes(mes):
    anio, numero = map(int, mes.split("-"))
    return f"{MESES[numero - 1].capitalize()} {anio}"


def _abrir_mes_guardado(nombre, mes):
    st.session_state[f"cronograma_mes_{nombre}"] = mes
    prefijo = f"cronograma_editor_{nombre}_{mes}"
    for clave in list(st.session_state):
        if clave.startswith(prefijo):
            st.session_state.pop(clave, None)
    st.session_state.pop(f"agenda_inicial_{nombre}_{mes}", None)
    cargar_agenda.clear()
    st.session_state[f"{prefijo}_editable"] = True
    st.session_state.pop("cronograma_pdf", None)


def _recuperar_cronogramas(perfil, historicos):
    """Consulta y PDF de la versión guardada de un mes, sin volver a publicarla."""
    clave = f"recuperar_cronogramas_{perfil['nombre']}"
    if st.button("Recuperar cronogramas de meses pasados", key=clave, width="stretch"):
        st.session_state[f"{clave}_abierto"] = not st.session_state.get(f"{clave}_abierto", False)
    if not st.session_state.get(f"{clave}_abierto"):
        return
    anteriores = [m for m in historicos if m < _mes_actual().strftime("%Y-%m")]
    if not anteriores:
        st.info("Todavía no hay cronogramas guardados de meses anteriores.")
        return
    with st.container(border=True):
        mes = st.selectbox("Mes guardado a recuperar", anteriores, format_func=_etiqueta_mes, key=f"{clave}_mes")
        try:
            agenda = cargar_agenda(perfil["nombre"], mes)
        except Exception:
            st.info("No se pudo recuperar este mes. Inténtalo de nuevo.")
            return
        agrupadas = {fecha: [{"Escuela": datos["escuela"], "Actividad": datos["actividad"]}]
                     for fecha, datos in agenda.items()}
        _calendario_mes(mes, agrupadas, lectura=True)
        huella = json.dumps(agenda, sort_keys=True)
        if agenda and st.button("Preparar PDF del mes recuperado", key=f"{clave}_preparar"):
            with st.spinner("Preparando tu cronograma..."):
                try:
                    firma, visto, sello = _recursos_firma(perfil)
                    pdf = generar_cronograma_pdf(_perfil_profesional(perfil), _etiqueta_mes(mes), [
                        {"fecha": date.fromisoformat(fecha).strftime("%d/%m/%Y"),
                         "escuela": datos["escuela"], "actividad": datos["actividad"]}
                        for fecha, datos in sorted(agenda.items())], firma, visto, sello)
                    st.session_state[f"{clave}_pdf"] = (mes, huella, pdf)
                except Exception:
                    st.info("No se pudo preparar el PDF. El cronograma sigue guardado.")
        archivo = st.session_state.get(f"{clave}_pdf")
        if archivo and archivo[:2] == (mes, huella):
            st.download_button("Descargar cronograma recuperado", archivo[2],
                f"Cronograma_{perfil['nombre']}_{mes}.pdf", "application/pdf", key=f"{clave}_descargar")
        if not agenda:
            st.caption("Este mes está guardado sin actividades.")
        st.button("Abrir mes recuperado para editar", key=f"{clave}_abrir",
                  on_click=_abrir_mes_guardado, args=(perfil["nombre"], mes))


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

    try:
        historicos = meses_con_cronograma(perfil["nombre"])
    except Exception:
        historicos = []
    disponibles = dict(_meses_disponibles())
    disponibles.update({mes: _etiqueta_mes(mes) for mes in historicos})
    meses = sorted(disponibles.items())
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

    if f"{editor_key}_respaldo" not in st.session_state:
        try:
            respaldo = cargar_borrador(perfil["nombre"], mes)
            if respaldo is not None:
                st.session_state[f"{editor_key}_dias"] = respaldo
                st.session_state[f"{editor_key}_respaldado"] = json.dumps(respaldo, ensure_ascii=False, sort_keys=True)
                if respaldo != agenda_guardada:
                    st.session_state[f"{editor_key}_editable"] = True
                    st.caption("Recuperamos tu borrador pendiente.")
            st.session_state[f"{editor_key}_respaldo"] = (perfil["nombre"], mes)
        except Exception:
            st.info("No se pudo recuperar el respaldo. Reintenta antes de comenzar otra edición.")
            return

    st.caption("Escuela y actividad en cada día. Rosa: inhábil · Amarillo: CTE.")
    clave_edicion = f"{editor_key}_editable"
    if clave_edicion not in st.session_state:
        st.session_state[clave_edicion] = not bool(agenda_guardada)
    if st.button("Editar cronograma", key=f"{editor_key}_editar", type="primary",
                 width="stretch", disabled=st.session_state[clave_edicion]):
        st.session_state[clave_edicion] = True
        st.rerun()
    if st.button("Actualizar calendario sin perder mi borrador", key=f"{editor_key}_recargar"):
        cargar_agenda.clear()
        st.session_state.pop(clave_agenda, None)
        st.session_state.pop("cronograma_pdf", None)
        st.rerun()
    agenda = _calendario_mes(mes, agenda_guardada, perfil["escuelas"], editor_key,
                             editable=st.session_state[clave_edicion], lugares=lugares_cronograma(perfil))
    _estado_respaldo(editor_key)
    _avisos_automaticos(perfil, mes)
    enviar = st.button("Guardar cambios y generar PDF", type="primary", width="stretch",
                       disabled=not st.session_state[clave_edicion])

    _recuperar_cronogramas(perfil, historicos)

    if enviar:
        try:
            _respaldar_editor(editor_key)
            with st.spinner("Guardando la agenda y preparando el PDF..."):
                resultado = guardar_agenda(perfil["nombre"], perfil["area"], mes, perfil["escuelas"], agenda)
                st.session_state[clave_agenda] = {r["fecha"]: {"escuela": r["escuela"], "actividad": r["actividad"]}
                                                for r in agenda}
                st.session_state[clave_edicion] = False
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
                        "Calendario guardado. Se conservaron los avisos ya registrados."
                    )
                    st.session_state["cronograma_publicacion_pendiente"] = None
                    st.session_state[f"cronograma_avisos_{perfil['nombre']}_{mes}_enviada"] = resultado.get("publicacion_id", "")
                except Exception as aviso_exc:
                    aviso_notificaciones = "Calendario guardado. El aviso pendiente se reintentará automáticamente."
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
                    st.info("El aviso sigue pendiente. Reintentaremos automáticamente; tu calendario se conserva.")
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
