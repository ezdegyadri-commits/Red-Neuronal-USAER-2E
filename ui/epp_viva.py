"""Un informe visible y estable; conexiones y análisis fuera de la hoja editable."""
from copy import deepcopy
from datetime import date
import hashlib
import json
import time
import streamlit as st
from services import epp as s, epp_papel as papel
from services.epp_modelo import AREAS, vacia, pendientes, conclusion_vigente
from services.planeacion_guardado_estado import diagnostico


def _key(doc):
    return 'epp_viva_'+hashlib.sha256((s.actor()['cuenta']+'|'+doc['id']).encode()).hexdigest()[:24]


def abrir(doc):
    p=_key(doc)
    st.session_state[p+'_cuenta']=s.actor()['cuenta']
    if p+'_doc' not in st.session_state:st.session_state[p+'_doc']=deepcopy(doc)
    return p


def preparar_cambios(p,nuevo,areas):
    prev=st.session_state[p+'_doc']
    cola=st.session_state.setdefault(p+'_cola',{})
    for area in areas:
        if area not in cola:
            old=prev['partes'].get(area,{})
            cola[area]={'base':papel.contenido(prev,area),'revision':old.get('revision','')}
    st.session_state[p+'_doc']=deepcopy(nuevo)
    st.session_state[p+'_pending']=bool(cola)


def guardar(p,manual=False):
    cola=st.session_state.get(p+'_cola',{})
    if not cola:return True
    if st.session_state.get(p+'_cuenta',s.actor()['cuenta'])!=s.actor()['cuenta']:
        raise PermissionError('La captura pendiente corresponde a otra cuenta.')
    if not manual and time.monotonic()<max(st.session_state.get(p+'_reintentar_en',0),st.session_state.get(p+'_agrupar_hasta',0)):return False
    doc=st.session_state[p+'_doc']
    for area in list(cola):
        try:
            item=cola[area]
            saved=s.guardar_cambios(doc,area,item['base'],papel.contenido(doc,area),item['revision'])
            doc['partes'][area]=saved;del cola[area]
        except Exception as exc:
            d=diagnostico(exc)
            st.session_state[p+'_diagnostico']=d
            st.session_state[p+'_reintentar_en']=time.monotonic()+max(15,d['espera']) if d['espera'] else float('inf')
            st.session_state[p+'_pending']=True
            return False
    st.session_state[p+'_pending']=False
    st.session_state[p+'_agrupar_hasta']=time.monotonic()+30
    st.session_state.pop(p+'_huella_pendiente',None)
    st.session_state.pop(p+'_diagnostico',None);st.session_state.pop(p+'_reintentar_en',None)
    if st.session_state.get(p+'_nonce'):st.session_state[p+'_aceptado']=st.session_state[p+'_nonce']
    return True


def recibir(p,event):
    if not event:return
    nonce=event.get('nonce')
    if not isinstance(nonce,str) or len(nonce)>120:raise ValueError('Envío sin identificador válido.')
    if nonce==st.session_state.get(p+'_nonce'):
        if st.session_state.get(p+'_pending'):guardar(p)
        return
    doc=st.session_state[p+'_doc']
    try:
        nuevo,areas=papel.aplicar(doc,event,huella_esperada=st.session_state.get(p+'_huella_pendiente'))
        preparar_cambios(p,nuevo,areas)
        if areas:st.session_state[p+'_huella_pendiente']=event['huella']
        st.session_state[p+'_nonce']=nonce
        st.session_state.pop(p+'_rechazado',None)
        if guardar(p,manual=event['accion']!='autoguardar'):st.session_state[p+'_aceptado']=nonce
        action=event['accion']
        if action=='inicio':st.session_state[p+'_volver']=True
        elif action in ('antecedentes','ia','opciones','pdf'):st.session_state[p+'_panel']=action
        elif action=='equipo':st.session_state[p+'_lectura']=0
    except (ValueError,PermissionError,RuntimeError) as exc:
        st.session_state[p+'_nonce']=nonce
        st.session_state[p+'_rechazado']=nonce
        st.session_state[p+'_diagnostico']=diagnostico(exc)


