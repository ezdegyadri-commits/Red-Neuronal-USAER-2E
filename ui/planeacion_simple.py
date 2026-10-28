"""Recorrido breve sobre los servicios canónicos; no crea otra persistencia."""
from copy import deepcopy
from datetime import datetime
from zoneinfo import ZoneInfo
import json
import pandas as pd
import streamlit as st
from services import planeacion as s, planeacion_equipo as equipo
from services.planeacion_modalidad import modalidad, GUIA_XIX, GUIA_XX, guia_grupal
from utils.escolar import grado_canonico
from ui.planeacion_pendientes import raiz
from services.planeacion_modelo import FORMATOS

PASOS=('1. ¿A quién planeo?', '2. Preparar con IA', '3. Revisar y enviar')


def _inyectar_estilos_planeacion():
    st.html('''
    <style>
    /* Estilos Institucionales Premium USAER 02-E */
    :root {
        --usaer-navy: #0F2D59;
        --usaer-navy-light: #1E3A8A;
        --usaer-teal: #0D9488;
        --usaer-teal-light: #14B8A6;
        --usaer-teal-bg: #F0FDFA;
        --usaer-gold: #D97706;
        --usaer-slate: #334155;
        --usaer-emerald: #059669;
    }

    /* Lienzo de Documento Oficial */
    .usaer-canvas-card {
        background: #FFFFFF;
        border: 1.5px solid #CBD5E1;
        border-radius: 14px;
        box-shadow: 0 6px 24px rgba(15, 45, 89, 0.08);
        padding: 1.5rem 1.75rem;
        margin-bottom: 1.5rem;
    }
    .usaer-official-header {
        border-bottom: 2.5px solid #0F2D59;
        padding-bottom: 0.75rem;
        margin-bottom: 1.15rem;
        text-align: center;
    }
    .usaer-sub-badge {
        font-size: 0.74rem;
        font-weight: 750;
        letter-spacing: 0.08em;
        text-transform: uppercase;
        color: #475569;
        margin-bottom: 0.2rem;
    }
    .usaer-main-title {
        font-size: 1.28rem;
        font-weight: 800;
        color: #0F2D59;
        margin: 0.25rem 0;
        letter-spacing: -0.01em;
    }
    .usaer-annex-badge {
        display: inline-block;
        background: linear-gradient(135deg, #0F2D59 0%, #0D9488 100%);
        color: #FFFFFF !important;
        font-size: 0.86rem;
        font-weight: 700;
        padding: 0.35rem 0.95rem;
        border-radius: 8px;
        margin-top: 0.4rem;
        letter-spacing: 0.03em;
        box-shadow: 0 2px 8px rgba(13, 148, 136, 0.25);
    }
    .usaer-meta-table {
        width: 100%;
        border-collapse: separate;
        border-spacing: 0;
        font-size: 0.88rem;
        margin-bottom: 0.85rem;
        border-radius: 8px;
        overflow: hidden;
        border: 1px solid #E2E8F0;
    }
    .usaer-meta-table td {
        padding: 0.55rem 0.75rem;
        border-bottom: 1px solid #E2E8F0;
        border-right: 1px solid #E2E8F0;
    }
    .usaer-meta-table tr:last-child td { border-bottom: none; }
    .usaer-meta-table td:last-child { border-right: none; }
    .usaer-meta-label {
        font-weight: 700;
        color: #0F2D59;
        background-color: #F8FAFC;
        width: 22%;
    }

    /* ========================================================================== */
    /* BOTONES GRANDES, AMABLES, VISIBLES Y PROFESIONALES                         */
    /* ========================================================================== */

    /* Herencia de color y estilo para textos internos en botones de Streamlit */
    div[data-testid="stButton"] button p,
    div[data-testid="stDownloadButton"] button p,
    div.stButton > button p,
    div.stDownloadButton > button p {
        color: inherit !important;
        font-size: inherit !important;
        font-weight: inherit !important;
        line-height: inherit !important;
        margin: 0 !important;
        letter-spacing: inherit !important;
    }

    /* Base para todos los botones del módulo: grandes, amables y táctiles */
    div.stButton > button,
    div.stDownloadButton > button {
        border-radius: 13px !important;
        font-weight: 700 !important;
        font-size: 1.02rem !important;
        letter-spacing: 0.01em !important;
        min-height: 50px !important;
        padding: 0.75rem 1.45rem !important;
        transition: all 0.2s cubic-bezier(0.16, 1, 0.3, 1) !important;
        box-shadow: 0 2px 8px rgba(15, 45, 89, 0.08) !important;
        cursor: pointer !important;
        display: inline-flex !important;
        align-items: center !important;
        justify-content: center !important;
        gap: 0.55rem !important;
    }

    /* Hover general con elevación agradable */
    div.stButton > button:hover,
    div.stDownloadButton > button:hover {
        transform: translateY(-2px) !important;
        box-shadow: 0 6px 20px rgba(15, 45, 89, 0.16) !important;
    }

    div.stButton > button:active,
    div.stDownloadButton > button:active {
        transform: translateY(0) !important;
        box-shadow: 0 2px 4px rgba(15, 45, 89, 0.1) !important;
    }

    /* 1. Botones Primarios (Llamados a la Acción Fuertes: Crear, Guardar, etc.) */
    div.stButton > button[kind="primary"],
    div.stButton > button[data-testid="baseButton-primary"] {
        background: linear-gradient(135deg, #0F4C5C 0%, #0D9488 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.06rem !important;
        font-weight: 800 !important;
        min-height: 52px !important;
        padding: 0.85rem 1.65rem !important;
        box-shadow: 0 4px 16px rgba(13, 148, 136, 0.35) !important;
    }
    div.stButton > button[kind="primary"]:hover,
    div.stButton > button[data-testid="baseButton-primary"]:hover {
        background: linear-gradient(135deg, #0A3742 0%, #0B7A6F 100%) !important;
        box-shadow: 0 8px 25px rgba(13, 148, 136, 0.48) !important;
        transform: translateY(-2px) scale(1.01) !important;
    }

    /* 2. Botones Secundarios / Estándar (Blanco Perlado con Borde Definido) */
    div.stButton > button[kind="secondary"],
    div.stButton > button[data-testid="baseButton-secondary"] {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        color: #0F2D59 !important;
        border: 1.5px solid #CBD5E1 !important;
    }
    div.stButton > button[kind="secondary"]:hover,
    div.stButton > button[data-testid="baseButton-secondary"]:hover {
        background: #F0FDFA !important;
        border-color: #0D9488 !important;
        color: #0D9488 !important;
    }

    /* 3. Botones del Asistente Inteligente (Conectividad en 1 Clic: Menta/Teal Amigable) */
    div[class*="st-key-"][class*="_asist_"] button,
    div[class*="st-key-"][class*="_step2_usar_"] button {
        background: linear-gradient(135deg, #F0FDFA 0%, #E6FFFA 100%) !important;
        border: 1.5px solid #0D9488 !important;
        color: #0F766E !important;
        font-weight: 750 !important;
        font-size: 0.98rem !important;
        min-height: 48px !important;
        padding: 0.7rem 1.35rem !important;
        box-shadow: 0 2px 8px rgba(13, 148, 136, 0.14) !important;
    }
    div[class*="st-key-"][class*="_asist_"] button:hover,
    div[class*="st-key-"][class*="_step2_usar_"] button:hover {
        background: linear-gradient(135deg, #0D9488 0%, #0F766E 100%) !important;
        color: #FFFFFF !important;
        border-color: #0F766E !important;
        box-shadow: 0 6px 18px rgba(13, 148, 136, 0.35) !important;
        transform: translateY(-2px) scale(1.01) !important;
    }

    /* 4. Botones de Continuar en tarjetas de borradores previos (Azul Royal) */
    div[class*="st-key-"][class*="_continuar_"] button {
        background: linear-gradient(135deg, #EFF6FF 0%, #DBEAFE 100%) !important;
        border: 1.5px solid #3B82F6 !important;
        color: #1D4ED8 !important;
        font-size: 1.0rem !important;
        font-weight: 750 !important;
        min-height: 48px !important;
        box-shadow: 0 2px 8px rgba(59, 130, 246, 0.16) !important;
    }
    div[class*="st-key-"][class*="_continuar_"] button:hover {
        background: linear-gradient(135deg, #2563EB 0%, #1D4ED8 100%) !important;
        color: #FFFFFF !important;
        border-color: #1D4ED8 !important;
        box-shadow: 0 6px 18px rgba(37, 99, 235, 0.35) !important;
    }

    /* 5. Barra Flotante de Acciones (Bottom Action Dock) */
    div[class*="st-key-"][class*="_acciones"] {
        position: sticky !important;
        bottom: 0 !important;
        z-index: 99 !important;
        background: rgba(255, 255, 255, 0.96) !important;
        backdrop-filter: blur(12px) !important;
        -webkit-backdrop-filter: blur(12px) !important;
        border-top: 2.5px solid #0D9488 !important;
        box-shadow: 0 -8px 25px rgba(15, 45, 89, 0.12) !important;
        border-radius: 16px 16px 0 0 !important;
        padding: 0.85rem 1.4rem !important;
    }

    /* Guardar Borrador (Azul Marino / Real Confiable) */
    div[class*="st-key-"][class*="_simple_save"] button {
        background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.04rem !important;
        font-weight: 800 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 14px rgba(37, 99, 235, 0.32) !important;
    }
    div[class*="st-key-"][class*="_simple_save"] button:hover {
        background: linear-gradient(135deg, #172554 0%, #1D4ED8 100%) !important;
        box-shadow: 0 8px 22px rgba(37, 99, 235, 0.45) !important;
        transform: translateY(-2px) !important;
    }
    div[class*="st-key-"][class*="_simple_save"] button::before {
        content: "💾";
        font-size: 1.15rem;
    }

    /* Ver PDF (Verde Azulado Institucional) */
    div[class*="st-key-"][class*="_simple_pdf"] button {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.04rem !important;
        font-weight: 800 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 14px rgba(13, 148, 136, 0.32) !important;
    }
    div[class*="st-key-"][class*="_simple_pdf"] button:hover {
        background: linear-gradient(135deg, #115E59 0%, #0F766E 100%) !important;
        box-shadow: 0 8px 22px rgba(13, 148, 136, 0.45) !important;
        transform: translateY(-2px) !important;
    }
    div[class*="st-key-"][class*="_simple_pdf"] button::before {
        content: "📄";
        font-size: 1.15rem;
    }

    /* Enviar a Dirección (Esmeralda Triunfal y Claro) */
    div[class*="st-key-"][class*="_simple_send"] button {
        background: linear-gradient(135deg, #059669 0%, #10B981 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-size: 1.08rem !important;
        font-weight: 850 !important;
        min-height: 52px !important;
        box-shadow: 0 4px 16px rgba(16, 185, 129, 0.38) !important;
    }
    div[class*="st-key-"][class*="_simple_send"] button:hover {
        background: linear-gradient(135deg, #047857 0%, #059669 100%) !important;
        box-shadow: 0 8px 25px rgba(16, 185, 129, 0.52) !important;
        transform: translateY(-2px) !important;
    }
    div[class*="st-key-"][class*="_simple_send"] button::before {
        content: "🚀";
        font-size: 1.15rem;
    }
    div[class*="st-key-"][class*="_simple_send"] button:disabled {
        background: #E2E8F0 !important;
        color: #94A3B8 !important;
        box-shadow: none !important;
        transform: none !important;
        cursor: not-allowed !important;
    }

    /* Descargar Respaldo Editable (Ámbar / Oro Institucional) */
    div[class*="st-key-"][class*="_bar_backup"] button,
    div[class*="st-key-"][class*="_simple_backup"] button {
        background: linear-gradient(180deg, #FFFFFF 0%, #FFFBEB 100%) !important;
        border: 1.5px solid #F59E0B !important;
        color: #B45309 !important;
        font-size: 1.0rem !important;
        font-weight: 750 !important;
        min-height: 52px !important;
        box-shadow: 0 2px 8px rgba(245, 158, 11, 0.14) !important;
    }
    div[class*="st-key-"][class*="_bar_backup"] button:hover,
    div[class*="st-key-"][class*="_simple_backup"] button:hover {
        background: linear-gradient(135deg, #F59E0B 0%, #D97706 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 18px rgba(217, 119, 6, 0.35) !important;
        transform: translateY(-2px) !important;
    }
    div[class*="st-key-"][class*="_bar_backup"] button::before,
    div[class*="st-key-"][class*="_simple_backup"] button::before {
        content: "📥";
        font-size: 1.15rem;
    }

    /* Botón Hero de transición a Paso 3 */
    div[class*="st-key-"][class*="_ir_paso3"] button {
        min-height: 58px !important;
        font-size: 1.15rem !important;
        font-weight: 850 !important;
        border-radius: 14px !important;
        letter-spacing: 0.02em !important;
        background: linear-gradient(135deg, #0F4C5C 0%, #0D9488 100%) !important;
        color: #FFFFFF !important;
        box-shadow: 0 6px 22px rgba(13, 148, 136, 0.38) !important;
    }
    div[class*="st-key-"][class*="_ir_paso3"] button:hover {
        background: linear-gradient(135deg, #0B3B48 0%, #0B7A6F 100%) !important;
        box-shadow: 0 10px 30px rgba(13, 148, 136, 0.52) !important;
        transform: translateY(-2px) scale(1.01) !important;
    }

    /* Volver a editar tras previsualizar PDF */
    div[class*="st-key-"][class*="_simple_hidepdf"] button {
        background: #F8FAFC !important;
        border: 1.5px solid #0D9488 !important;
        color: #0D9488 !important;
        font-weight: 750 !important;
        font-size: 1.0rem !important;
        min-height: 48px !important;
    }
    div[class*="st-key-"][class*="_simple_hidepdf"] button:hover {
        background: #F0FDFA !important;
        color: #0F766E !important;
    }
    div[class*="st-key-"][class*="_simple_hidepdf"] button::before {
        content: "✏️ ";
        font-size: 1.05rem;
    }

    /* Descargar PDF */
    div[class*="st-key-"][class*="_simple_download"] button {
        background: linear-gradient(135deg, #BE123C 0%, #E11D48 100%) !important;
        color: #FFFFFF !important;
        border: none !important;
        font-weight: 800 !important;
        font-size: 1.04rem !important;
        min-height: 52px !important;
        box-shadow: 0 4px 16px rgba(225, 29, 72, 0.35) !important;
    }
    div[class*="st-key-"][class*="_simple_download"] button:hover {
        background: linear-gradient(135deg, #9F1239 0%, #BE123C 100%) !important;
        box-shadow: 0 8px 24px rgba(225, 29, 72, 0.48) !important;
        transform: translateY(-2px) !important;
    }
    div[class*="st-key-"][class*="_simple_download"] button::before {
        content: "📥 ";
        font-size: 1.15rem;
    }

    /* Guardar datos Anexo XX */
    div[class*="st-key-"][class*="_as_save_btn"] button {
        background: linear-gradient(135deg, #0F766E 0%, #0D9488 100%) !important;
        color: #FFFFFF !important;
        font-weight: 750 !important;
        min-height: 48px !important;
        box-shadow: 0 2px 8px rgba(13, 148, 136, 0.2) !important;
    }

    /* Editar planeación en historial de borradores */
    div[class*="st-key-"][class*="_editar_"] button {
        background: linear-gradient(180deg, #FFFFFF 0%, #F8FAFC 100%) !important;
        border: 1.5px solid #94A3B8 !important;
        color: #334155 !important;
        font-size: 0.96rem !important;
        font-weight: 700 !important;
        min-height: 46px !important;
    }
    div[class*="st-key-"][class*="_editar_"] button:hover {
        background: #F1F5F9 !important;
        border-color: #64748B !important;
        color: #0F172A !important;
    }

    /* Actualizar matrícula y refrescar documentos */
    div[class*="st-key-"][class*="_refrescar"] button,
    div[class*="st-key-"][class*="_simple_fuentes"] button {
        background: #FFFFFF !important;
        border: 1.5px solid #0D9488 !important;
        color: #0D9488 !important;
        font-weight: 700 !important;
        min-height: 46px !important;
    }
    div[class*="st-key-"][class*="_refrescar"] button:hover,
    div[class*="st-key-"][class*="_simple_fuentes"] button:hover {
        background: #F0FDFA !important;
        color: #0F766E !important;
    }
    </style>
    ''')


