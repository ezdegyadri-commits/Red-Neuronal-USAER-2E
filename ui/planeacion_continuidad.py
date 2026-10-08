"""Conexiones, integración revisable y seguimiento dentro del editor existente."""
from datetime import date,datetime
from zoneinfo import ZoneInfo
import pandas as pd
import streamlit as st
from services import planeacion as s
from services import planeacion_continuidad as c
from services.planeacion_colaboracion import integrar


def _borrador(prefix,key,campo,persist):
    doc=st.session_state[prefix+'_doc']
    valor=st.session_state[key]
    if hasattr(valor,'isoformat'):valor=valor.isoformat()
    doc['metadatos'].setdefault('seguimiento_en_curso',{})[campo]=valor
    persist(prefix,automatic=True)


def panel(prefix,abrir,persist):
    doc=st.session_state[prefix+'_doc']
    with st.expander('Conexiones y seguimiento · del expediente a la planeación'):
        st.caption('EPP → Plan de Intervención → trimestral → resultados observados. Las conexiones no aprueban documentos ni sustituyen acuerdos del equipo.')
        links=doc['metadatos'].get('vinculos_documentales',[])
        nombres={a['ID_Alumno']:a['Nombre del alumno'] for a in doc['datos']['Alumnos']}
        if links:st.dataframe(pd.DataFrame([{**v,'alumno':nombres.get(v['alumno'],'')} for v in links]),hide_index=True)
        else:st.caption('Aún no hay un documento de origen vigente vinculado. Puedes preparar el borrador sin inventar una EPP o un PI.')
        for aviso in doc['metadatos'].get('avisos_continuidad',[]):st.warning(aviso)
        if doc['metadatos'].get('resumen_anterior_para_revisar'):
            with st.expander('Resumen anterior conservado para comparar'):
                st.caption('Cambió el expediente: el resumen actual usa la lectura nueva. Tu redacción anterior se conserva aquí para conciliarla, no se envía automáticamente a la IA.')
                st.write(doc['metadatos']['resumen_anterior_para_revisar'])
        if st.button('Actualizar conexiones del expediente',key=prefix+'_conexiones'):
            try:
                s.refrescar();actual=s.preparar_contexto(doc);abrir(prefix,actual);persist(prefix);st.rerun()
            except Exception:st.warning('No se pudieron confirmar las conexiones. Tu redacción se conserva.')
        if doc['formato']=='XXI' and st.button('Precargar NEE y BAP desde la EPP revisada',key=prefix+'_precargar_epp'):
            try:abrir(prefix,c.trasladar_epp(doc));persist(prefix);st.rerun()
            except (ValueError,PermissionError) as exc:st.warning(str(exc))
        aportes=doc['metadatos'].get('aportaciones_equipo',{})
        for aviso in doc['metadatos'].get('avisos_integracion',[]):st.warning(aviso)
        if aportes:
            for area,aporte in aportes.items():st.caption(area+' · '+aporte['autor']+' · '+('integrada' if doc['metadatos'].get('aportaciones_integradas',{}).get(area)==aporte['revision'] else 'pendiente de integrar'))
            if st.button('Integrar aportaciones al borrador para revisar',key=prefix+'_integrar'):
                abrir(prefix,integrar(doc));persist(prefix);st.rerun()
                # Integrar no equivale a validar ni firmar.
        st.markdown('##### Registrar resultados y decidir el siguiente paso')
        st.caption('Revisión semestral para PI; trimestral para planeaciones. Usa resultados observados, no actividades previstas. El registro alimentará futuras planeaciones.')
        registros=doc['metadatos'].get('seguimiento_formativo',[])
        for r in registros:
            st.write(r['fecha']+' · '+r['decision']);st.write(r['hallazgos'])
        gen=st.session_state.get(prefix+'_generation',0);base=f'{prefix}_{gen}_seguimiento'
        borrador=doc['metadatos'].get('seguimiento_en_curso',{})
        fecha=st.date_input('Fecha del seguimiento',value=date.fromisoformat(borrador.get('fecha',datetime.now(ZoneInfo('America/Mexico_City')).date().isoformat())),key=base+'_fecha',on_change=_borrador,args=(prefix,base+'_fecha','fecha',persist))
        hallazgos=st.text_area('Qué se observó y qué apoyo funcionó',value=borrador.get('hallazgos',''),max_chars=6000,key=base+'_texto',on_change=_borrador,args=(prefix,base+'_texto','hallazgos',persist))
        decisiones=['Continuar','Ajustar','Retirar apoyo','Ampliar reto']
        decision=st.selectbox('Decisión educativa',decisiones,index=decisiones.index(borrador.get('decision','Continuar')),key=base+'_decision',on_change=_borrador,args=(prefix,base+'_decision','decision',persist))
        fuentes=doc['metadatos'].get('fuentes',[]);opciones={f['referencia']:f for f in fuentes if f.get('vinculo_verificado') and f.get('tipo') not in ('PLAN','MATERIAL')}
        refs=st.multiselect('Evidencias que sustentan el seguimiento',list(opciones),default=[r for r in borrador.get('referencias',[]) if r in opciones],format_func=lambda i:i+' · '+opciones[i].get('tipo','')+' · '+opciones[i].get('fecha',''),key=base+'_refs',on_change=_borrador,args=(prefix,base+'_refs','referencias',persist))
        if st.button('Guardar seguimiento formativo',key=base+'_save',disabled=not hallazgos.strip() or not refs):
            try:abrir(prefix,c.seguimiento(doc,fecha.isoformat(),hallazgos,decision,refs));persist(prefix);st.rerun()
            except (ValueError,PermissionError) as exc:st.warning(str(exc))