def sincronizar(p):
    if time.monotonic()-st.session_state.get(p+'_lectura',0)<10:return
    st.session_state[p+'_lectura']=time.monotonic()
    doc=st.session_state[p+'_doc']
    try:
        # Guardados de cualquier integrante invalidan el caché compartido. Las
        # lecturas periódicas no lo vacían para cada maestra/celda.
        remote=next((d for d in s.listar(True) if d['id']==doc['id']),None)
        if not remote:return
        cola=st.session_state.get(p+'_cola',{})
        for area,part in remote['partes'].items():
            if area not in cola:doc['partes'][area]=deepcopy(part)
        st.session_state.pop(p+'_lectura_error',None)
    except Exception:st.session_state[p+'_lectura_error']=True


@st.fragment(run_every=10)
def hoja(p):
    sincronizar(p);guardar(p)
    doc=st.session_state[p+'_doc']
    from ui.planeacion_papel import editor,refrescar_editor
    d=st.session_state.get(p+'_diagnostico',{})
    spec=papel.hoja(doc)
    if st.session_state.get(p+'_pending') and st.session_state.get(p+'_huella_pendiente'):spec['huella']=st.session_state[p+'_huella_pendiente']
    event=editor(key=p+'_papel',hoja=spec,on_edicion=lambda e:recibir(p,e),
        guardado='' if st.session_state.get(p+'_pending') else max((r.get('fecha','') for r in doc['partes'].values()),default=''),
        aceptado_nonce=st.session_state.get(p+'_aceptado',''),rechazado=st.session_state.get(p+'_rechazado',''),error=d.get('causa',''))
    if event and event.get('nonce')!=st.session_state.get(p+'_nonce'):
        recibir(p,event)
        if st.session_state.get(p+'_volver') or st.session_state.get(p+'_panel'):st.rerun(scope='app')
        refrescar_editor()
    if st.session_state.get(p+'_pending') or d:
        if d:st.warning(d['causa']+' '+d['accion'].replace('planeación','EPP'))
        else:st.caption('Guardado pendiente; puedes seguir escribiendo o abrir otra EPP. El texto de esta hoja se conserva por separado.')
        if st.button('Reintentar guardado de esta EPP',key=p+'_retry'):guardar(p,True);refrescar_editor()
        st.download_button('Respaldar esta EPP pendiente',json.dumps(doc,ensure_ascii=False,indent=2),file_name='EPP-pendiente.json',mime='application/json',key=p+'_backup')
    if st.session_state.get(p+'_lectura_error'):st.caption('No se pudieron actualizar los aportes del equipo. Se reintentará; tu texto no se reemplazó.')


def _incorporar(p,area,value):
    # Capturar el instrumento una vez también completa la tabla del informe.
    if area!='Conclusión':
        nombres=list(dict.fromkeys(e.get('nombre','') for e in value.get('evaluaciones',[]) if e.get('nombre')))
        fechas=list(dict.fromkeys(e.get('fecha','') for e in value.get('evaluaciones',[]) if e.get('fecha')))
        if not value.get('instrumentos','').strip():value['instrumentos']='\n'.join(nombres)
        if not value.get('fecha_aplicacion','').strip():value['fecha_aplicacion']=', '.join(fechas)
    doc=deepcopy(st.session_state[p+'_doc']);doc['partes'].setdefault(area,{})['contenido']=value
    preparar_cambios(p,doc,{area})
    return guardar(p,True)