def periodo_actual(hoy=None):
    hoy=hoy or datetime.now(ZoneInfo('America/Mexico_City')).date()
    return hoy.year if hoy.month>=8 else hoy.year-1, 2 if hoy.month<=3 else 3 if hoy.month<=6 else 1


def seleccion(frame,ids,incluir=False):
    """Presentación de la modalidad. La autorización definitiva sigue en nueva()."""
    rows=frame.loc[frame['ID_Alumno'].astype(str).isin(ids)].to_dict('records')
    if len(rows)!=len(set(ids)):raise ValueError('Revisa los alumnos de tu matrícula.')
    tipos={modalidad(r) for r in rows}
    if not tipos or 'por confirmar' in tipos:raise ValueError('Para continuar, este alumno requiere tener asignada su modalidad de atención (individual o grupal) en el padrón.')
    if tipos=={'individual'} and not incluir:return 'individual'
    if 'individual' in tipos and not incluir:raise ValueError('Para reunir alumnos individuales, activa la opción avanzada de sesión grupal.')
    return 'grupal'


def _abrir(base,prefix,doc):
    from ui import planeacion as u
    from ui.planeacion_pendientes import pendientes
    local=next((p for p in pendientes(base) if st.session_state[p+'_doc'].get('id')==doc.get('id')),None)
    if local:
        st.session_state[base+'_activa']=local
        st.session_state[base+'_viva_entrada']=False
        return local
    previo=st.session_state.get(prefix+'_doc')
    if previo and st.session_state.get(prefix+'_pending'):
        if previo.get('id')==doc.get('id'):
            st.session_state[base+'_activa']=prefix
            st.session_state[base+'_viva_entrada']=False
            return prefix
        from ui.planeacion_pendientes import conservar
        conservar(prefix,base)
    u._open(prefix,doc)
    st.session_state[prefix+'_mostrar_pdf']=False
    st.session_state[base+'_activa']=prefix
    st.session_state[base+'_viva_entrada']=False
    st.session_state[base+'_paso_pendiente']=PASOS[2] if doc.get('metadatos',{}).get('generacion_completa') or doc.get('metadatos',{}).get('preparacion_local') else PASOS[1]
    return prefix


