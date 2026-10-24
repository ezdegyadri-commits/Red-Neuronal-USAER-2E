"""Una misma acción de archivo para documentos generados y escaneados."""
import streamlit as st
from config.settings import SCHOOL_YEAR
from services import archivo_expediente as archivo


def ids_contexto(frame,identificador):
    """Resuelve un contexto explícito por IDs, nunca por nombre del archivo."""
    from services.expediente_contexto import ids_contexto as resolver
    return resolver(frame,identificador)


def boton(ids,tipo,contenido,nombre,key,fuente='',ciclo=SCHOOL_YEAR,etapa='',disabled=False):
    if not st.session_state.get('autenticado') or not st.session_state.get('usuario'):return
    try:
        destino=archivo.contexto(ids,tipo,ciclo,etapa)
        st.caption('Destino: expediente '+destino['Ambito']+' · '+destino['Ciclo']+'. Se archiva una copia identificable de esta versión, no se publica ni se modifica el original.')
    except Exception as exc:
        st.caption('Para añadir a expediente: '+str(exc));return
    if st.button('Añadir a expediente',key=key,disabled=disabled):
        try:
            data=contenido() if callable(contenido) else contenido
            archivo.guardar(ids,tipo,ciclo,nombre,bytes(data),fuente,etapa)
            st.success('Documento verificado y añadido al expediente '+destino['Ambito']+'. Si vuelves a pulsar, la misma copia no se duplica.')
        except Exception as exc:st.warning('No se confirmó el archivo: '+str(exc)+' El documento original se conserva.')


