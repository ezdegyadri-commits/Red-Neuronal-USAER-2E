"""Propuestas locales revisables sobre antecedentes propios, sin motor ni escritura."""
from copy import deepcopy
import re
from services import planeacion as s
from services.planeacion_generacion import fuentes_pertinentes
from services.curriculo import contexto_ia
from services.planeacion_modelo import FORMATOS
from utils.text import normalizar_texto
from services.planeacion_nee import necesidad,es_bapse,nee_padron


def proponer(doc):
    """Completa vacíos, no reemplaza celdas, confirma NEE ni predice resultados.

    Solo se ejecuta al crear una hoja nueva o por petición explícita. No al abrir
    documentos: así el texto que se eliminó deliberadamente no reaparece.
    """
    s.autorizar(doc,True)
    if doc['formato'] not in ('XXIII','XXV'):return deepcopy(doc)
    if doc['formato']=='XXV':
        from services.planeacion_social import proponer as proponer_social
        return proponer_social(doc)
    result=deepcopy(doc);area=doc['datos']['Función']
    tabla='barreras' if doc['formato']=='XXV' else 'aprendizajes'
    headers=FORMATOS[doc['formato']]['tablas'][tabla]
    fuentes=fuentes_pertinentes(doc);refs=contexto_ia(doc).get('referentes_por_grado',[])
    alumnos=doc['datos']['Alumnos'];rows=result['tablas'][tabla]
    # Reutiliza el padrón autorizado (cacheado); admite sus columnas NEE
    # existentes sin imponer un encabezado nuevo ni modificar la base.
    padron=s.padron_autorizado()
    registrados={str(r['ID_Alumno']):r for r in padron.to_dict('records')} if 'ID_Alumno' in padron else {}
    for a in alumnos:
        aid=a['ID_Alumno']
        # Los materiales generales y antecedentes de otros alumnos no son NEE.
        vinculadas=[f for f in fuentes if set(str(f.get('alumno','')).split(','))=={aid}]
        propias=[f for f in vinculadas if not es_bapse(f)]
        grado=re.match(r'^\s*([1-6])(?:\D|$)',str(a.get('Grado','')))
        relevantes=[r for r in refs if grado and str(r['grado'])==grado[1]]
        datos=' '.join(f['texto'][:1200] for f in propias)+' '+' '.join(r['contenido'] for r in relevantes)
        registro=registrados.get(aid,a)
        nee,origen_nee=necesidad(registro,propias,relevantes,area)
        if not datos.strip() and tabla=='barreras':continue
        datos+=' '+nee
        texto=normalizar_texto(datos)
        if area=='Psicología':
            objetivo='Reconocer y comunicar una emoción en una situación escolar, explorando una alternativa de regulación o convivencia.'
            descriptor='El alumno identifica una emoción y elige una alternativa de respuesta en una situación escolar.'
        elif area=='Comunicación':
            objetivo='Expresar una elección, una necesidad o una idea en un intercambio funcional mediante el canal de comunicación pertinente.'
            descriptor='El alumno comunica una elección, petición o idea mediante un canal accesible.'
        elif any(t in texto for t in ('LECTURA','LECTO','LEER')):
            objetivo='Comprender información de un texto pertinente y comunicar una idea mediante una respuesta accesible.'
            descriptor='El alumno identifica información de un texto leído o escuchado y comunica una idea por un medio accesible.'
        elif 'ESCRIT' in texto:
            objetivo='Construir y compartir un mensaje significativo mediante escritura o una forma de expresión accesible.'
            descriptor='El alumno produce y comparte un mensaje relacionado con la actividad.'
        elif any(t in texto for t in ('NUMER','CONTEO','CANTIDAD','MATEMAT')):
            objetivo='Representar y resolver una situación de cantidad vinculada al contenido pertinente con recursos accesibles.'
            descriptor='El alumno representa una cantidad y explica su solución con los apoyos previstos.'
        else:
            objetivo='Participar en una actividad vinculada al antecedente documentado o al contenido seleccionado, mediante apoyos pertinentes.'
            descriptor='El alumno realiza la acción propuesta y comunica su respuesta por un medio accesible.'
        nombre=a['Nombre del alumno']
        antecedente='\n\n'.join('['+str(f.get('referencia',''))+'] '+str(f['texto'])[:900] for f in propias[:3])
        necesidad_texto=nee
        verbos={'Reconocer':'reconoce','Expresar':'expresa','Comprender':'comprende','Construir':'construye','Representar':'representa','Participar':'participa'}
        verbo=objetivo.split(' ',1)[0]
        objetivo=verbos.get(verbo,verbo.lower())+' '+objetivo.split(' ',1)[1]
        if relevantes:objetivo+='\nContenido de referencia: '+ '; '.join(r['contenido'] for r in relevantes[:3])+'.'
        valores=({'Barreras para el Aprendizaje y la Participación':nombre+' · Propuesta para revisar las barreras documentadas del entorno; no equivale a una NEE.',
                   'Apoyos y/o ajustes razonables':'Propuesta para revisión: ofrecer información accesible, revisar los recursos reales con las personas implicadas y dar seguimiento a los acuerdos que efectivamente se alcancen.'} if tabla=='barreras' else
                  {'Necesidades educativas específicas':necesidad_texto,'Aprendizaje y/u objetivo':nombre+': '+objetivo,'Descriptor de logro':nombre+': '+descriptor})
        row=next((r for r in rows if r.get('_alumnos_apartados')==[aid] and not r.get('_aporte') and not r.get('_sesion_equipo')),None)
        if row is None and len(alumnos)==1:
            row=next((r for r in rows if not r.get('_aporte') and not r.get('_sesion_equipo') and not r.get('_alumnos_apartados') and any(not str(r.get(h,'') or '').strip() for h in headers)),None)
        if row is None:
            row=next((r for r in rows if not any(str(r.get(h,'') or '').strip() for h in headers) and not r.get('_aporte') and not r.get('_sesion_equipo') and not r.get('_alumnos_apartados')),None)
            # Una tabla ya redactada no recibe filas paralelas que aparenten
            # reemplazar sus decisiones. Solo completar blancos vinculados.
            if row is None and any(r for r in rows if not r.get('_alumnos_apartados')):continue
            if row is None:
                if len(rows)>=100:break
                row=dict.fromkeys(headers,'');rows.append(row)
            row['_alumnos_apartados']=[aid]
        else:row.setdefault('_alumnos_apartados',[aid])
        # Reparar solo la copia exacta que produjo la versión anterior; una
        # redacción modificada por la docente nunca se reemplaza a ciegas.
        legacy=nombre+' · Antecedentes para revisar la necesidad educativa (no confirma NEE):\n'+'\n\n'.join('['+str(f.get('referencia',''))+'] '+str(f['texto'])[:900] for f in vinculadas[:3])
        if tabla=='aprendizajes' and row.get('Necesidades educativas específicas')==legacy:
            row['Necesidades educativas específicas']=nee
        for campo,value in valores.items():
            if value and not str(row.get(campo,'') or '').strip():row[campo]=value
        row['_origenes_apartados']=[{'tipo':f.get('tipo',''),'registro':f.get('registro',''),'alumno':f.get('alumno',''),'referencia':f.get('referencia','')} for f in propias[:3]]
        row['_referentes_apartados']=[r['id'] for r in relevantes]
        if tabla=='aprendizajes' and row.get('Necesidades educativas específicas')==nee:row['_nee_origen']=origen_nee
    if result!=doc:
        result['metadatos']['propuestas_apartados']={'motor':'sin IA','requiere_revision_docente':True,
            'aviso':'Se prioriza la NEE registrada por la maestra o en EPP revisada; si falta, se propone una hipótesis educativa para aceptar, editar o eliminar. BAPSE no se copia como NEE. Las propuestas no determinan diagnósticos ni logros alcanzados.'}
    return result
