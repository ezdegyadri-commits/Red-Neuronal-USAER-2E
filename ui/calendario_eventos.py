"""Calendario informativo compartido y publicación exclusiva de Dirección."""
import calendar
from datetime import date, datetime
from zoneinfo import ZoneInfo
from uuid import uuid4

import streamlit as st

from services.calendario_eventos import cargar_eventos, calendario_base, guardar_evento, desplazar_mes
from services.cronogramas import perfil_especialista


def eventos_mes(mes):
    try:
        return cargar_eventos(mes)
    except Exception:
        # Las actividades oficiales siguen disponibles si falla la base central.
        st.caption("Los eventos nuevos de Dirección no están disponibles por ahora.")
        return [e for e in calendario_base()["eventos"] if e["Fecha"].startswith(mes + "-")]


def ventana_eventos(fecha, eventos):
    items = [e for e in eventos if e["Fecha"] == fecha]
    if not items:
        return
    with st.popover(f"📌 {len(items)} aviso{'s' if len(items) != 1 else ''}", width="stretch"):
        st.caption(date.fromisoformat(fecha).strftime("%d/%m/%Y") + " · Informativo, no bloquea tu planeación")
        for e in items:
            st.write(e["Titulo"])
            if e.get("Origen") == "SEGEY":
                st.caption("SEGEY · Dirección de Educación Especial")
            elif e.get("Detalle"):
                st.caption(e["Detalle"])


def pendientes_mes(mes):
    for e in calendario_base().get("pendientes", []):
        if e["mes"] == mes:
            st.caption(f"Por definir: {e['titulo']} (sin fecha asignada).")


_MESES=('enero','febrero','marzo','abril','mayo','junio','julio','agosto','septiembre','octubre','noviembre','diciembre')


def _etiqueta(mes):
    anio,numero=map(int,mes.split('-'))
    return _MESES[numero-1]+' de '+str(anio)


def _mover_mes(clave,pasos):
    st.session_state[clave]=desplazar_mes(st.session_state[clave],pasos)


def _mes_hoy(clave):
    st.session_state[clave]=datetime.now(ZoneInfo('America/Mexico_City')).strftime('%Y-%m')


def selector_mes(mes,clave,label='Mes para consultar'):
    date.fromisoformat(mes+'-01')
    key=clave+'_mes_navegacion'
    if key not in st.session_state or st.session_state.get(clave+'_origen')!=mes:
        st.session_state[key]=mes;st.session_state[clave+'_origen']=mes
    actual=st.session_state[key]
    hoy=datetime.now(ZoneInfo('America/Mexico_City')).strftime('%Y-%m')
    opciones=sorted({desplazar_mes(hoy,i) for i in range(-12,25)}|{actual,mes})
    anterior,centro,siguiente=st.columns([1,3,1])
    anterior.button('◀ Mes anterior',key=clave+'_anterior',on_click=_mover_mes,args=(key,-1),disabled=actual=='1900-01',use_container_width=True)
    centro.selectbox(label,opciones,key=key,format_func=_etiqueta)
    siguiente.button('Mes siguiente ▶',key=clave+'_siguiente',on_click=_mover_mes,args=(key,1),disabled=actual=='2100-12',use_container_width=True)
    st.button('Volver al mes actual',key=clave+'_hoy',on_click=_mes_hoy,args=(key,))
    return st.session_state[key]