def panel(ids,prefix,grupal=False):
    st.subheader('Documentos del expediente')
    st.caption('Archivo privado y conectado · Manual USAER, Anexos VI y IX. Los requisitos varían según la etapa y el caso; no se exige llenar documentos que no correspondan.')
    try:
        disponibles=archivo.listar()
        from services import epp
        from services.expediente_automatico import organizar_archivados
        if any(r.get('Ambito')=='grupal' and r.get('Tipo') in archivo.CONTEXTUAL for r in disponibles):
            try:disponibles=organizar_archivados(disponibles,{d['alumno'] for d in epp.listar(incluir_bajas=True)})
            except Exception:st.caption('La etapa EPP no pudo actualizarse ahora. Se conserva la clasificación original y todos los archivos disponibles.')
        contexto_ids=set(map(str,ids))
        import json
        if grupal:
            destino=archivo.contexto(ids,'Planeación grupal',SCHOOL_YEAR)
            docs=[r for r in disponibles if r['Ambito']=='grupal' and all(str(r.get(k,''))==str(destino[k]) for k in ('ID_Escuela','Grado','Grupo'))]
        else:docs=[r for r in disponibles if bool(contexto_ids & set(json.loads(r['ID_Alumnos_JSON']))) and r['Ambito']=='individual']
    except Exception:
        st.warning('No se pudo consultar el índice del expediente. No se han modificado documentos.');return
    if docs:
        from ui.tablas import tabla_paginada
        import pandas as pd
        tabla_paginada(pd.DataFrame(docs)[['Tipo','Nombre','Ciclo','Fecha']],prefix+'_tabla')
        porid={r['ID_Documento']:r for r in docs}
        elegido=st.selectbox('Documento para recuperar',list(porid),format_func=lambda k:porid[k]['Tipo']+' · '+porid[k]['Nombre']+' · '+porid[k]['Fecha'][:16],key=prefix+'_doc')
        with st.expander('Vista previa · síntesis del documento precargado'):
            from ui.documento_sintesis import archivado
            archivado(elegido,porid[elegido],lambda:archivo.descargar(elegido)[1],prefix+'_preview')
        if st.button('Preparar descarga privada',key=prefix+'_preparar'):
            try:
                row,data=archivo.descargar(elegido)
                st.download_button('Descargar documento',data,file_name=row['Nombre'],mime=row['Mime'],key=prefix+'_descarga')
            except Exception as exc:st.warning('No se pudo verificar la descarga: '+str(exc))
    else:st.info('Todavía no hay copias archivadas aquí. Los instrumentos conectados que ya existían no se borran ni se sustituyen.')
    with st.expander('Planeaciones e informes que ya existen en la plataforma'):
        _conectados(ids,prefix,grupal)
    with st.expander('Índice automático y cronológico de documentos generados'):
        if st.checkbox('Consultar índice conectado',key=prefix+'_indice_vivo'):
            try:
                from services.expediente_automatico import documentos_vivos,orden_cronologico
                vivos=documentos_vivos(ids,grupal)
                cronologia=orden_cronologico(docs+vivos)
                if cronologia:
                    import pandas as pd
                    vista=pd.DataFrame(cronologia)
                    st.dataframe(vista[[c for c in ('Fecha_Documento','Fecha','Seccion','Tipo','Nombre','Estado','Origen_Vivo') if c in vista]],hide_index=True,width='stretch')
                    fuentes=sorted({r['Origen_Vivo'] for r in vivos})
                    if fuentes:
                        origen=st.selectbox('Abrir módulo de origen',fuentes,key=prefix+'_origen_vivo')
                        if st.button('Ir al documento de origen',key=prefix+'_ir_origen'):
                            st.session_state['navegacion_principal']=origen;st.rerun()
                else:st.info('No hay documentos vinculados por identificador para este expediente.')
                st.caption('Los registros se integran por ID y fecha, sin borrar las fuentes. Los borradores no equivalen a informes concluidos. Las fechas no disponibles quedan al final, sin inventarlas.')
            except Exception:st.warning('La lectura del índice está incompleta. Se conservan los archivos y versiones anteriores; vuelve a intentar.')
    with st.expander('Qué integra este expediente según el manual'):
        tipos=archivo.GRUPAL+archivo.CONTEXTUAL if grupal else archivo.INDIVIDUAL+archivo.CONTEXTUAL
        presentes={r['Tipo'] for r in docs}
        for tipo in tipos:st.write(('✓ Archivado · ' if tipo in presentes else '○ Según etapa y caso · ')+tipo)
        if grupal:st.caption('Al iniciar EPP, sus documentos específicos deben pasar al expediente individual. Un documento colectivo no se mueve completo si incluye información de otros alumnos.')
    with st.expander('Añadir documento escaneado',expanded=not docs):
        subida=st.file_uploader('PDF o foto legible · hasta 5 MB',type=['pdf','png','jpg','jpeg'],key=prefix+'_archivo',max_upload_size=5)
        sugerido=archivo.sugerir_tipo(subida.name) if subida else None
        if subida:
            import hashlib
            carga=hashlib.sha256(subida.getvalue()).hexdigest()[:16]
        else:carga='sin_archivo'
        tipos=archivo.TIPOS if grupal else archivo.INDIVIDUAL+archivo.CONTEXTUAL
        tipo=st.selectbox('Tipo de documento',tipos,index=tipos.index(sugerido) if sugerido in tipos else None,
            placeholder='Confirma qué documento es',key=prefix+'_tipo_'+carga)
        if sugerido:st.caption('Sugerencia por el nombre del archivo; confirma el tipo. El contenido no se envía a IA y el nombre no determina a quién pertenece.')
        etapa=''
        if tipo in archivo.CONTEXTUAL:
            etapa=st.selectbox('Etapa del documento',['Atención grupal','EPP iniciada'],index=0 if grupal else 1,key=prefix+'_etapa')
        destinatarios=ids
        if grupal and (tipo in archivo.INDIVIDUAL or etapa=='EPP iniciada'):
            frame=archivo.visibles();nombres={str(r['ID_Alumno']):r.get('Nombre_Completo',r['ID_Alumno']) for r in frame.fillna('').to_dict('records')}
            destinatarios=st.multiselect('Alumno(s) a quienes corresponde este documento individual',ids,format_func=lambda k:nombres.get(k,k),key=prefix+'_destinatarios_'+carga)
        ciclo=st.text_input('Ciclo del documento',value=SCHOOL_YEAR,key=prefix+'_ciclo')
        if subida and tipo:
            try:
                destino=archivo.contexto(destinatarios,tipo,ciclo,etapa)
                did=archivo.guardar(destinatarios,tipo,ciclo,subida.name,subida.getvalue(),'Escaneado',etapa)
                st.success('Escaneo integrado automáticamente al expediente '+destino['Ambito']+'. La misma copia no se duplica.')
                from ui.documento_sintesis import archivado
                archivado(did,{**destino,'Nombre':subida.name},subida.getvalue,prefix+'_subida_preview')
            except Exception as exc:
                st.warning('El archivo todavía no está confirmado: '+str(exc)+' El original se conserva.')
                boton(destinatarios,tipo,subida.getvalue,subida.name,prefix+'_anexar','Escaneado',ciclo,etapa)


