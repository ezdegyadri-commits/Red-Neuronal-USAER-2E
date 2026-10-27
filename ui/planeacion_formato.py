"""Vista del formato familiar, sin otra persistencia ni otro expediente."""
from copy import deepcopy
import json
import pandas as pd
import streamlit as st
from services import planeacion as s,planeacion_formato as f
from services.planeacion_modelo import FORMATOS
from services.planeacion_modalidad import guia_grupal,GUIA_XIX
from services.curriculo import contexto_ia
def generar_pdf(doc):
    try:
        from documents.planeacion import generar_pdf as _gp
        return _gp(doc)
    except ModuleNotFoundError:
        return b"%PDF-1.4 (reportlab no disponible)"


def _celda(prefix,key,tabla,indice,campo,persist):
    st.session_state[prefix+'_doc']=f.editar_celda(st.session_state[prefix+'_doc'],tabla,indice,campo,st.session_state[key])
    st.session_state.pop(prefix+'_pdf',None);persist(prefix,automatic=True)

def _guia(prefix,key,base,persist):
    st.session_state[prefix+'_doc']=f.editar_guia(st.session_state[prefix+'_doc'],st.session_state[key],base)
    st.session_state.pop(prefix+'_pdf',None);persist(prefix,automatic=True)

def _guia_texto(prefix,key,indice,campo,persist,abrir):
    doc=st.session_state[prefix+'_doc'];base=guia_grupal(doc)['filas']
    actualizado=f.editar_guia(doc,{'edited_rows':{indice:{campo:st.session_state[key]}}},base)
    # Cambiar generación también actualiza la matriz, sin conservar un baseline obsoleto.
    abrir(prefix,actualizado);persist(prefix)