def herramientas(p):
    doc=st.session_state[p+'_doc'];allowed=papel.editables(doc)
    if not allowed:st.info('Vista de consulta del informe compartido.');return
    area=st.selectbox('Mi área de trabajo',allowed,key=p+'_area_herramientas')
    v=papel.contenido(doc,area)
    st.caption('Los hallazgos y el análisis se incorporan al mismo informe. No se crea otra EPP ni se reescriben aportaciones ajenas.')
    tab1,tab2,tab3=st.tabs(['Antecedentes','Evaluaciones de mi área','Análisis y revisión'])
    with tab1:
        if st.button('Reunir antecedentes del expediente',key=p+'_fuentes'):
            try:
                plan=s.contexto(doc)
                st.session_state[p+'_contexto']=plan
            except Exception:st.warning('No se pudo reunir el expediente. No se borraron los antecedentes ya recuperados.')
        plan=st.session_state.get(p+'_contexto',{})
        if plan.get('metadatos',{}).get('fuentes_pendientes'):st.warning('La consulta está incompleta; no se presume ausencia de antecedentes. Vuelve a reunirlos cuando mejore la conexión.')
        for f in plan.get('metadatos',{}).get('fuentes',[]):
            if f.get('vinculo_verificado') and f.get('alumno')==doc['alumno']:
                with st.expander(str(f.get('tipo','Antecedente'))+' · '+str(f.get('fecha','Sin fecha'))):st.write(f.get('texto',''))
        if not plan:st.caption('Reutiliza eventos, BAP, sugerencias y resultados ya vinculados con este alumno. No se mezclan homónimos ni escuelas.')
    with tab2:
        if area=='Conclusión':st.info('La conclusión reúne los resultados de las áreas; no se aplica un instrumento adicional aquí.')
        else:
            with st.form(p+'_instrumento_'+area,clear_on_submit=False):
                from ui.epp import CATALOGO_INSTRUMENTOS_SEGEY
                cat=st.selectbox('Instrumento de referencia',['Otro instrumento o técnica']+CATALOGO_INSTRUMENTOS_SEGEY.get(area,[]))
                nombre=st.text_input('Nombre del instrumento o técnica (si es otro)')
                fecha=st.date_input('Fecha de aplicación',value=None,format='DD/MM/YYYY')
                resultados=st.text_area('Resultados y observaciones documentadas',max_chars=10000)
                limites=st.text_area('Limitaciones y aspectos por confirmar',max_chars=1000)
                reviewed=st.checkbox('Estos resultados corresponden exclusivamente al alumno de esta EPP')
                add=st.form_submit_button('Incorporar evaluación revisada')
            if add:
                try:
                    from services.epp_entrada import entrada_directa
                    if not reviewed:raise ValueError('Revisa y confirma que la evaluación corresponde a este alumno.')
                    ev=entrada_directa({'Instrumento o técnica aplicada':nombre if cat=='Otro instrumento o técnica' else cat,'Fecha de aplicación (AAAA-MM-DD)':str(fecha or ''),'Resultados y observaciones documentadas':resultados,'Limitaciones y aspectos por confirmar':limites})
                    if not any(e['id']==ev['id'] for e in v['evaluaciones']):v['evaluaciones'].append(ev)
                    v['validada']=False
                    if _incorporar(p,area,v):st.success('Evaluación incorporada al mismo informe.')
                except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
            with st.expander('Escanear o cargar una evaluación'):
                from services.materiales_planeacion import TIPOS,leer_material
                upload=st.file_uploader('Documento de evaluación de este alumno',type=TIPOS,key=p+'_upload_'+area)
                if upload and st.button('Leer documento sin enviarlo a IA',key=p+'_leer_'+area):
                    try:
                        with st.spinner('Leyendo el documento…'):r=leer_material(upload.name,upload.getvalue())
                        st.session_state[p+'_trans_'+area]=r['texto'][:12000]
                        for aviso in r['avisos']:st.caption(aviso)
                    except Exception:st.warning('No se pudo leer. Conserva el original e intenta con un PDF con texto o una imagen más clara.')
                if p+'_trans_'+area in st.session_state:
                    texto=st.text_area('Hallazgos transcritos: revisa y corrige',value=st.session_state[p+'_trans_'+area],max_chars=12000,key=p+'_texto_'+area)
                    check=st.checkbox('Revisé el contenido y no contiene datos de terceros',key=p+'_rev_'+area)
                    if st.button('Incorporar transcripción revisada',disabled=not check or not texto.strip(),key=p+'_aplicar_'+area):
                        ev={'id':hashlib.sha256(texto.encode()).hexdigest(),'nombre':'Evaluación cargada de '+area,'texto':texto}
                        if not any(e['id']==ev['id'] for e in v['evaluaciones']):v['evaluaciones'].append(ev)
                        v['validada']=False;_incorporar(p,area,v)
                if upload and upload.name.rsplit('.',1)[-1].lower() in ('pdf','png','jpg','jpeg') and len(upload.getvalue())<=5*1024*1024:
                    from ui.archivo_expediente import boton
                    check=st.checkbox('El original contiene solo datos de este alumno',key=p+'_archivo_revisado_'+area)
                    tipo={'Aprendizaje':'Competencia curricular','Psicología':'Estudio psicológico','Comunicación':'Evaluación de comunicación y lenguaje','Trabajo Social':'Estudio social'}[area]
                    boton([doc['alumno']],tipo,upload.getvalue,upload.name,p+'_archivo_'+area,doc['id'],doc['ciclo'],'EPP iniciada',disabled=not check)
            for ev in v.get('evaluaciones',[]):
                with st.expander(ev.get('nombre','Evaluación')+' · '+ev.get('fecha','Sin fecha')):st.write(ev['texto'])
    with tab3:
        from services.epp_entrada import huella_instrumentos
        if st.button('Preparar resumen para el análisis',key=p+'_resumen_'+area):
            try:
                plan=s.contexto(doc);st.session_state[p+'_contexto']=plan
                st.session_state[p+'_resumen_'+area]=s.resumen(doc,area,v,plan)
                st.session_state[p+'_huella_'+area]=huella_instrumentos(doc,area,v)
                st.session_state.pop(p+'_consent_'+area,None)
            except Exception as exc:st.warning(str(exc) if isinstance(exc,ValueError) else 'No se pudo preparar el resumen; no se enviaron datos a IA.')
        if p+'_resumen_'+area in st.session_state:
            stale=st.session_state.get(p+'_huella_'+area)!=huella_instrumentos(doc,area,v)
            if stale:st.warning('Cambiaron las evaluaciones. Prepara de nuevo el resumen antes de analizar.')
            resumen=st.text_area('Resumen que se enviará a IA: elimina nombres, CURP, domicilios y contactos',value=st.session_state[p+'_resumen_'+area],max_chars=12000,key=p+'_resumen_texto_'+area)
            consent=st.checkbox('Revisé el resumen anonimizado y autorizo su análisis en Gemini',key=p+'_consent_'+area)
            if st.button('Proponer solo los apartados vacíos',disabled=not consent or stale,key=p+'_generar_'+area):
                try:
                    from ai.epp import generar
                    bar=st.progress(0,text='Preparando los hallazgos revisados…');bar.progress(20,text='Analizando las evaluaciones y redactando la propuesta…')
                    fingerprint=hashlib.sha256((area+'|'+resumen).encode()).hexdigest()
                    cache=st.session_state.get(p+'_propuesta_'+area,{})
                    r=cache.get('resultado') if cache.get('huella')==fingerprint else None
                    if r is None:
                        r=generar(resumen,area)
                        st.session_state[p+'_propuesta_'+area]={'huella':fingerprint,'resultado':r}
                    bar.progress(85,text='Comprobando fuentes y conservando tu redacción…')
                    for f,t in r['campos'].items():
                        if not str(v['campos'].get(f,'')).strip():v['campos'][f]=t
                    if area=='Conclusión':
                        for name in ('nee','bap'):
                            if not any(str(row.get('NEE' if name=='nee' else 'Tipo de barrera','')).strip() for row in v[name]):v[name]=r[name]
                    v['validada']=False;v['pendientes_ia']=r['faltantes']
                    if _incorporar(p,area,v):bar.progress(100,text='Propuesta guardada para revisión profesional.')
                    else:bar.empty()
                except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError)) else 'No se completó el análisis. Tu redacción permanece intacta; puedes continuar sin IA.')
        st.caption('La IA no aplica ni califica pruebas, no determina CI ni emite diagnósticos. No sustituye la revisión del equipo.')
        with st.expander('Recuperar un respaldo de mi área'):
            upload=st.file_uploader('Respaldo editable EPP (.json)',type=['json'],key=p+'_respaldo_'+area)
            check=st.checkbox('Comparé el respaldo con la hoja y quiero recuperar mi área; las versiones anteriores se conservarán',key=p+'_confirmar_recuperar_'+area)
            if upload and st.button('Recuperar mi texto en este informe',disabled=not check,key=p+'_recuperar_'+area):
                try:
                    if len(upload.getvalue())>300000:raise ValueError('El respaldo supera el tamaño permitido.')
                    restored=papel.recuperar(doc,json.loads(upload.getvalue()),area)
                    if _incorporar(p,area,restored):st.success('Texto recuperado en el mismo informe y guardado como nueva versión.')
                except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'No se pudo leer el respaldo. El informe permanece intacto.')
        if st.button('Confirmar revisión de mi área' if area!='Conclusión' else 'Validar conclusión acordada por el equipo',key=p+'_validar_'+area):
            try:
                if not guardar(p,True):raise ValueError('Primero confirma el guardado pendiente de tu área.')
                actual=next(d for d in s.listar() if d['id']==doc['id'])
                v=papel.contenido(actual,area);v['validada']=True
                saved=s.guardar(actual,area,v,actual['partes'].get(area,{}).get('revision',''))
                st.session_state[p+'_doc']['partes'][area]=saved;st.success('Revisión confirmada.')
            except Exception as exc:st.warning(str(exc) if isinstance(exc,(ValueError,RuntimeError,PermissionError)) else 'No se confirmó la revisión; tu texto se conserva.')