def crear_borrador(base,fmt,ids,ciclo,trimestre,tipo,incluir=False,presentacion=None,proponer_apartados=False,nuevo_independiente=False,todos_grupos=False,anual=False):
    """Las dos vistas comparten creación, protección de pendientes y contexto."""
    from ui import planeacion as u
    if tipo in ('individual','especialista') and not nuevo_independiente:
        from services.planeacion_recuperacion import equivalentes
        frame=s.padron_autorizado()
        elegidos=frame.loc[frame['ID_Alumno'].astype(str).isin(set(map(str,ids)))]
        if len(elegidos)!=len(set(map(str,ids))) or elegidos['ID_Escuela'].nunique()!=1:
            raise PermissionError('Selecciona alumnos autorizados de una misma escuela.')
        existentes=equivalentes(s.listar(),s.identidad(),fmt,ids,elegidos.iloc[0]['ID_Escuela'],ciclo,trimestre,tipo)
        if existentes:
            # Abrir el avance confirmado, no guardar una copia de la plantilla.
            return _abrir(base,base+'_'+tipo,existentes[0])
    with st.spinner('Reuniendo la información que ya registró el equipo…'):
        solicitud='especialista' if tipo=='grupal' and s.identidad()['area'] in ('Comunicación','Psicología','Trabajo Social') else tipo
        parametros={'anual':True} if anual else {}
        doc=s.nueva(fmt,ids,int(ciclo),trimestre,modalidad=solicitud,incluir_individuales=incluir,vista_formato=presentacion,todos_grupos=todos_grupos,**parametros)
        existente=bool(doc.get('revision'))
        if not existente or doc['metadatos'].pop('contexto_matricula_pendiente',False):doc=s.preparar_contexto(doc)
        if equipo.aplica(doc) and not doc['metadatos'].get('equipo',{}).get('subgrupos'):
            doc=equipo.guardar_subgrupo(equipo.preparar(doc),'Subgrupo 1',ids)
        if fmt=='XXI' and any(v['tipo']=='EPP' for v in doc['metadatos'].get('vinculos_documentales',[])):
            from services.planeacion_continuidad import trasladar_epp
            doc=trasladar_epp(doc)
    if proponer_apartados and not existente:
        from services.planeacion_apartados import proponer
        doc=proponer(doc)
    if presentacion in ('guia','trimestral'):doc['metadatos']['vista_formato']=presentacion
    modalidad_actual=doc['metadatos'].get('modalidad_planeacion') or tipo
    prefix=_abrir(base,base+'_'+modalidad_actual,doc);u._persist(prefix)
    return prefix