def _tabla(prefix,tabla,persist,abrir):
    doc=st.session_state[prefix+'_doc'];headers=FORMATOS[doc['formato']]['tablas'][tabla]
    st.markdown('#### '+f.TITULOS[tabla]);gen=st.session_state.get(prefix+'_generation',0)
    for i,row in enumerate(doc['tablas'][tabla]):
        if row.get('_sesion_equipo'):
            st.caption('Actividad vinculada a una sesión: '+str(row.get('Temporalidad',row.get('Fecha',''))))
            st.write(row.get('Actividades',''));continue
        with st.container(border=True):
            st.caption('Fila '+str(i+1));columnas=st.columns(min(3,len(headers)))
            for j,campo in enumerate(headers):
                key=f'{prefix}_{gen}_formato_{tabla}_{i}_{campo}'
                ayuda = None
                if campo in ('Descriptor de logro', 'Descriptor de Logro'):
                    ayuda = 'Manual SEGEY: Sujeto + verbo en presente + complemento observable (Ej: El alumno lee hasta 100 palabras con el Método Troncoso)'
                elif campo in ('Necesidades educativas específicas', 'NEE'):
                    ayuda = 'Manual SEGEY: Verbo + qué (Ej: Necesita fortalecer la atención sostenida)'
                elif campo in ('Barreras para el Aprendizaje y la Participación', 'BAP'):
                    ayuda = 'Manual SEGEY: Enunciadas sobre las barreras del entorno/contexto, no etiquetas del alumno'
                elif campo == 'Temporalidad':
                    ayuda = 'Ej: Primera semana de noviembre / Sesión semanal de 45 min / Quincenal'
                elif campo == 'Recursos':
                    ayuda = 'Ej: Material concreto, pictogramas, regletas, libros sensoriales, libretas'

                with columnas[j%len(columnas)]:
                    st.text_area(campo,value=str(row.get(campo,'') or ''),height=130,key=key,help=ayuda,on_change=_celda,args=(prefix,key,tabla,i,campo,persist))
                    if campo in ('Necesidades educativas específicas', 'NEE') and doc.get('metadatos',{}).get('modalidad_planeacion')!='individual':
                        from services.planeacion_nee import catalogo_nee_validadas
                        target_alumno = None
                        if row.get('_alumnos_apartados') and isinstance(row['_alumnos_apartados'], list):
                            target_alumno = row['_alumnos_apartados'][0]
                        elif doc.get('datos', {}).get('Alumnos'):
                            target_alumno = doc['datos']['Alumnos'][0]

                        catalogo = catalogo_nee_validadas(doc, alumno_id=target_alumno)
                        opciones_nee = [c['texto'] for c in catalogo]
                        curr_nee = str(row.get(campo, '') or '').strip()

                        if opciones_nee:
                            n_idx = opciones_nee.index(curr_nee) + 1 if curr_nee in opciones_nee else 0
                            n_sel = st.selectbox(
                                '📋 NEE validada de EPP',
                                ['(Escribir libre / mantener actual)'] + opciones_nee,
                                index=n_idx,
                                key=f'{key}_nee_sel',
                                help='Selecciona una NEE validada en la EPP para incorporarla a este aprendizaje sin recapturar.'
                            )
                            append_mode = False
                            if len(opciones_nee) > 1 and curr_nee:
                                append_mode = st.checkbox('➕ Añadir a texto actual (sin reemplazar)', key=f'{key}_nee_append', value=False)
                            if n_sel != '(Escribir libre / mantener actual)':
                                nuevo_valor = f"{curr_nee}\n{n_sel}".strip() if (append_mode and curr_nee and n_sel not in curr_nee) else n_sel
                                if nuevo_valor != curr_nee:
                                    st.session_state[prefix+'_doc'] = f.editar_celda(st.session_state[prefix+'_doc'], tabla, i, campo, nuevo_valor)
                                    st.session_state.pop(prefix+'_pdf', None)
                                    persist(prefix, automatic=True)
                                    st.rerun()
                        else:
                            st.caption('ℹ️ Sin NEE validadas en EPP para este alumno (puedes redactar libremente en el campo superior).')

                    if campo == 'Contextos' and FORMATOS.get(doc['formato'],{}).get('contextos'):
                        opts = FORMATOS[doc['formato']]['contextos']
                        curr_ctx = str(row.get(campo,'') or '').strip()
                        c_idx = opts.index(curr_ctx) + 1 if curr_ctx in opts else 0
                        c_sel = st.selectbox('Contexto normativo', ['(Escribir libre)'] + opts, index=c_idx, key=f'{key}_ctx_sel')
                        if c_sel != '(Escribir libre)' and c_sel != curr_ctx:
                            st.session_state[prefix+'_doc'] = f.editar_celda(st.session_state[prefix+'_doc'], tabla, i, campo, c_sel)
                            st.session_state.pop(prefix+'_pdf', None)
                            persist(prefix, automatic=True)
            c_act1, c_act2, c_act3 = st.columns([1, 1, 1])
            with c_act1:
                if st.button('⬆️ Insertar arriba', key=f'{prefix}_{gen}_{tabla}_{i}_ins_arriba', help='Insertar una fila vacía arriba de esta'):
                    abrir(prefix, f.insertar_fila(st.session_state[prefix+'_doc'], tabla, i))
                    persist(prefix, automatic=True)
                    st.rerun()
            with c_act2:
                if st.button('⬇️ Insertar abajo', key=f'{prefix}_{gen}_{tabla}_{i}_ins_abajo', help='Insertar una fila vacía debajo de esta'):
                    abrir(prefix, f.insertar_fila(st.session_state[prefix+'_doc'], tabla, i + 1))
                    persist(prefix, automatic=True)
                    st.rerun()
            with c_act3:
                if st.button('🗑️ Eliminar fila', key=f'{prefix}_{gen}_{tabla}_{i}_eliminar', help='Eliminar esta fila de la planeación'):
                    abrir(prefix, f.quitar_fila(st.session_state[prefix+'_doc'], tabla, i))
                    persist(prefix, automatic=True)
                    st.rerun()
    if not doc['tablas'][tabla]:st.caption('Sin contenido todavía. Redacta o solicita una propuesta a partir de evidencia documentada.')
    if st.button('Añadir fila · '+f.TITULOS[tabla],key=f'{prefix}_{gen}_{tabla}_add'):
        abrir(prefix,f.nueva_fila(st.session_state[prefix+'_doc'],tabla));persist(prefix);st.rerun()