def _conectados(ids,prefix,grupal=False):
    """Proyección por ID, sin duplicar ni migrar las fuentes históricas."""
    from services import planeacion as planes,epp
    try:
        planes.identidad();documentos={}
        for d in planes.versiones_actuales():documentos[d['id']]=d
        candidatos=[]
        destino=archivo.contexto(ids,'Planeación grupal',SCHOOL_YEAR) if grupal else None
        for d in documentos.values():
            if d['metadatos'].get('borrador_eliminado'):continue
            if grupal:
                from utils.escolar import grado_canonico,grupo_canonico
                if d['metadatos'].get('modalidad_planeacion')!='grupal' or str(d['datos']['ID_Escuela'])!=str(destino['ID_Escuela']):continue
                if {(grado_canonico(a.get('Grado')),grupo_canonico(a.get('Grupo'))) for a in d['datos']['Alumnos']}!={(destino['Grado'],destino['Grupo'])}:continue
            elif d['metadatos'].get('modalidad_planeacion')=='grupal' or not set(ids)&{a['ID_Alumno'] for a in d['datos']['Alumnos']}:continue
            try:planes.autorizar(d,incluir_bajas=True)
            except PermissionError:continue
            candidatos.append(d)
        if candidatos:
            porid={d['id']:d for d in candidatos}
            from services.planeacion_compartida import etiqueta
            did=st.selectbox('Planeación vinculada',list(porid),format_func=lambda k:etiqueta(porid[k]),key=prefix+'_plan')
            if st.button('Preparar PDF de la planeación vinculada',key=prefix+'_plan_pdf'):
                from documents.planeacion_papel import generar_pdf
                d=porid[did];pdf=generar_pdf(d,archivo=True)
                st.download_button('Descargar planeación vinculada',pdf,file_name='planeacion-'+did+'.pdf',mime='application/pdf',key=prefix+'_plan_download')
        informes=[] if grupal else [d for d in epp.listar(incluir_bajas=True) if d['alumno'] in set(ids)]
        if informes:
            porid={d['id']:d for d in informes}
            eid=st.selectbox('EPP vinculada',list(porid),format_func=lambda k:porid[k]['ciclo']+' · '+k[-10:],key=prefix+'_epp')
            with st.expander('Vista previa sintetizada de la EPP vinculada'):
                from services.documento_sintesis import sintetizar
                d=porid[eid]
                hallazgos='\n'.join(str(v) for p in d['partes'].values() for v in
                                    [p.get('contenido',{}).get('sintesis',''),*p.get('contenido',{}).get('campos',{}).values()] if str(v).strip())
                st.write(sintetizar(hallazgos)['resumen'] or 'No hay hallazgos redactados todavía.')
                nee=d['partes'].get('Conclusión',{}).get('contenido',{}).get('nee',[])
                for n in nee:
                    if n.get('NEE'):st.write('• '+n['NEE'])
                st.caption('Síntesis de los apartados capturados. Solo una conclusión vigente y validada alimenta el selector de NEE de planeación; un borrador no equivale a evaluación concluida.')
            if st.button('Preparar PDF de la EPP vinculada',key=prefix+'_epp_pdf'):
                from documents.epp import generar_pdf
                d=porid[eid];pdf=generar_pdf(d,epp.alumno_autorizado(d['alumno'],incluir_bajas=True))
                st.download_button('Descargar EPP vinculada',pdf,file_name='EPP-'+eid[:12]+'.pdf',mime='application/pdf',key=prefix+'_epp_download')
        if not candidatos and not informes:st.caption('No hay planeaciones o EPP guardadas vinculadas a estos destinatarios en tu ámbito.')
        st.caption('Se conservan las fuentes. Los documentos colectivos con otros alumnos no se trasladan a una escuela nueva. Los registros antiguos sin ID necesitan revisión para evitar atribuirlos por homonimia.')
    except Exception:st.caption('No se pudo consultar toda la documentación conectada. Las copias archivadas y las fuentes originales se conservan; reintenta.')


def pagina_grupal(df):
    from utils.escolar import grado_canonico,grupo_canonico
    rows=df.fillna('').copy()
    if rows.empty:st.info('No hay grupos en tu asignación actual.');return
    escuelas=sorted(rows['Nombre_Escuela'].astype(str).unique())
    escuela=st.selectbox('Escuela del expediente grupal',escuelas,key='archivo_grupal_escuela')
    rows=rows.loc[rows['Nombre_Escuela'].astype(str).eq(escuela)].copy()
    rows['_grupo']=[grado_canonico(r.get('Grado'))+' '+grupo_canonico(r.get('Grupo')) for r in rows.to_dict('records')]
    grupo=st.selectbox('Grado y grupo del expediente',sorted(rows['_grupo'].unique()),key='archivo_grupal_grupo')
    rows=rows.loc[rows['_grupo'].eq(grupo)]
    st.caption(str(len(rows))+' alumnos vinculados. No se mezclan escuelas ni grados.')
    panel(rows['ID_Alumno'].astype(str).tolist(),'archivo_grupal_'+str(rows.iloc[0]['ID_Escuela'])+'_'+grupo,True)