def _entrada(base,actor):
    from ui import planeacion as u
    st.subheader(PASOS[0])
    try:docs=[d for d in s.listar() if d['cuenta']==actor['cuenta']]
    except Exception:
        docs=[];st.warning('No se pudieron consultar los borradores guardados. La edición abierta se conserva.')
    st.markdown('#### Continuar donde me quedé')
    if docs:
        pagina=st.number_input('Página de mis documentos',1,max(1,(len(docs)+4)//5),1,key=base+'_pagina_docs') if len(docs)>5 else 1
        for doc in sorted(docs,key=lambda d:d.get('guardado_en',''),reverse=True)[(pagina-1)*5:pagina*5]:
            with st.container(border=True):
                st.write(doc['datos']['Escuela regular']+' · '+', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos']))
                st.caption({'CON_OBSERVACIONES':'Por ajustar','BORRADOR':'Borrador','ENVIADO':'Enviado','VALIDADO':'Revisado'}.get(doc['estado'],doc['estado'])+' · '+doc['datos'].get('Periodo',''))
                if st.button('Continuar',key=base+'_continuar_'+doc['id']):
                    try:
                        from services.planeacion_modalidad import modalidad_documento
                        _abrir(base,base+'_'+modalidad_documento(doc,s.padron_autorizado()),doc);st.rerun()
                    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
                if st.button('Editar planeación',key=base+'_editar_'+doc['id']):
                    try:
                        from ui.planeacion_edicion import abrir_guardada
                        abrir_guardada(base,doc);st.rerun()
                    except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
    else:st.caption('Tus borradores aparecerán aquí después del primer guardado confirmado.')
    with st.expander('Recuperar un respaldo o consultar ayuda'):
        if st.button('Actualizar mis documentos',key=base+'_simple_refrescar'):
            s.refrescar();st.rerun()
        _recuperar(base)
        from ui.planeacion_ayuda import panel
        panel(actor['area'])
    st.markdown('#### Nueva planeación')
    if st.button('Actualizar matrícula disponible',key=base+'_refrescar_matricula'):
        s.refrescar_matricula();st.rerun()
    frame=s.padron_autorizado()
    if frame.empty:st.info('No hay alumnos asignados disponibles.');return
    escuelas=frame[['ID_Escuela','Nombre_Escuela']].drop_duplicates().to_dict('records')
    indice=st.selectbox('Escuela asignada',range(len(escuelas)),format_func=lambda i:escuelas[i]['Nombre_Escuela'],key=base+'_escuela') if len(escuelas)>1 else 0
    escolar=frame.loc[frame['ID_Escuela'].astype(str)==str(escuelas[indice]['ID_Escuela'])]
    individuales=sum(modalidad(r)=='individual' for r in escolar.to_dict('records'))
    grupales=sum(modalidad(r)=='grupal' for r in escolar.to_dict('records'))
    st.caption(f'{len(escolar)} alumnos disponibles · {individuales} individuales · {grupales} grupales. Abre el selector para elegir.')
    etiquetas={str(r['ID_Alumno']):str(r['Nombre_Completo'])+' · '+str(r.get('Grado',''))+' '+str(r.get('Grupo','')) for r in escolar.to_dict('records')}
    ids=st.multiselect('Alumno o alumnos para planear',list(etiquetas),format_func=etiquetas.get,key=base+'_alumnos_'+str(escuelas[indice]['ID_Escuela']))
    pendientes_mod=[r for r in escolar.to_dict('records') if modalidad(r)=='por confirmar']
    if pendientes_mod:st.caption(f'Nota: {len(pendientes_mod)} alumno(s) tienen pendiente registrar su modalidad de atención en el padrón.')
    ciclo,trimestre=periodo_actual();incluir=False
    with st.expander('Cambiar periodo u organizar una sesión grupal especial'):
        ciclo=st.number_input('Inicio del ciclo escolar',2020,2040,ciclo,key=base+'_ciclo')
        trimestre=st.selectbox('Trimestre',[1,2,3],index=trimestre-1,key=base+'_trimestre')
        incluir=st.checkbox('Incluir alumnos de atención individual en esta sesión grupal',key=base+'_incluir')
    st.caption(f'Curso {ciclo}–{ciclo+1} · Trimestre {trimestre}. La modalidad se toma del padrón; no lo modifica.')
    tipo=None
    if ids:
        try:tipo=seleccion(escolar,ids,incluir)
        except ValueError as exc:st.info(str(exc))
    fmt='XXV' if actor['area']=='Trabajo Social' else 'XXIII'
    if tipo=='individual' and len(ids)==1 and actor['area']=='Aprendizaje' and not actor['director']:
        opcion=st.segmented_control('¿Qué documento necesitas?', ['Planeación trimestral','Plan de intervención'],default='Planeación trimestral',key=base+'_formato')
        fmt='XXI' if opcion=='Plan de intervención' else 'XXIII'
    if st.button('Crear mi borrador',type='primary',disabled=not tipo,key=base+'_crear'):
        try:
            crear_borrador(base,fmt,ids,ciclo,trimestre,tipo,incluir);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def _herramientas(prefix,actor):
    from ui import planeacion as u
    doc=st.session_state[prefix+'_doc']
    herramienta=st.selectbox('Herramienta que necesito',['Elige una herramienta','Materiales y escaneos','Referentes oficiales','Evidencias del expediente','Conexiones y seguimiento','Organizar sesiones del equipo','Ideas adicionales con IA','Respaldo y versiones','Guía grupal XIX / XX','Ayuda paso a paso'],key=prefix+'_herramienta')
    if herramienta=='Materiales y escaneos':u._materiales(prefix,doc)
    elif herramienta=='Referentes oficiales':u._curriculo(prefix,doc)
    elif herramienta=='Evidencias del expediente':
        if st.button('Actualizar información del expediente',key=prefix+'_simple_fuentes'):
            try:s.refrescar_evidencias();u._open(prefix,s.preparar_contexto(doc));u._persist(prefix);st.rerun()
            except Exception:st.warning('No se confirmó la actualización. Tu edición se conserva.')
        for i, fuente in enumerate(doc['metadatos'].get('fuentes',[])):
            with st.expander(fuente['referencia']+' · '+fuente['tipo']):
                st.write(fuente['texto']);st.caption('Ya se considera si su vínculo con estos alumnos está verificado.')
                if st.button('➕ Usar en mi planeación', key=f'{prefix}_tool_usar_{i}'):
                    try:
                        from services.planeacion_formato import usar_evidencia
                        actualizado=usar_evidencia(st.session_state[prefix+'_doc'],fuente)
                        u._open(prefix,actualizado);u._persist(prefix);st.success('¡Agregado a tu borrador!');st.rerun()
                    except Exception as exc:st.info(str(exc))
    elif herramienta=='Conexiones y seguimiento':
        from ui.planeacion_continuidad import panel
        panel(prefix,u._open,u._persist)
    elif herramienta=='Organizar sesiones del equipo':
        from ui.planeacion_equipo import panel
        panel(prefix,doc,u._persist,u._open,compact=True)
    elif herramienta=='Ideas adicionales con IA':u._ai(prefix,doc)
    elif herramienta=='Respaldo y versiones':_respaldo(prefix,doc)
    elif herramienta=='Guía grupal XIX / XX':
        _guia_adicional(prefix,doc)
    elif herramienta=='Ayuda paso a paso':
        from ui.planeacion_ayuda import panel
        panel(actor['area'])


def _respaldo(prefix,doc):
    from ui import planeacion as u
    st.download_button('Descargar respaldo editable',json.dumps(doc,ensure_ascii=False,indent=2),file_name='planeacion-'+doc['id']+'.json',mime='application/json',key=prefix+'_simple_backup')
    base=raiz(prefix)
    if st.session_state.get(prefix+'_pending'):
        st.warning('Descarga el respaldo antes de conciliar una edición pendiente con otra versión.')
        confirmar=st.checkbox('Ya respaldé mi edición y quiero conservarla para conciliar',key=prefix+'_simple_resguardar_confirm')
        if st.button('Conservar edición pendiente para conciliar',disabled=not confirmar,key=prefix+'_simple_resguardar'):
            u._resguardar_pendiente(prefix);st.rerun()
    for p in (base+'_individual',base+'_grupal'):
        for firma,resguardo in st.session_state.get(p+'_resguardos',{}).items():
            st.download_button('Descargar edición conservada para conciliar',json.dumps(resguardo,ensure_ascii=False),file_name='planeacion-conciliar-'+resguardo['id']+'.json',mime='application/json',key=p+'_simple_resguardo_'+firma)
    _recuperar(base)
    if st.toggle('Consultar versiones anteriores',key=prefix+'_simple_history'):
        for history in s.listar(True):
            if history['id']==doc['id']:
                st.download_button(history['guardado_en'][:19]+' · '+history['estado'],json.dumps(history,ensure_ascii=False),file_name=history['revision']+'.json',mime='application/json',key=prefix+'_simple_version_'+history['revision'])


def _recuperar(base):
    from ui import planeacion as u
    archivo=st.file_uploader('Recuperar un respaldo editable (.json)',type=['json'],key=base+'_simple_import')
    payload=None
    if archivo:
        try:
            if archivo.size>500000:raise ValueError('El respaldo es demasiado extenso.')
            payload=json.loads(archivo.getvalue())
            if not isinstance(payload,dict):raise ValueError('El respaldo debe contener un documento o texto pendiente válido.')
            if payload.get('respaldo_anterior'):
                anterior=json.loads(payload['respaldo_anterior'])
                if not isinstance(anterior,dict):raise ValueError('El respaldo anterior no tiene un formato válido.')
                if anterior.get('tipo')=='usaer-texto-pendiente-v2':
                    opcion=st.selectbox('Texto que deseas recuperar',['Texto de esta revisión','Respaldo anterior conservado'],index=0 if payload.get('celdas') else 1,key=base+'_respaldo_origen')
                    if opcion.startswith('Respaldo anterior'):payload=anterior
        except (ValueError,TypeError) as exc:st.warning(str(exc));return
    if payload and st.button('Recuperar este respaldo',key=base+'_simple_restore'):
        try:
            if isinstance(payload.get('documento'),dict) and isinstance(payload.get('filas'),list):
                actor=s.identidad();original=payload['documento']
                if payload.get('cuenta_aporte')!=actor['cuenta'] or payload.get('area_aporte')!=actor['area']:
                    raise PermissionError('Recupera esta aportación con la misma cuenta y área que descargó el respaldo.')
                actual=next((d for d in s.compartidos() if d['id']==original.get('id')),None)
                if not actual:raise PermissionError('No se encontró la hoja compartida dentro de tu escuela asignada.')
                if original['metadatos'].get('aportaciones_equipo',{}).get(actor['area'])!=actual['metadatos'].get('aportaciones_equipo',{}).get(actor['area']):
                    raise RuntimeError('Tu área cambió después de descargar el respaldo. Conserva ambas versiones antes de conciliar; no se reemplazó nada.')
                panel=base+'_colaboracion';prefix=panel+'_'+actual['id']+'_'+actor['area']
                st.session_state.update({prefix+'_doc':actual,prefix+'_filas':payload['filas'],prefix+'_obs':payload.get('observaciones',''),
                                         prefix+'_filas_retiradas':payload.get('filas_retiradas',[]),prefix+'_pending':True,
                                         panel+'_abierto':actual['id'],base+'_submodulo':'equipo'})
                from ui.planeacion_colaboracion import _guardar
                _guardar(prefix);st.rerun();return
            if payload.get('tipo')=='usaer-texto-pendiente-v2':
                from services.planeacion_texto_local import recuperar
                colaborativa=bool(payload.get('colaborativa'))
                actual=next((d for d in (s.compartidos() if colaborativa else s.listar()) if d['id']==payload['documento']),None)
                if not actual:raise PermissionError('Abre el respaldo con la cuenta y escuela del documento original.')
                recuperado=recuperar(actual,payload,colaborativa)
                if colaborativa:
                    actor=s.identidad();panel=base+'_colaboracion';prefix=panel+'_'+actual['id']+'_'+actor['area']
                    filas,obs=recuperado
                    st.session_state.update({prefix+'_doc':actual,prefix+'_filas':filas,prefix+'_obs':obs,prefix+'_pending':True,
                                             panel+'_abierto':actual['id'],base+'_submodulo':'equipo'})
                    from ui.planeacion_colaboracion import _guardar
                    _guardar(prefix)
                else:
                    from services.planeacion_modalidad import modalidad_documento
                    prefix=base+'_'+modalidad_documento(recuperado,s.padron_autorizado())
                    _abrir(base,prefix,recuperado);u._persist(prefix)
                st.rerun();return
            recovered=payload;s.autorizar(recovered,True)
            if recovered['cuenta']!=s.identidad()['cuenta']:raise PermissionError('El respaldo corresponde a otra cuenta.')
            actual=next((d for d in s.listar() if d['id']==recovered['id']),None)
            # Mantener la revisión original: el guardado detectará cambios de
            # otra sesión en lugar de apropiarse de su revisión y sobrescribirla.
            if not actual and not recovered.get('revision'):recovered['revision']=''
            from services.planeacion_modalidad import modalidad_documento
            prefix=base+'_'+modalidad_documento(recovered,s.padron_autorizado())
            _abrir(base,prefix,recovered);u._persist(prefix);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