def panel(p):
    action=st.session_state.get(p+'_panel')
    if not action:return
    def cerrar():st.session_state.pop(p+'_panel',None)
    @st.dialog('EPP · Conexiones del informe',width='large',on_dismiss=cerrar)
    def mostrar():
        if st.button('Volver a mi informe',key=p+'_cerrar_panel'):
            st.session_state.pop(p+'_panel',None);st.rerun()
        if action=='pdf':
            from documents.epp import generar_pdf
            doc=st.session_state[p+'_doc'];pdf=generar_pdf(doc,s.alumno_autorizado(doc['alumno']))
            st.download_button('Descargar informe único en PDF',pdf,file_name='EPP.pdf',mime='application/pdf',key=p+'_pdf')
            if st.session_state.get(p+'_pending'):st.warning('Este PDF incluye tu captura pendiente; descargarlo no confirma el guardado central.')
            from ui.archivo_expediente import boton
            boton([doc['alumno']],'EPP',pdf,'EPP.pdf',p+'_archivar',doc['id'],doc['ciclo'],'EPP iniciada')
        else:herramientas(p)
    mostrar()


def proteger_salida(key):
    cuenta=s.actor()['cuenta'];legacy='epp_'+hashlib.sha256(cuenta.encode()).hexdigest()[:12]+'_edit_'
    keys=[k[:-8] for k,v in list(st.session_state.items()) if k.endswith('_pending') and v and
          (k.startswith('epp_viva_') and st.session_state.get(k[:-8]+'_cuenta')==cuenta or k.startswith(legacy))]
    if not keys:return True
    st.warning('Hay EPP pendientes de confirmación central. Reintenta o descarga cada respaldo antes de cerrar.')
    for p in keys:
        doc=st.session_state[p+'_doc'];s.autorizar(doc)
        backup=doc if p.startswith('epp_viva_') else {'informe':doc['id'],'area':st.session_state[p+'_area'],'contenido':st.session_state[p+'_value']}
        st.download_button('Respaldar EPP pendiente',json.dumps(backup,ensure_ascii=False,indent=2),file_name='EPP-pendiente.json',mime='application/json',key=key+p)
    if st.button('Reintentar EPP pendientes',key=key+'_epp_retry'):
        results=[]
        for p in keys:
            if p.startswith('epp_viva_'):results.append(guardar(p,True))
            else:
                from ui.epp import _save
                _save(p);results.append(not st.session_state.get(p+'_pending'))
        if all(results):return True
    return st.checkbox('Ya descargué los respaldos EPP; continuar al cierre',key=key+'_epp_respaldadas')