def panel(prefix,persist,abrir,texto,materiales,curriculo,ia,autosave,preview,field):
    doc=st.session_state[prefix+'_doc'];s.autorizar(doc,True)
    if doc['metadatos'].get('version_contexto')!=s.VERSION_CONTEXTO:
        doc=s.preparar_contexto(doc);abrir(prefix,doc);st.session_state[prefix+'_pending']=True
    st.caption('Edita sobre tu formato. Los datos y fuentes existentes se reutilizan; la IA propone solo cuando lo solicitas.')
    from ui.planeacion_intervenciones_nee import panel as panel_nee
    panel_nee(prefix,persist,abrir)
    with st.container(border=True):
        st.subheader(FORMATOS[doc['formato']]['titulo']);datos=doc['datos'];izq,der=st.columns(2)
        izq.write('Escuela regular: '+datos['Escuela regular']);izq.write('CCT: '+datos.get('CCT',''))
        izq.write('Servicio de apoyo: '+datos.get('Servicio de apoyo','USAER 02-E'));izq.write('Zona: '+str(datos.get('Zona','001')))
        der.write('Especialista: '+datos['Nombre del especialista']);der.write('Función: '+datos['Función'])
        der.write('Curso escolar: '+datos['Curso escolar']+' · Trimestre: '+str(datos['Trimestre']))
        st.write('Periodo: '+datos['Periodo'])
        st.dataframe(pd.DataFrame(datos['Alumnos']).drop(columns=['ID_Alumno','ID_Maestro_Regular'],errors='ignore'),hide_index=True)
        st.caption('Datos del padrón. El grado de referencia curricular no cambia el grado de inscripción.')
        if not datos.get('CCT'):texto(prefix,'datos','CCT','CCT no registrado: verifica y completa')
    autosave(prefix)
    if doc.get('observaciones_director'):st.info('Dirección: '+doc['observaciones_director'])
    with st.expander('Expediente, documentos y referentes oficiales'):
        if st.button('Actualizar información del expediente',key=prefix+'_formato_fuentes'):
            try:s.refrescar_evidencias();abrir(prefix,s.preparar_contexto(st.session_state[prefix+'_doc']));persist(prefix);st.rerun()
            except Exception:st.warning('No se confirmó la actualización. Tu borrador se conserva.')
        for fuente in doc['metadatos'].get('fuentes',[]):
            with st.expander(fuente['referencia']+' · '+fuente['tipo']+' · '+fuente.get('fecha','')):st.write(fuente['texto'])
        if doc['metadatos'].get('fuentes_pendientes'):st.warning('Hay fuentes pendientes de lectura. Confirma antes de generar.')
        materiales(prefix,doc);curriculo(prefix,doc)
    with st.expander('Necesidades y apoyos que sustentan este formato',expanded=not bool(doc['metadatos'].get('fuentes'))):
        texto(prefix,'metadatos','necesidades_confirmadas','Necesidades y apoyos documentados (incluye la referencia de origen)')
        st.caption('Describe lo observado y su origen; una condición por sí sola no determina la actividad.')
    cur=contexto_ia(st.session_state[prefix+'_doc'])
    if cur.get('referentes_por_grado'):
        with st.expander('Contenido y PDA del formato · referencias verificadas'):
            for r in cur['referentes_por_grado']:
                st.write(str(r['grado'])+'° · '+r['contenido']);st.write(r['pda']);st.caption(r['fuente']+' · página '+str(r['pagina_pdf']))
    if doc['formato']=='XXI':
        texto(prefix,'metadatos','fuente_iepp','Referencia del IEPP: fecha, folio o ubicación del informe')
        key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_formato_iepp'
        st.checkbox('Las NEE fueron confirmadas en el IEPP.',value=bool(doc['metadatos'].get('NEE confirmadas desde IEPP')),key=key,on_change=field,args=(prefix,key,'metadatos','NEE confirmadas desde IEPP'))
        for campo in ('Necesidades educativas específicas asociadas a','Maestro de grupo','Vigencia en cursos escolares'):texto(prefix,'datos',campo)
    else:
        with st.expander('Proponer el contenido de mi formato con IA'):
            from ui.planeacion_generacion import panel_generacion
            panel_generacion(prefix,persist,abrir)
    if doc['metadatos'].get('modalidad_planeacion')=='grupal':
        st.markdown('#### Planeación grupal · actividades por alumno y área')
        guia=guia_grupal(st.session_state[prefix+'_doc']);enlazada=doc['metadatos'].get('guia_compartida')
        key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_formato_guia';basekey=key+'_base'
        if basekey not in st.session_state:st.session_state[basekey]=deepcopy(guia['filas'])
        base=st.session_state[basekey]
        st.data_editor(pd.DataFrame(base,columns=['ID_Alumno',*GUIA_XIX]).drop(columns='ID_Alumno'),hide_index=True,
            disabled=True if enlazada else ['Nombre alumno','Discapacidad o condición'],key=key,on_change=_guia,args=(prefix,key,base,persist))
        if enlazada:st.caption('Guía compartida: edita aportaciones en Trabajo colaborativo y actualiza conexiones.')
        else:
            for i,row in enumerate(guia_grupal(st.session_state[prefix+'_doc'])['filas']):
                with st.expander('Editar texto completo · '+row['Nombre alumno']):
                    cols=st.columns(2)
                    for j,campo in enumerate(GUIA_XIX[2:]):
                        key=f'{prefix}_{st.session_state.get(prefix+"_generation",0)}_guia_texto_{i}_{campo}'
                        with cols[j%2]:st.text_area(campo,value=str(row.get(campo,'') or ''),height=130,key=key,on_change=_guia_texto,args=(prefix,key,i,campo,persist,abrir))
        st.caption('Situación final se completa después con resultados observados, no con predicciones.')
    for tabla in FORMATOS[doc['formato']]['tablas']:
        if tabla=='evaluacion_final':
            with st.expander('Resultados al finalizar'):_tabla(prefix,tabla,persist,abrir)
        else:_tabla(prefix,tabla,persist,abrir)
    from services.planeacion_equipo import aplica
    if aplica(doc):
        from ui.planeacion_equipo import panel as equipo
        with st.expander('Organización, competencias y sesiones del equipo especialista'):
            equipo(prefix,st.session_state[prefix+'_doc'],persist,abrir)
    for campo in doc['textos']:texto(prefix,'textos',campo)
    with st.expander('Ideas adicionales para mejorar una actividad'):ia(prefix,st.session_state[prefix+'_doc'])
    from ui.planeacion_continuidad import panel as continuidad
    continuidad(prefix,abrir,persist)
    actual=st.session_state[prefix+'_doc'];faltas=s.revisar(actual)
    with st.expander('Revisión antes de enviar · '+str(len(faltas))+' pendientes'):
        for falta in faltas:st.write('• '+falta)
    izquierda,derecha=st.columns(2)
    if izquierda.button('Guardar borrador',key=prefix+'_formato_save'):persist(prefix);st.rerun()
    if derecha.button('Enviar a Dirección',key=prefix+'_formato_send',disabled=bool(faltas)):persist(prefix,'ENVIADO');st.rerun()
    st.download_button('Descargar respaldo editable',json.dumps(actual,ensure_ascii=False,indent=2),file_name='planeacion-'+actual['id']+'.json',mime='application/json',key=prefix+'_formato_backup')
    st.subheader('Vista previa de tu planeación')
    st.caption('Mismo formato de descarga, con referencias y complementos. No consulta IA.')
    with st.expander('Ver la hoja y descargar PDF'):
        try:
            from ui.planeacion import _pdf_sesion
            pdf=_pdf_sesion(prefix,actual);preview(prefix+'_formato_preview',pdf)
            st.download_button('Descargar PDF',pdf,file_name='planeacion-'+actual['id']+'.pdf',mime='application/pdf',key=prefix+'_formato_pdf')
        except Exception:st.warning('No se pudo preparar la vista. Tu borrador se conserva.')