def _guia_adicional(prefix,doc):
    from ui import planeacion as u
    if doc['metadatos'].get('modalidad_planeacion')!='grupal':
        st.info('Estos complementos corresponden a la planeación grupal.');return
    guia=guia_grupal(doc);enlazada=bool(doc['metadatos'].get('guia_compartida'))
    st.caption('La tabla por alumno ya se edita en Revisar y enviar. Aquí están los complementos del mismo documento, no una nueva guía.')
    if enlazada:st.info('La guía está vinculada: sus aportaciones se editan en Trabajo colaborativo.')
    key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_anexos'
    maestro=st.text_input('Maestro de grupo regular',value=guia['maestro_grupo'],key=key+'_maestro',disabled=enlazada)
    as_rows=guia['as']
    if st.checkbox('Incluir guía AS (Anexo XX): solo aptitudes documentadas',value=bool(as_rows),key=key+'_as'):
        st.caption('Aptitudes y enriquecimiento requieren evidencia, no se asignan automáticamente.')
        defaults=as_rows or [{'Nombre alumno':a['Nombre del alumno'],**{h:'' for h in GUIA_XX[1:]}} for a in doc['datos']['Alumnos']]
        as_rows=st.data_editor(pd.DataFrame(defaults,columns=GUIA_XX),hide_index=True,disabled=True if enlazada else ['Nombre alumno'],key=key+'_xx').fillna('').to_dict('records')
    if st.button('Guardar complementos de la guía',key=key+'_save',disabled=enlazada):
        current=deepcopy(st.session_state[prefix+'_doc'])
        current['metadatos']['guia_grupal_manual']={**current['metadatos'].get('guia_grupal_manual',{}),'maestro_grupo':maestro,'filas':guia_grupal(current)['filas'],'as':as_rows}
        u._open(prefix,current);u._persist(prefix);st.rerun()


def _pendientes(doc):
    from services.planeacion_revision import pendientes
    faltas,items=pendientes(doc)
    return faltas,[i['mensaje'] for i in items]


def _insertar_en_guia_alumno(prefix,indice,campo,texto_nuevo,persist,abrir,reemplazar=False):
    from services.planeacion_formato import editar_guia
    doc=st.session_state[prefix+'_doc'];guia=guia_grupal(doc);base=guia['filas']
    if 0<=indice<len(base):
        actual=str(base[indice].get(campo,'') or '').strip()
        valor_final=texto_nuevo if (reemplazar or not actual) else f'{actual}\n• {texto_nuevo}'
        actualizado=editar_guia(doc,{'edited_rows':{indice:{campo:valor_final}}},base)
        gen=st.session_state.get(prefix+'_generation',0);key=f'{prefix}_{gen}_simple_guia'
        st.session_state[key+'_base']=deepcopy(actualizado['metadatos']['guia_grupal_manual']['filas'])
        abrir(prefix,actualizado);persist(prefix);return True
    return False


def _lienzo_encabezado_oficial(doc):
    formato=doc['formato'];modalidad_doc=doc['metadatos'].get('modalidad_planeacion','grupal')
    if modalidad_doc=='grupal':anexo_txt='ANEXO XIX. GUÍA DE PLANEACIÓN GRUPAL'
    elif formato=='XXI':anexo_txt='ANEXO XXI. PLAN DE INTERVENCIÓN'
    elif formato=='XXV':anexo_txt='ANEXO XXV. PLANEACIÓN DEL ÁREA DE TRABAJO SOCIAL'
    else:anexo_txt='ANEXO XXIII. PLANEACIÓN DEL SERVICIO DE APOYO DE EDUCACIÓN ESPECIAL'
    datos=doc['datos'];escuela=datos.get('Escuela regular','');cct=datos.get('CCT','31FUA0024E')
    curso=datos.get('Curso escolar','');esp=datos.get('Nombre del especialista','');func=datos.get('Función','')
    from utils.escolar import grado_canonico
    grados_grupos=', '.join(f"{grado_canonico(a.get('Grado',''))} {a.get('Grupo','')}".strip() for a in datos.get('Alumnos',[])) or datos.get('Periodo','')
    maestro_g=(doc['metadatos'].get('guia_grupal_manual',{}).get('maestro_grupo','')) or datos.get('Maestro de grupo','')
    st.markdown(f'''
    <div class="usaer-canvas-card">
        <div class="usaer-official-header">
            <div class="usaer-sub-badge">GOBIERNO DEL ESTADO DE YUCATÁN · SECRETARÍA DE EDUCACIÓN</div>
            <div class="usaer-sub-badge">DIRECCIÓN DE EDUCACIÓN ESPECIAL · ZONA ESCOLAR 001</div>
            <div class="usaer-main-title">USAER 02-E · SISTEMA INTEGRADO DE PLANEACIÓN</div>
            <div class="usaer-annex-badge">{anexo_txt}</div>
        </div>
        <table class="usaer-meta-table">
            <tr>
                <td class="usaer-meta-label">Escuela regular:</td>
                <td><strong>{escuela}</strong></td>
                <td class="usaer-meta-label">C.C.T.:</td>
                <td>{cct}</td>
            </tr>
            <tr>
                <td class="usaer-meta-label">Curso escolar:</td>
                <td>{curso}</td>
                <td class="usaer-meta-label">Grado y Grupo:</td>
                <td>{grados_grupos}</td>
            </tr>
            <tr>
                <td class="usaer-meta-label">Docente de grupo:</td>
                <td>{maestro_g or '<em>Por especificar</em>'}</td>
                <td class="usaer-meta-label">Especialista USAER:</td>
                <td>{esp} ({func})</td>
            </tr>
        </table>
    </div>
    ''', unsafe_allow_html=True)