def calendario_informativo(mes,clave='calendario_comun',navegable=True):
    st.markdown("#### Actividades del mes · USAER")
    if navegable:mes=selector_mes(mes,clave)
    st.markdown('##### '+_etiqueta(mes).capitalize())
    st.caption("Abre los avisos del día para ver los detalles. No modifican tu horario.")
    eventos = eventos_mes(mes)
    anio, numero = map(int, mes.split("-"))
    for col, nombre in zip(st.columns(7), ("Dom", "Lun", "Mar", "Mié", "Jue", "Vie", "Sáb")):
        col.caption(nombre)
    for semana in calendar.Calendar(firstweekday=6).monthdatescalendar(anio, numero):
        for col, fecha in zip(st.columns(7), semana):
            with col:
                with st.container(border=True):
                    if fecha.month == numero:
                        st.write(str(fecha.day))
                        ventana_eventos(fecha.isoformat(), eventos)
                    else:
                        st.caption("—")
    pendientes_mes(mes)
    if not eventos:st.caption('No hay actividades publicadas para este mes.')
    return mes


def eventos_direccion():
    perfil = perfil_especialista(st.session_state.get("nombre", ""), st.session_state.get("rol", ""))
    if not st.session_state.get('autenticado') or not perfil or perfil["area"] != "Dirección":
        st.error("Apartado exclusivo de Dirección.")
        return
    st.subheader("Publicar actividades para todo el equipo")
    st.caption("Visibles para especialistas y maestras de apoyo. Son avisos informativos, no bloqueos.")
    hoy = datetime.now(ZoneInfo("America/Mexico_City")).date()
    mes=selector_mes(hoy.strftime('%Y-%m'),'eventos_director',label='Mes de actividades')
    mes_fecha=date.fromisoformat(mes+'-01')
    mensaje=st.session_state.pop('evento_director_confirmado','')
    if mensaje:st.success('Actividad publicada para todo el equipo: '+mensaje)
    try:
        eventos = cargar_eventos(mes)
    except Exception:
        st.info("No se pudieron consultar los eventos. Reintenta en un momento.")
        return
    seleccionado = st.selectbox("Añadir o actualizar", [None, *eventos],
        format_func=lambda e: "Nueva actividad" if e is None else f"{e['Fecha'][8:]} · {e['Titulo']}",
        key="evento_director_elegido_"+mes)
    clave_nuevo='evento_director_nuevo_id_'+mes
    identificador = seleccionado["ID_Evento"] if seleccionado else st.session_state.setdefault(clave_nuevo, uuid4().hex)
    version = seleccionado.get("Revision", "base") if seleccionado else "nuevo"
    with st.form(f"publicar_evento_{identificador}_{version}"):
        fecha = st.date_input("Fecha de la actividad", value=date.fromisoformat(seleccionado["Fecha"]) if seleccionado else mes_fecha)
        titulo = st.text_input("Actividad", value=seleccionado["Titulo"] if seleccionado else "", max_chars=300)
        detalle = st.text_area("Detalles (opcional)", value=seleccionado.get("Detalle", "") if seleccionado else "", max_chars=3000)
        publicar = st.form_submit_button("Publicar actividad para todos", type="primary", width="stretch")
    if publicar:
        try:
            guardar_evento(fecha, titulo, detalle, identificador, seleccionado.get("Revision", "base") if seleccionado else None)
            st.session_state.pop(clave_nuevo, None)
            st.session_state['evento_director_confirmado']=titulo
            st.rerun()
        except (ValueError, PermissionError) as exc:
            st.info(str(exc))
        except Exception:
            st.error("No se pudo publicar la actividad. Inténtalo de nuevo.")
    calendario_informativo(mes,clave='eventos_director_vista',navegable=False)


def calendario_page():
    if not st.session_state.get('autenticado'):
        st.error('Inicia sesión para consultar el calendario.');return
    st.title('Calendario de actividades')
    st.caption('Actividades comunes de la USAER. Explora otros meses y abre los avisos de cada día; no cambian tu horario ni tu planeación.')
    perfil=perfil_especialista(st.session_state.get('nombre',''),st.session_state.get('rol',''))
    if perfil and perfil['area']=='Dirección':eventos_direccion()
    else:
        mes=datetime.now(ZoneInfo('America/Mexico_City')).strftime('%Y-%m')
        calendario_informativo(mes,clave='calendario_personal')
