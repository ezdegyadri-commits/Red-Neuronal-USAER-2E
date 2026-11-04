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
            if any(t in texto for t in ('PRESILAB','SILAB','INICIAL','FONOL')):
                objetivo='Desarrollar conciencia fonológica y correspondencia grafofonética mediante tarjetas con imágenes y modelado docente.'
                descriptor='El alumno identifica el sonido inicial y asocia la grafía correspondiente utilizando tarjetas con imágenes.'
            else:
                objetivo='Localizar información explícita en textos breves y expresar oralmente o con apoyo visual la idea principal.'
                descriptor='El alumno lee frases cortas o escucha la lectura mediada y señala los elementos clave del texto.'
        elif 'ESCRIT' in texto:
            if any(t in texto for t in ('PRESILAB','SILAB','INICIAL','NOMBRE')):
                objetivo='Escribir su nombre y palabras significativas de su entorno apoyándose en sílabas móviles y modelado.'
                descriptor='El alumno forma y escribe palabras cortas de su entorno utilizando sílabas móviles.'
            else:
                objetivo='Producir enunciados significativos apoyándose en bancos de palabras y referentes gráficos.'
                descriptor='El alumno redacta oraciones sencillas con propósito comunicativo empleando apoyos visuales.'
        elif any(t in texto for t in ('NUMER','CONTEO','CANTIDAD','MATEMAT')):
            if any(t in texto for t in ('BASICO','INICIAL','1 A 10','1 A 20','1 A 50','CONTEO')):
                objetivo='Consolidar el conteo con correspondencia uno a uno y la asociación cantidad-numeral con material concreto.'
                descriptor='El alumno cuenta colecciones de objetos hasta 50 y asocia la cantidad con el numeral mediante fichas de conteo.'
            else:
                objetivo='Resolver situaciones problemáticas de suma y resta contextualizadas utilizando material manipulativo y esquemas.'
                descriptor='El alumno resuelve situaciones problemáticas cotidianas empleando bloques base diez o fichas y explica su resultado.'
        else:
            objetivo='Desarrollar habilidades de seguimiento de instrucciones y resolución de tareas paso a paso mediante modelado y material manipulativo.'
            descriptor='El alumno sigue la secuencia guiada por el docente manipulando el material concreto adaptado y comunica su respuesta.'
        nombre=a['Nombre del alumno']
        antecedente='\n\n'.join('['+str(f.get('referencia',''))+'] '+str(f['texto'])[:900] for f in propias[:3])
        necesidad_texto=nee
        verbos={'Reconocer':'reconoce','Expresar':'expresa','Comprender':'comprende','Construir':'construye','Representar':'representa','Participar':'participa','Desarrollar':'desarrolla','Localizar':'localiza','Escribir':'escribe','Producir':'produce','Consolidar':'consolida','Resolver':'resuelve'}
        verbo=objetivo.split(' ',1)[0]
        objetivo_adaptado=verbos.get(verbo,verbo.lower())+' '+objetivo.split(' ',1)[1]
        if relevantes:
            pda_texto = f"{relevantes[0].get('contenido', '')} — {relevantes[0].get('pda', '')}"
        else:
            pda_texto = objetivo_adaptado
        valores=({'Barreras para el Aprendizaje y la Participación':nombre+' · Propuesta para revisar las barreras documentadas del entorno; no equivale a una NEE.',
                   'Apoyos y/u ajustes razonables':'Propuesta para revisión: ofrecer información accesible, revisar los recursos reales con las personas implicadas y dar seguimiento a los acuerdos que efectivamente se alcancen.'} if tabla=='barreras' else
                  {'Necesidades educativas específicas':necesidad_texto,'Aprendizaje y/u objetivo':pda_texto,'Descriptor de logro':descriptor})
        
        # Consolidación: si ya existe una fila con la misma NEE, no crear filas parásitas duplicadas
        if tabla == 'aprendizajes' and any(r.get('Necesidades educativas específicas') == necesidad_texto for r in rows):
            continue

        row=next((r for r in rows if r.get('_alumnos_apartados')==[aid] and not r.get('_aporte') and not r.get('_sesion_equipo')),None)
        if row is None and len(alumnos)==1:
            row=next((r for r in rows if not r.get('_aporte') and not r.get('_sesion_equipo') and not r.get('_alumnos_apartados') and any(not str(r.get(h,'') or '').strip() for h in headers)),None)
        if row is None:
            row=next((r for r in rows if not any(str(r.get(h,'') or '').strip() for h in headers) and not r.get('_aporte') and not r.get('_sesion_equipo') and not r.get('_alumnos_apartados')),None)
            if row is None and any(r for r in rows if not r.get('_alumnos_apartados')):continue
            if row is None:
                if len(rows)>=100:break
                row=dict.fromkeys(headers,'');rows.append(row)
            row['_alumnos_apartados']=[aid]
        else:row.setdefault('_alumnos_apartados',[aid])
        legacy=nombre+' · Antecedentes para revisar la necesidad educativa (no confirma NEE):\n'+'\n\n'.join('['+str(f.get('referencia',''))+'] '+str(f['texto'])[:900] for f in vinculadas[:3])
        if tabla=='aprendizajes' and row.get('Necesidades educativas específicas')==legacy:
            row['Necesidades educativas específicas']=nee
        for campo,value in valores.items():
            if value and not str(row.get(campo,'') or '').strip():row[campo]=value
        row['_origenes_apartados']=[{'tipo':f.get('tipo',''),'registro':f.get('registro',''),'alumno':f.get('alumno',''),'referencia':f.get('referencia','')} for f in propias[:3]]
        row['_referentes_apartados']=[r['id'] for r in relevantes]
        if tabla=='aprendizajes' and row.get('Necesidades educativas específicas')==nee:
            row['_nee_origen']=origen_nee
    if result!=doc:
        result['metadatos']['propuestas_apartados']={'motor':'sin IA','requiere_revision_docente':True,
            'aviso':'Se prioriza la NEE registrada por la maestra o en EPP revisada; si falta, se propone una hipótesis educativa para aceptar, editar o eliminar. BAPSE no se copia como NEE. Las propuestas no determinan diagnósticos ni logros alcanzados.'}
    return result
