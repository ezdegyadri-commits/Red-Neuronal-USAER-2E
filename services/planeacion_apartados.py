"""Propuestas locales revisables sobre antecedentes propios, sin motor ni escritura."""
from copy import deepcopy
import re
from services import planeacion as s
from services.planeacion_generacion import fuentes_pertinentes
from services.curriculo import contexto_ia
from services.planeacion_modelo import FORMATOS
from utils.text import normalizar_texto


def proponer(doc):
    """Completa vacíos, no reemplaza celdas, confirma NEE ni predice resultados.

    Solo se ejecuta al crear una hoja nueva o por petición explícita. No al abrir
    documentos: así el texto que se eliminó deliberadamente no reaparece.
    """
    s.autorizar(doc,True)
    if doc['formato'] not in ('XXIII','XXV'):return deepcopy(doc)
    result=deepcopy(doc);area=doc['datos']['Función']
    tabla='barreras' if doc['formato']=='XXV' else 'aprendizajes'
    headers=FORMATOS[doc['formato']]['tablas'][tabla]
    fuentes=fuentes_pertinentes(doc);refs=contexto_ia(doc).get('referentes_por_grado',[])
    alumnos=doc['datos']['Alumnos'];rows=result['tablas'][tabla]
    for a in alumnos:
        aid=a['ID_Alumno']
        # Los materiales generales y antecedentes de otros alumnos no son NEE.
        propias=[f for f in fuentes if set(str(f.get('alumno','')).split(','))=={aid}]
        grado=re.match(r'^\s*([1-6])(?:\D|$)',str(a.get('Grado','')))
        relevantes=[r for r in refs if grado and str(r['grado'])==grado[1]]
        datos=' '.join(f['texto'][:1200] for f in propias)+' '+' '.join(r['contenido'] for r in relevantes)
        if not datos.strip():continue
        texto=normalizar_texto(datos)
        if area=='Psicología':
            objetivo='Reconocer y comunicar una emoción en una situación escolar, explorando una alternativa de regulación o convivencia.'
            descriptor='En una situación escolar propuesta, identifica una emoción y elige una alternativa de respuesta; registrar el apoyo necesario y revisar su pertinencia.'
        elif area=='Comunicación':
            objetivo='Expresar una elección, una necesidad o una idea en un intercambio funcional mediante el canal de comunicación pertinente.'
            descriptor='En un intercambio funcional, comunica una elección, petición o idea mediante el canal accesible; registrar la respuesta y los apoyos utilizados.'
        elif any(t in texto for t in ('LECTURA','LECTO','LEER')):
            objetivo='Comprender información de un texto pertinente y comunicar una idea mediante una respuesta accesible.'
            descriptor='Después de leer o escuchar un texto, identifica información y comunica una idea con palabras, imágenes o el canal pertinente; conservar una muestra y registrar los apoyos.'
        elif 'ESCRIT' in texto:
            objetivo='Construir y compartir un mensaje significativo mediante escritura o una forma de expresión accesible.'
            descriptor='Produce y comparte un mensaje relacionado con la actividad; conservar la muestra y registrar qué apoyos facilitaron su elaboración.'
        elif any(t in texto for t in ('NUMER','CONTEO','CANTIDAD','MATEMAT')):
            objetivo='Representar y resolver una situación de cantidad vinculada al contenido pertinente con recursos accesibles.'
            descriptor='Representa una cantidad o explica una solución en una situación propuesta; registrar el procedimiento y los apoyos, sin anticipar el nivel de logro.'
        else:
            objetivo='Participar en una actividad vinculada al antecedente documentado o al contenido seleccionado, mediante apoyos pertinentes.'
            descriptor='Realiza una acción relacionada con el objetivo y comunica su respuesta por un medio accesible; recoger una evidencia y registrar los apoyos para ajustar la siguiente sesión.'
        nombre=a['Nombre del alumno']
        antecedente='\n\n'.join('['+str(f.get('referencia',''))+'] '+str(f['texto'])[:900] for f in propias[:3])
        necesidad=(nombre+' · Antecedentes para revisar la necesidad educativa (no confirma NEE):\n'+antecedente) if propias else ''
        if relevantes:
            objetivo='Propuesta de objetivo · '+nombre+': trabajar '+ '; '.join(r['contenido'] for r in relevantes[:3])+'.\n'+objetivo
        else:objetivo='Propuesta de objetivo · '+nombre+': '+objetivo+'\nVinculación con PDA pendiente de selección; no sustituye un referente oficial.'
        valores=({'Barreras para el Aprendizaje y la Participación':necesidad.replace('necesidad educativa (no confirma NEE)','barrera del entorno (no confirma BAP)'),
                   'Apoyos y/o ajustes razonables':'Propuesta para revisión: ofrecer información accesible, revisar los recursos reales con las personas implicadas y dar seguimiento a los acuerdos que efectivamente se alcancen.'} if tabla=='barreras' else
                  {'Necesidades educativas específicas':necesidad,'Aprendizaje y/u objetivo':objetivo,'Descriptor de logro':'Propuesta de logro · '+nombre+': '+descriptor})
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
        for campo,value in valores.items():
            if value and not str(row.get(campo,'') or '').strip():row[campo]=value
        row['_origenes_apartados']=[{'tipo':f.get('tipo',''),'registro':f.get('registro',''),'alumno':f.get('alumno',''),'referencia':f.get('referencia','')} for f in propias[:3]]
        row['_referentes_apartados']=[r['id'] for r in relevantes]
    if result!=doc:
        result['metadatos']['propuestas_apartados']={'motor':'sin IA','requiere_revision_docente':True,
            'aviso':'Son propuestas de objetivo y logro para revisión, no NEE confirmadas ni resultados alcanzados. Los PDA oficiales se conservan separados; edita o elimina cualquier propuesta.'}
    return result