def _asistente_inteligente_alumno(prefix,doc,actor,u):
    from services.curriculo import CAMPOS, catalogo
    alumnos=doc['datos']['Alumnos']
    if not alumnos:return
    st.markdown('''
    <div style="background: linear-gradient(135deg, #F0FDFA 0%, #FFFFFF 100%); border: 1.5px solid #0D9488; border-radius: 10px; padding: 0.85rem 1.1rem; margin-bottom: 1rem;">
        <span style="background-color: #0D9488; color: white; font-size: 0.75rem; font-weight: 700; padding: 0.2rem 0.55rem; border-radius: 4px; text-transform: uppercase;">
            ⚡ Asistente Inteligente · Conectividad del Alumno en 1 Clic
        </span>
        <div style="font-size: 0.85rem; color: #475569; margin-top: 0.35rem;">
            Selecciona a un alumno para transferir antecedentes del expediente, insertar referentes oficiales (PDA) o aplicar secuencias didácticas directamente en su fila de la guía.
        </div>
    </div>
    ''', unsafe_allow_html=True)
    al_idx=st.selectbox('🎯 Alumno activo para enriquecer con conectividad',range(len(alumnos)),format_func=lambda i:f"{alumnos[i]['Nombre del alumno']} ({grado_canonico(alumnos[i].get('Grado',''))} {alumnos[i].get('Grupo','')}) · {alumnos[i].get('Condición','')}",key=prefix+'_asistente_alumno_idx')
    al_sel=alumnos[al_idx];al_id=str(al_sel['ID_Alumno']);al_nombre=al_sel['Nombre del alumno']
    area_docente=actor['area'];col_destino=area_docente if area_docente in GUIA_XIX else 'Aprendizaje'
    tabs=st.tabs(['📁 Antecedentes del expediente','🎯 Referentes NEM / PDA','✨ Secuencia en 3 momentos','🧠 Especialidad / Apoyos'])
    with tabs[0]:
        fuentes=doc['metadatos'].get('fuentes',[])
        fuentes_alumno=[f for f in fuentes if str(f.get('id_alumno',''))==al_id or al_nombre.lower() in str(f.get('texto','')).lower()]
        fuentes_mostrar=fuentes_alumno if fuentes_alumno else fuentes[:5]
        if fuentes_mostrar:
            st.caption(f'Antecedentes disponibles para {al_nombre}. Pulsa en insertar para transferir a su fila ({col_destino}):')
            for i,f in enumerate(fuentes_mostrar):
                with st.container(border=True):
                    st.markdown(f"**{f.get('referencia',f.get('tipo','Registro'))}** · *{f.get('fecha','')}*")
                    txt_prev=f.get('texto','')
                    st.write(txt_prev[:250]+('…' if len(txt_prev)>250 else ''))
                    if st.button(f'➕ Transferir a la fila de {al_nombre.split()[0]}',key=f'{prefix}_asist_fuente_{al_idx}_{i}'):
                        _insertar_en_guia_alumno(prefix,al_idx,col_destino,f"[{f.get('tipo','Expediente')}] {txt_prev[:200]}",u._persist,u._open)
                        st.success(f'¡Transferido a la columna {col_destino} de {al_nombre}!');st.rerun()
        else:st.info(f'No hay antecedentes específicos registrados para {al_nombre}.')
    with tabs[1]:
        st.caption(f'Selecciona el campo formativo y el PDA para contextualizar los objetivos de {al_nombre}:')
        c_col1,c_col2=st.columns([1,2])
        with c_col1:
            campo_sel=st.selectbox('Campo formativo curricular (NEM)',list(CAMPOS.keys()),key=f'{prefix}_asist_campo_{al_idx}')
        with c_col2:
            grado_al=None
            try:
                import re
                m=re.search(r'([1-6])',str(al_sel.get('Grado','')))
                if m:grado_al=int(m.group(1))
            except Exception:grado_al=None
            cat_data=catalogo().get('registros',[])
            regs_cat=[r for r in cat_data if r.get('campo')==campo_sel and (grado_al is None or r.get('grado')==grado_al)]
            if not regs_cat:regs_cat=[r for r in cat_data if r.get('campo')==campo_sel][:15]
            pda_sel=st.selectbox('Contenido y PDA oficial',range(len(regs_cat)),format_func=lambda i:f"{regs_cat[i]['grado']}° · {regs_cat[i]['contenido'][:50]}... -> {regs_cat[i]['pda'][:60]}...",key=f'{prefix}_asist_pda_{al_idx}') if regs_cat else None
        if pda_sel is not None and regs_cat:
            reg=regs_cat[pda_sel]
            st.markdown(f"**Contenido:** {reg['contenido']}\n\n**PDA ({reg['grado']}°):** {reg['pda']}")
            if st.button(f'➕ Insertar PDA en columna Aprendizaje de {al_nombre.split()[0]}',key=f'{prefix}_asist_ins_pda_{al_idx}'):
                texto_pda=f"PDA ({campo_sel} · {reg['grado']}°): {reg['pda']}"
                _insertar_en_guia_alumno(prefix,al_idx,'Aprendizaje',texto_pda,u._persist,u._open)
                st.success(f'¡PDA vinculado a la fila de {al_nombre}!');st.rerun()
    with tabs[2]:
        st.caption(f'Estructura de educación especial en 3 momentos (tangible, guiado y observable) para {al_nombre}:')
        cond=al_sel.get('Condición','Sin condición específica')
        sec_propuesta=f'1. Inicio tangible: Actividad manipulable de activación y encuadre visual adaptada a {cond}.\n2. Desarrollo guiado: Ejercitación con andamiaje paso a paso, material concreto y modelado.\n3. Cierre observable: Demostración práctica del logro y autoevaluación formativa con apoyo pictográfico.'
        st.text_area('Propuesta pedagógica estructurada',value=sec_propuesta,height=110,key=f'{prefix}_asist_sec_txt_{al_idx}')
        if st.button(f'➕ Aplicar secuencia a columna {col_destino} de {al_nombre.split()[0]}',key=f'{prefix}_asist_ins_sec_{al_idx}'):
            _insertar_en_guia_alumno(prefix,al_idx,col_destino,sec_propuesta,u._persist,u._open)
            st.success(f'¡Secuencia integrada a la fila de {al_nombre}!');st.rerun()
    with tabs[3]:
        st.caption('Aportes y estrategias según la función o especialidad:')
        esp_cols=st.columns(2)
        with esp_cols[0]:
            st.markdown('**Estrategia socioemocional / conductual:**')
            psic_opts=['Estructuración visual de rutinas y normas claras de convivencia','Economía de fichas y reforzamiento positivo contingente','Pausas activas y técnicas de respiración para autorregulación','Canalización socioemocional y diálogo asertivo ante frustración']
            psic_sel=st.selectbox('Estrategia de conducta',psic_opts,key=f'{prefix}_asist_esp_psic_{al_idx}')
            if st.button(f'➕ Insertar en Psicología de {al_nombre.split()[0]}',key=f'{prefix}_asist_btn_psic_{al_idx}'):
                _insertar_en_guia_alumno(prefix,al_idx,'Psicología',psic_sel,u._persist,u._open)
                st.success('¡Estrategia agregada a Psicología!');st.rerun()
        with esp_cols[1]:
            st.markdown('**Comunicación / Trabajo Social:**')
            com_opts=['Tablero de comunicación aumentativa con pictogramas (SAAC)','Modelado fonoarticulatorio y pausas en turnos conversacionales','Compromiso de corresponsabilidad y seguimiento en el hogar','Visita domiciliaria de verificación de contexto sociofamiliar']
            com_sel=st.selectbox('Estrategia de apoyo',com_opts,key=f'{prefix}_asist_esp_com_{al_idx}')
            destino_esp='Trabajo Social' if ('hogar' in com_sel or 'domiciliaria' in com_sel) else 'Comunicación'
            if st.button(f'➕ Insertar en {destino_esp} de {al_nombre.split()[0]}',key=f'{prefix}_asist_btn_com_{al_idx}'):
                _insertar_en_guia_alumno(prefix,al_idx,destino_esp,com_sel,u._persist,u._open)
                st.success(f'¡Estrategia agregada a {destino_esp}!');st.rerun()


