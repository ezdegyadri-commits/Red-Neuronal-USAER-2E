"""Aplicación digital y resultados externos, reutilizando el guardado de la EPP."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import time
import pandas as pd
import streamlit as st
from services import epp_instrumentos as motor


@st.fragment(run_every=30)
def _estado(prefix,get_value,save_value):
    if not st.session_state.get(prefix+'_aplicacion_sucia'):return
    if time.monotonic()-st.session_state.get(prefix+'_intento',0)>=30:
        st.session_state[prefix+'_intento']=time.monotonic()
        if save_value(get_value(),True):st.session_state[prefix+'_aplicacion_sucia']=False
    st.caption('Aplicación pendiente de confirmación; puedes continuar.' if st.session_state.get(prefix+'_aplicacion_sucia') else 'Borrador de aplicación confirmado.')


def digital(doc,area,prefix,get_value,save_value,nombre=None,codigo_preseleccionado=None):
    codigos=[k for k,v in motor.DEFINICIONES.items() if v['area']==area and (not nombre or nombre==v['nombre'])]
    if not codigos:
        st.info('Este instrumento aún no tiene un protocolo y reglas de corrección verificadas en la plataforma. Registra resultados profesionales o utiliza Foto / escaneo. No se calculan puntuaciones por aproximación.')
        return
    codigo=codigo_preseleccionado if codigo_preseleccionado in codigos else st.selectbox('Formato digital disponible',codigos,format_func=lambda k:motor.DEFINICIONES[k]['nombre'],key=prefix+'_digital')
    d=motor.DEFINICIONES[codigo];key=prefix+'_digital_'+codigo
    def captura():return deepcopy(get_value().get('aplicaciones_en_curso',{}).get(codigo,motor.plantilla(codigo)))
    def guardar_captura(cap):
        value=deepcopy(get_value());value.setdefault('aplicaciones_en_curso',{})[codigo]=motor.validar(codigo,cap)
        value['validada']=False;st.session_state[key+'_aplicacion_sucia']=True
        force=time.monotonic()-st.session_state.get(key+'_intento',0)>=30
        if force:st.session_state[key+'_intento']=time.monotonic()
        ok=save_value(value,force)
        if ok and force:st.session_state[key+'_aplicacion_sucia']=False
    def fecha():
        cap=captura();v=st.session_state.get(key+'_fecha');cap['fecha']=v.isoformat() if v else '';guardar_captura(cap)
    cap=captura()
    st.caption(motor.FUENTE+' · pp. '+d['paginas']+'. Se conservan las opciones originales; «No observado» identifica pendientes, no equivale a «No».')
    st.date_input('Fecha de aplicación del formato',value=date.fromisoformat(cap['fecha']) if cap['fecha'] else None,format='DD/MM/YYYY',key=key+'_fecha',on_change=fecha)
    groups={}
    for q in d['items']:groups.setdefault(tuple(q['opciones']),[]).append(q)
    for n,(opciones,questions) in enumerate(groups.items()):
        tablekey=key+'_respuestas_'+str(n);basekey=tablekey+'_base'
        rows=[{'Ítem':q['id'],'Aspecto':q['texto'],'Respuesta':cap['respuestas'][q['id']]['respuesta'],'Observaciones':cap['respuestas'][q['id']]['observaciones']} for q in questions]
        if basekey not in st.session_state or tablekey not in st.session_state:st.session_state[basekey]=rows
        def cambio(tk=tablekey,bk=basekey):
            current=motor.editar_respuestas(codigo,captura(),st.session_state[bk],st.session_state.get(tk,{}))
            guardar_captura(current)
        config={'Respuesta':st.column_config.SelectboxColumn('Respuesta',options=list(opciones),required=True) if opciones else st.column_config.TextColumn('Respuesta',max_chars=500),
                'Aspecto':st.column_config.TextColumn('Aspecto',width='large'),'Observaciones':st.column_config.TextColumn('Observaciones',max_chars=500)}
        st.data_editor(pd.DataFrame(st.session_state[basekey]),hide_index=True,num_rows='fixed',disabled=['Ítem','Aspecto'],column_config=config,key=tablekey,on_change=cambio,width='stretch')
    result=motor.calcular(codigo,captura())
    st.write('Registros respondidos: '+str(result['respondidos'])+'/'+str(result['total_registros'])+' · Pendientes: '+str(len(result['pendientes'])))
    if result['conteos']:st.write(result['conteos'])
    st.caption(result['alcance'])
    backup={'tipo':'USAER-aplicacion-v1','documento':doc['id'],'area':area,'instrumento':codigo,'captura':captura()}
    st.download_button('Respaldar mis respuestas',json.dumps(backup,ensure_ascii=False,indent=2),file_name='aplicacion-'+codigo+'.json',mime='application/json',key=key+'_backup')
    with st.expander('Recuperar respuestas desde un respaldo'):
        upload=st.file_uploader('Respaldo de esta aplicación (.json)',type=['json'],key=key+'_restaurar_archivo')
        check=st.checkbox('Confirmo recuperar las respuestas de este alumno e instrumento',key=key+'_restaurar_confirmar')
        if upload and st.button('Recuperar aplicación',disabled=not check,key=key+'_restaurar'):
            try:
                if len(upload.getvalue())>30000:raise ValueError('El respaldo es demasiado extenso.')
                r=json.loads(upload.getvalue())
                if any(r.get(k)!=backup[k] for k in ('tipo','documento','area','instrumento')):raise ValueError('El respaldo corresponde a otro alumno, función o instrumento.')
                guardar_captura(motor.validar(codigo,r.get('captura')))
                for k in list(st.session_state):
                    if k.startswith(key+'_respuestas_') or k==key+'_fecha':st.session_state.pop(k,None)
                st.rerun()
            except (ValueError,TypeError,PermissionError) as exc:st.warning(str(exc))
    _estado(key,get_value,save_value)
    if st.button('Guardar borrador de aplicación',key=key+'_guardar'):
        if save_value(get_value(),True):st.session_state[key+'_aplicacion_sucia']=False;st.success('Borrador confirmado.')
    checked=st.checkbox('Revisé las respuestas y corresponden al alumno de esta EPP',key=key+'_revisada')
    if st.button('Resumir respuestas e incorporar al informe',disabled=not checked,key=key+'_incorporar'):
        try:
            current=deepcopy(doc);current['partes'].setdefault(area,{})['contenido']=deepcopy(get_value())
            value=motor.incorporar(current,area,codigo,captura(),revisada=checked)
            if save_value(value,True):st.success('Resultados descriptivos incorporados al mismo informe. La revisión profesional continúa pendiente.')
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))


@st.fragment(run_every=1)
def _lectura_visual(key):
    job=st.session_state.get(key+'_vision')
    if not job:return
    if not job.done():st.progress(35,text='Leyendo los resultados del instrumento…');return
    st.session_state.pop(key+'_vision',None)
    try:
        st.session_state[key+'_lectura']=job.result()
        st.session_state.pop(key+'_vision_error',None)
    except Exception:st.session_state[key+'_vision_error']='No se completó la lectura visual; conserva el archivo y prueba la lectura local o una imagen más clara.'
    st.rerun(scope='app')


def externo(doc,area,prefix,get_value,save_value,solo_carga=False):
    st.caption('Carga el informe de resultados o una foto legible. Puedes leerlo localmente o autorizar su lectura visual con Gemini. Revisa la síntesis antes de vincularla. No envíes cuadernillos completos, reactivos protegidos ni datos de terceros.')
    source=st.radio('Origen del documento',['Archivo o escaneo','Tomar fotografía'],horizontal=True,key=prefix+'_origen')
    if source=='Tomar fotografía':upload=st.camera_input('Fotografiar informe de resultados',key=prefix+'_camara')
    else:upload=st.file_uploader('Informe externo o escaneo',type=['pdf','png','jpg','jpeg','webp','docx'],max_upload_size=32,key=prefix+'_archivo')
    if not upload:return
    data=upload.getvalue()
    if len(data)>32*1024*1024:st.warning('Usa un archivo de hasta 32 MB.');return
    fid=hashlib.sha256(data).hexdigest();key=prefix+'_externo_'+fid[:16]
    visual=False
    ext=upload.name.rsplit('.',1)[-1].lower()
    if solo_carga and ext in ('pdf','png','jpg','jpeg','webp') and len(data)<=5*1024*1024:
        visual=st.checkbox('Autorizar lectura visual con IA de este archivo del alumno',key=key+'_autorizar_vision')
    if st.button('Leer foto o escaneo',key=key+'_leer',disabled=key+'_vision' in st.session_state):
        try:
            st.session_state.pop(key+'_vision_error',None)
            if visual:
                from ai.epp_contextual import enviar_lectura,configuracion
                mime={'pdf':'application/pdf','png':'image/png','jpg':'image/jpeg','jpeg':'image/jpeg','webp':'image/webp'}[ext]
                st.session_state[key+'_vision']=enviar_lectura(data,mime,configuracion())
            else:
                from services.materiales_planeacion import leer_material
                with st.spinner('Leyendo el documento sin enviarlo a IA…'):read=leer_material(upload.name,data)
                st.session_state[key+'_lectura']=read
        except Exception:st.warning('No se pudo leer el archivo. Intenta una foto frontal y nítida o un PDF con texto; el informe anterior no cambió.')
    _lectura_visual(key)
    if st.session_state.get(key+'_vision_error'):st.warning(st.session_state[key+'_vision_error'])
    read=st.session_state.get(key+'_lectura')
    if not read:return
    for aviso in read.get('avisos',[]):st.caption(aviso)
    from ui.documento_sintesis import vista
    texto=vista(read.get('texto',''),key)['resumen']
    nombre=st.text_input('Instrumento o informe que emitió el profesional',key=key+'_nombre')
    fecha=st.date_input('Fecha de la evaluación externa',value=None,format='DD/MM/YYYY',key=key+'_fecha')
    reviewed=st.checkbox('Verifiqué alumno, instrumento, fecha y resultados contra el original; no hay información de terceros',key=key+'_revisado')
    archivable=upload.name.rsplit('.',1)[-1].lower() in ('pdf','png','jpg','jpeg') and len(data)<=5*1024*1024
    st.caption('Al guardar se conservarán el original y su síntesis en el expediente, sin otro botón de archivo.' if archivable else
        'Se conservarán los resultados revisados en la EPP. Para conservar también el original en el expediente, utiliza PDF, JPG o PNG de hasta 5 MB.')
    fingerprint=hashlib.sha256(json.dumps([texto,nombre,str(fecha)]).encode()).hexdigest()
    if st.button('Vincular instrumento a esta EPP' if solo_carga else 'Guardar evaluación y preparar análisis',disabled=not reviewed or not texto.strip(),key=key+'_preparar'):
        try:
            from services.epp_entrada import entrada_directa
            from services import epp as s
            ev=entrada_directa({'Instrumento o técnica aplicada':nombre,'Fecha de aplicación (AAAA-MM-DD)':str(fecha or ''),'Resultados y observaciones documentadas':texto})
            ev.update(entrada='EXTERNA_REVISADA',archivo_sha256=fid)
            value=deepcopy(get_value())
            value['evaluaciones']=[e for e in value['evaluaciones'] if e.get('archivo_sha256')!=fid and e['id']!=ev['id']]+[ev]
            value['validada']=False
            if not save_value(value,True):raise ValueError('La evaluación sigue pendiente de confirmación. Reintenta el guardado; no se envió a IA.')
            if archivable:
                try:
                    from services.evaluacion_archivo import guardar as archivar
                    archivar(doc,area,upload.name,data,texto)
                    st.success('Original y síntesis confirmados en el expediente; disponibles como antecedentes.')
                except Exception:
                    st.warning('Los resultados están guardados en la EPP, pero no se confirmó el archivo o su síntesis. Conserva esta carga y vuelve a pulsar Guardar evaluación; no se duplicará una copia ya confirmada.')
            if solo_carga:
                st.success('Instrumento vinculado. Ya puedes usar Redactar EPP Automáticamente.')
                st.rerun()
            plan=s.contexto(doc)
            st.session_state[key+'_resumen']=s.resumen(doc,area,value,plan)
            from services.epp_entrada import huella_instrumentos
            st.session_state[key+'_fuente']=(fingerprint,huella_instrumentos(doc,area,get_value()))
            st.session_state.pop(key+'_consent',None);st.session_state.pop(key+'_resumen_editado',None)
        except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,PermissionError,RuntimeError)) else 'No se pudo reunir el contexto; la evaluación guardada se conserva. Reintenta preparar el análisis.')
    if solo_carga or key+'_resumen' not in st.session_state:return
    from services.epp_entrada import huella_instrumentos
    stale=st.session_state.get(key+'_fuente')!=(fingerprint,huella_instrumentos(doc,area,get_value()))
    if stale:st.warning('Cambió la lectura, el instrumento o la fecha. Prepara otra vez el análisis para no usar un resumen anterior.')
    resumen=st.text_area('Resumen para el motor: elimina nombres, CURP, domicilios y contactos',value=st.session_state[key+'_resumen'],max_chars=12000,height=180,key=key+'_resumen_editado')
    consent=st.checkbox('Revisé el resumen anonimizado y autorizo enviarlo a Gemini para proponer mis apartados',key=key+'_consent')
    if st.button('Analizar resultados y completar solo apartados vacíos',disabled=not consent or stale,key=key+'_analizar'):
        try:
            from ai.epp import generar
            from services.epp_modelo import validar_parte
            bar=st.progress(10,text='Preparando resultados revisados…')
            digest=hashlib.sha256((area+resumen).encode()).hexdigest()
            cache=st.session_state.get(key+'_propuesta',{})
            result=cache.get('resultado') if cache.get('huella')==digest else None
            if result is None:
                result=generar(resumen,area);st.session_state[key+'_propuesta']={'huella':digest,'resultado':result}
            bar.progress(80,text='Verificando fuentes y conservando aportaciones…')
            value=deepcopy(get_value())
            for field,text in result['campos'].items():
                if not value['campos'].get(field,'').strip():value['campos'][field]=text
            value['pendientes_ia']=result['faltantes'];value['validada']=False
            value=validar_parte(area,value)
            if save_value(value,True):bar.progress(100,text='Borrador ensamblado y guardado para revisión profesional.')
            else:bar.empty();st.warning('El borrador permanece pendiente de confirmación; no lo generes otra vez, reintenta el guardado.')
        except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'El motor no completó el análisis. Se conservan la evaluación y los textos anteriores; puedes continuar sin IA.')