def page():
    a=s.actor();base='epp_'+hashlib.sha256(a['cuenta'].encode()).hexdigest()[:12]
    st.title('Evaluación psicopedagógica')
    st.caption('Un alumno y ciclo, un solo informe compartido. Apoyo lo inicia; cada especialista continúa sus apartados en la misma hoja.')
    from ui.epp_programacion import panel as programacion
    programacion(base)
    opened=st.session_state.get(base+'_viva_abierta')
    if opened:
        p=opened
        if st.session_state.pop(p+'_volver',False):
            st.session_state.pop(base+'_viva_abierta',None);st.rerun()
        doc=st.session_state[p+'_doc'];s.autorizar(doc)
        if doc['partes']['META']['estado']=='ELIMINADO':st.warning('Este informe fue retirado. Su historial y tu edición pendiente se conservan.');return
        st.caption('Escribe directamente en los apartados de tu función. Los aportes de las demás áreas se muestran para consulta y se actualizan sin mover tu selección.')
        hoja(p);panel(p);return
    try:frame=s.planes.padron_autorizado().fillna('');docs=s.listar(True)
    except Exception:st.warning('No se pudo consultar la matrícula y las EPP. No se modificó ningún registro.');return
    if frame.empty:st.info('No hay alumnos disponibles en tu asignación.');return
    schools={str(r['ID_Escuela']):str(r.get('Nombre_Escuela') or r['ID_Escuela']) for r in frame.to_dict('records')}
    school=st.selectbox('Escuela asignada',list(schools),format_func=schools.get,key=base+'_escuela_viva')
    registros=frame.loc[frame['ID_Escuela'].astype(str).eq(school)].to_dict('records')
    ciclo=st.selectbox('Ciclo escolar',sorted({'2026-2027'}|{d['ciclo'] for d in docs},reverse=True),key=base+'_ciclo_vivo')
    by_student={d['alumno']:d for d in docs if d['ciclo']==ciclo}
    if not s.puede_crear():registros=[r for r in registros if str(r['ID_Alumno']) in by_student and by_student[str(r['ID_Alumno'])]['partes']['META']['estado']!='ELIMINADO']
    search=st.text_input('Buscar alumno por nombre',key=base+'_busqueda_viva')
    from utils.text import normalizar_texto
    registros=[r for r in registros if normalizar_texto(search) in normalizar_texto(r.get('Nombre_Completo',''))]
    if not registros:st.info('No hay coincidencias o EPP iniciadas en esta escuela. Apoyo debe iniciar el informe; no es necesario dar de alta otra vez al alumno.');return
    def label(r):
        d=by_student.get(str(r['ID_Alumno']));state='Retirada · recuperable' if d and d['partes']['META']['estado']=='ELIMINADO' else 'Continuar EPP' if d else 'Por iniciar'
        return str(r['Nombre_Completo'])+' · '+str(r.get('Grado',''))+' '+str(r.get('Grupo',''))+' · '+state
    registros.sort(key=lambda r:normalizar_texto(r['Nombre_Completo']))
    labels={str(r['ID_Alumno']):label(r) for r in registros}
    aid=st.selectbox('Alumno',list(labels),format_func=labels.get,key=base+'_alumno_vivo_'+school)
    st.caption(str(len(registros))+' alumnos disponibles. Se incluyen todas las modalidades y grupos de la matrícula autorizada; no se filtran por atención grupal/individual.')
    if st.button('Abrir EPP del alumno',type='primary',key=base+'_abrir_viva'):
        try:
            doc=by_student.get(aid)
            if not doc:doc=s.crear(aid,ciclo)
            if doc['partes']['META']['estado']=='ELIMINADO':raise ValueError('Esta EPP está retirada. Recupera el informe anterior para continuar sin duplicarlo.')
            st.session_state[base+'_viva_abierta']=abrir(doc);st.rerun()
        except (ValueError,PermissionError,RuntimeError) as exc:st.warning(str(exc))
        except Exception:st.warning('No se confirmó la apertura. Reintenta: se reutilizará la misma identidad y no se generará otra EPP.')
    doc=by_student.get(aid)
    if doc and doc['partes']['META']['estado']=='ELIMINADO' and s.puede_crear() and doc['partes']['META']['cuenta']==a['cuenta']:
        if st.button('Recuperar el mismo informe retirado',key=base+'_recuperar_viva'):
            s.retirar(doc,True);st.rerun()