def _editor(prefix,actor,paso):
    from ui import planeacion as u
    from ui.planeacion_formato import _tabla,_guia,_guia_texto
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    if doc['metadatos'].get('version_contexto')!=s.VERSION_CONTEXTO:
        u._open(prefix,s.preparar_contexto(doc));st.session_state[prefix+'_pending']=True;doc=st.session_state[prefix+'_doc']
    st.subheader(FORMATOS[doc['formato']]['titulo'])
    st.write(doc['datos']['Escuela regular']+' · '+doc['datos'].get('CCT',''))
    st.caption(', '.join(a['Nombre del alumno'] for a in doc['datos']['Alumnos'])+' · '+doc['datos']['Periodo'])
    u._autosave(prefix)
    if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
    from ui.planeacion_edicion import panel as opciones_edicion
    opciones_edicion(prefix)
    if paso==PASOS[1]:
        st.subheader(PASOS[1]);st.caption('El expediente alimenta el borrador. La IA propone; tú decides y puedes editar todo.')
        from ui.planeacion_respaldo import acceso
        acceso(prefix, raiz(prefix), PASOS[2])
        from ui.planeacion_local import panel as actividades_locales
        actividades_locales(prefix)
        fuentes=doc['metadatos'].get('fuentes',[])
        with st.expander('📋 1. Antecedentes automáticos (Anexos III, IV, V y visitas)', expanded=True):
            st.caption('Revisa lo ya documentado por el equipo. Si un antecedente te sirve, pulsa "+ Usar en borrador" para transferirlo sin copiar y pegar.')
            if doc['metadatos'].get('fuentes_pendientes'):st.warning('Parte del expediente aún no pudo leerse. Comprueba las fuentes antes de solicitar propuestas.')
            if fuentes:
                for i, fuente in enumerate(fuentes):
                    with st.container(border=True):
                        c_txt,c_btn=st.columns([3.5,1.5])
                        with c_txt:
                            st.markdown(f"**{fuente.get('referencia',fuente.get('tipo','Registro'))}** · *{fuente.get('fecha','')}*")
                            st.write(fuente.get('texto',''))
                        with c_btn:
                            if st.button('➕ Usar en borrador', key=f'{prefix}_step2_usar_{i}'):
                                try:
                                    from services.planeacion_formato import usar_evidencia
                                    actualizado=usar_evidencia(st.session_state[prefix+'_doc'],fuente)
                                    u._open(prefix,actualizado);u._persist(prefix);st.success('¡Agregado a tu borrador!');st.rerun()
                                except Exception as exc:st.info(str(exc))
            else:
                st.info('No hay antecedentes previos registrados en el expediente para este alumno o grupo.')
            if st.button('🔄 Actualizar antecedentes del expediente', key=prefix+'_step2_refresh_fuentes'):
                try:s.refrescar_evidencias();u._open(prefix,s.preparar_contexto(doc));u._persist(prefix);st.rerun()
                except Exception:st.warning('No se confirmó la actualización. Tu edición se conserva.')
        with st.expander('📚 2. Referentes oficiales y PDA (Plan y Programas)', expanded=actor['area']=='Aprendizaje'):
            st.caption('Selecciona uno o varios campos formativos y busca sus PDA. Complementan la función de tu área; no sustituyen su formato ni sus acuerdos.')
            if st.toggle('Buscar y adaptar referentes curriculares (PDA)', key=prefix+'_toggle_curriculo'):
                u._curriculo(prefix,doc)
        if actor['area']=='Psicología':
            with st.expander('🧠 2. Competencias socioemocionales y conducta (Manual SEGEY · Zona 001)', expanded=True):
                st.caption('Enfoca tu intervención en las 5 competencias formativas y estrategias conductuales de la Tabla 8 del Manual.')
                cols_psic = st.columns(2)
                with cols_psic[0]:
                    st.markdown('**Competencias formativas prioritarias:**')
                    c_sel = st.multiselect('Competencias a favorecer', [
                        'Autoconciencia (identificación de emociones y autoconcepto)',
                        'Autorregulación (tolerancia a frustración y manejo de impulsos)',
                        'Conciencia social (empatía y normas de convivencia)',
                        'Relaciones interpersonales (escucha activa y trabajo en equipo)',
                        'Toma de decisiones responsables (solución pacífica de conflictos)'
                    ], key=prefix+'_psic_comp')
                with cols_psic[1]:
                    st.markdown('**Estrategias conductuales sugeridas (Tabla 8):**')
                    e_sel = st.multiselect('Estrategias de aula', [
                        'Economía de fichas / reforzamiento positivo',
                        'Semáforo de control del tiempo de trabajo',
                        'Pausas activas y espacios breves de esparcimiento',
                        'Estructuración visual de rutinas y normas en aula',
                        'Técnicas de relajación y respiración'
                    ], key=prefix+'_psic_est')
                if (c_sel or e_sel) and st.button('➕ Aplicar al enfoque de mi planeación', key=prefix+'_psic_aplicar'):
                    texto_adic = []
                    if c_sel: texto_adic.append('Competencias socioemocionales prioritarias:\n• ' + '\n• '.join(c_sel))
                    if e_sel: texto_adic.append('Estrategias conductuales:\n• ' + '\n• '.join(e_sel))
                    previo = doc['metadatos'].get('necesidades_confirmadas', '')
                    doc['metadatos']['necesidades_confirmadas'] = (previo + '\n\n' + '\n\n'.join(texto_adic)).strip()
                    u._open(prefix, doc); u._persist(prefix); st.success('¡Enfoque socioemocional integrado!'); st.rerun()
        elif actor['area']=='Comunicación':
            with st.expander('🗣️ 2. Canal comunicativo y participación (Manual SEGEY p. 13-14, 23)', expanded=True):
                st.caption('Prioriza canales de comunicación y estrategias para el aula regular según las características del alumno.')
                cols_com = st.columns(2)
                with cols_com[0]:
                    st.markdown('**Canal comunicativo prioritario:**')
                    canal_sel = st.selectbox('Canal comunicativo principal', [
                        'Selecciona un canal...',
                        'Lenguaje oral (estimulación fonoarticulatoria y morfosintaxis)',
                        'Lengua de Señas Mexicana (LSM) / Enfoque bilingüe-bicultural',
                        'SAAC (Sistemas Aumentativos y Alternativos / Tableros con pictogramas)',
                        'Lectoescritura funcional y adaptada',
                        'Comunicación pre-simbólica / Claves visuales y gestuales'
                    ], key=prefix+'_com_canal')
                with cols_com[1]:
                    st.markdown('**Contextos y estrategias prioritarias:**')
                    ambito_sel = st.multiselect('Contextos y estrategias', [
                        'Aula de apoyo: estimulación fonoarticulatoria y desarrollo de habla',
                        'Aula regular: modelado y pausas comunicativas con pares',
                        'Familia: fomento de situaciones de elección y diálogo en casa',
                        'Uso de apoyos visuales y material concreto en clase'
                    ], key=prefix+'_com_ambito')
                if canal_sel != 'Selecciona un canal...' and st.button('➕ Aplicar al enfoque de mi planeación', key=prefix+'_com_aplicar'):
                    texto_com = [f'Canal comunicativo: {canal_sel}']
                    if ambito_sel: texto_com.append('Estrategias en contextos:\n• ' + '\n• '.join(ambito_sel))
                    previo = doc['metadatos'].get('necesidades_confirmadas', '')
                    doc['metadatos']['necesidades_confirmadas'] = (previo + '\n\n' + '\n\n'.join(texto_com)).strip()
                    u._open(prefix, doc); u._persist(prefix); st.success('¡Enfoque de comunicación integrado!'); st.rerun()
        elif actor['area']=='Trabajo Social':
            with st.expander('🤝 2. Barreras de contexto y corresponsabilidad (Manual SEGEY Formato XXV)', expanded=True):
                from ui.planeacion_social import panel as panel_social
                panel_social(prefix,u._persist,u._open)
        with st.expander('✨ 3. Propuesta pedagógica con IA', expanded=True):
            if doc['formato']=='XXI':
                st.caption('Las NEE y BAP se precargan únicamente de una conclusión vigente de EPP. No se validan automáticamente.')
                u._text(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
                key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_iepp'
                st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(doc['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=u._field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
                u._ai(prefix,doc)
            else:
                from ui.planeacion_generacion import panel_generacion
                panel_generacion(prefix,u._persist,u._open,compact=True)
        with st.expander('Añadir una necesidad documentada si hace falta evidencia'):
            u._text(prefix,'metadatos','necesidades_confirmadas','Necesidades y apoyos documentados (incluye la referencia de origen)')
        st.markdown('---')
        if st.button('Continuar a mi formato para revisar y entregar ➡️', type='primary', key=prefix+'_ir_paso3', use_container_width=True):
            st.session_state[raiz(prefix)+'_paso']=PASOS[2];st.rerun()
    else:
        st.subheader(PASOS[2]);st.caption('Edita directamente en tu formato. Los resultados finales se registran después de trabajar con el alumno.')
        from ui.planeacion_respaldo import informacion
        informacion(prefix, raiz(prefix), PASOS[1])
        _lienzo_encabezado_oficial(doc)
        with st.expander('Datos generales del formato'):
            st.write(doc['datos'])
            if not doc['datos'].get('CCT'):u._text(prefix,'datos','CCT','CCT no registrado: verifica y completa')
            if doc['formato']=='XXI':
                for campo in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):u._text(prefix,'datos',campo)
        if doc['metadatos'].get('modalidad_planeacion')=='grupal':
            _asistente_inteligente_alumno(prefix,doc,actor,u)
            st.markdown('#### Actividades por alumno y área · Anexo XIX')
            guia=guia_grupal(doc);enlazada=doc['metadatos'].get('guia_compartida')
            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_guia';bk=key+'_base'
            if bk not in st.session_state:st.session_state[bk]=deepcopy(guia['filas'])
            base=st.session_state[bk]
            st.data_editor(pd.DataFrame(base,columns=['ID_Alumno',*GUIA_XIX]).drop(columns='ID_Alumno'),hide_index=True,disabled=True if enlazada else ['Nombre alumno','Discapacidad o condición'],key=key,on_change=_guia,args=(prefix,key,base,u._persist))
            if enlazada:st.caption('Edita las aportaciones en Trabajo colaborativo y actualiza las conexiones.')
            else:
                with st.expander('Editar texto completo por alumno'):
                    for i,row in enumerate(guia_grupal(st.session_state[prefix+'_doc'])['filas']):
                        st.markdown('##### '+row['Nombre alumno'])
                        for campo in GUIA_XIX[2:]:
                            key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_guia_{i}_{campo}'
                            st.text_area(campo,value=str(row.get(campo,'') or ''),key=key,on_change=_guia_texto,args=(prefix,key,i,campo,u._persist,u._open))
            with st.expander('🌟 Anexo XX: Guía de Planeación Grupal para Alumnos con Aptitudes Sobresalientes (AS)', expanded=bool(guia.get('as'))):
                st.caption('Manual SEGEY Anexo XX: Registra las aptitudes sobresalientes (I, C, SA, PM, A), enriquecimiento (E, A, EC) y metodología diversificada.')
                as_activado = st.checkbox('Activar Anexo XX para este grupo', value=bool(guia.get('as')), key=f'{prefix}_as_anexo_check')
                if as_activado:
                    as_base = guia.get('as') or [{'Nombre alumno': a['Nombre del alumno'], **{h: '' for h in GUIA_XX[1:]}} for a in doc['datos']['Alumnos']]
                    key_as = f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_simple_xx'
                    as_editado = st.data_editor(pd.DataFrame(as_base, columns=GUIA_XX), hide_index=True, disabled=True if enlazada else ['Nombre alumno'], key=key_as).fillna('').to_dict('records')
                    if st.button('Guardar datos de Anexo XX (AS)', key=f'{prefix}_as_save_btn', disabled=enlazada):
                        current = deepcopy(st.session_state[prefix+'_doc'])
                        current['metadatos']['guia_grupal_manual'] = {**current['metadatos'].get('guia_grupal_manual', {}), 'as': as_editado}
                        u._open(prefix, current); u._persist(prefix); st.success('¡Anexo XX guardado correctamente!'); st.rerun()
        for tabla in FORMATOS[doc['formato']]['tablas']:
            if tabla=='evaluacion_final':
                with st.expander('Resultados al finalizar'):_tabla(prefix,tabla,u._persist,u._open)
            else:_tabla(prefix,tabla,u._persist,u._open)
        for campo in doc['textos']:u._text(prefix,'textos',campo)
    actual=st.session_state[prefix+'_doc'];faltas,avisos=_pendientes(actual)
    with st.expander('Antes de enviar · '+str(len(avisos))+' aspectos por completar'):
        from ui.planeacion_revision import panel as revisar
        revisar(prefix)
    # Solo la clase pública st-key del contenedor propio; no depende del DOM de
    # botones ni columnas internas. La barra acompaña el desplazamiento.
    st.html('<style>.st-key-'+prefix+'_acciones {position:sticky;bottom:0;z-index:99;background:rgba(255,255,255,0.96);backdrop-filter:blur(12px);-webkit-backdrop-filter:blur(12px);padding:0.85rem 1.2rem;border-top:2.5px solid #0D9488;box-shadow:0 -8px 25px rgba(15,45,89,0.12);border-radius:16px 16px 0 0;} @media(max-width:640px){.st-key-'+prefix+'_acciones{padding:0.5rem;}}</style>')
    with st.container(horizontal=True,vertical_alignment='center',key=prefix+'_acciones'):
        if st.button('Guardar borrador',key=prefix+'_simple_save'):u._persist(prefix);st.rerun()
        if st.button('Ver PDF',key=prefix+'_simple_pdf'):
            st.session_state[prefix+'_mostrar_pdf']=True;st.rerun()
        if st.button('Enviar a Dirección',key=prefix+'_simple_send',disabled=bool(faltas)):u._persist(prefix,'ENVIADO');st.rerun()
        st.download_button('Descargar respaldo editable',json.dumps(actual,ensure_ascii=False,indent=2),file_name='planeacion-'+actual['id']+'.json',mime='application/json',key=prefix+'_bar_backup')
    if st.session_state.get(prefix+'_mostrar_pdf'):
        if st.button('Volver a editar',key=prefix+'_simple_hidepdf'):
            st.session_state[prefix+'_mostrar_pdf']=False;st.rerun()
        try:
            pdf=u._pdf_sesion(prefix,actual);u._preview(prefix+'_simple_preview',pdf)
            st.download_button('Descargar PDF',pdf,file_name='planeacion-'+actual['id']+'.pdf',mime='application/pdf',key=prefix+'_simple_download')
        except Exception:st.warning('No se pudo preparar el PDF. Tu borrador se conserva.')
    if st.toggle('Más herramientas',key=prefix+'_mas_herramientas'):_herramientas(prefix,actor)


def pagina():
    from ui import planeacion as u
    _inyectar_estilos_planeacion()
    actor=s.identidad();base=u._prefix()
    from ui.planeacion_pendientes import panel as envios_pendientes
    envios_pendientes(base)
    st.title('Mi planeación · '+actor['area'])
    st.caption('Elige alumnos, prepara tu propuesta y revisa el formato. Captura una vez; reutiliza lo que el equipo ya conoce.')
    labels=['Mi planeación','Trabajo colaborativo']+(['Revisión directiva'] if actor['director'] else [])
    tabs=st.tabs(labels)
    with tabs[0]:
        activo=st.session_state.get(base+'_activa')
        if not activo:
            # Compatibilidad con borradores abiertos antes de activar esta vista.
            prefixes=[p for p in (base+'_individual',base+'_grupal') if p+'_doc' in st.session_state]
            activo=next((p for p in prefixes if st.session_state.get(p+'_pending')),next(iter(prefixes),None))
            if activo:st.session_state[base+'_activa']=activo
        for p in (base+'_individual',base+'_grupal'):
            if p!=activo and st.session_state.get(p+'_pending') and p+'_doc' in st.session_state:
                st.warning('Hay otra edición pendiente de '+p.rsplit('_',1)[-1]+'. Se conserva sin reemplazarla.')
                st.download_button('Respaldar otra edición pendiente',json.dumps(st.session_state[p+'_doc'],ensure_ascii=False),file_name='planeacion-pendiente.json',key=p+'_simple_otro_respaldo')
                if st.button('Guardar otra edición pendiente',key=p+'_simple_otro_guardar'):u._persist(p);st.rerun()
        if activo and activo+'_doc' in st.session_state:
            if base+'_paso_pendiente' in st.session_state:
                st.session_state[base+'_paso']=st.session_state.pop(base+'_paso_pendiente')
            paso=st.segmented_control('Mi recorrido',PASOS,default=PASOS[1],key=base+'_paso') or PASOS[1]
            if paso==PASOS[0]:
                u._autosave(activo);_entrada(base,actor)
            else:_editor(activo,actor,paso)
        else:_entrada(base,actor)
    with tabs[1]:
        from ui.planeacion_colaboracion import panel
        panel(base+'_colaboracion')
    if actor['director']:
        with tabs[2]:u.direccion_panel()
