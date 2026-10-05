"""Referentes oficiales trazables. El catálogo procede de tablas SEP, sin IA."""
from copy import deepcopy
import gzip
import json
from pathlib import Path
import re
import streamlit as st

CAMPOS={
 'Lenguajes':'Comunicar, interpretar y expresar significados mediante lenguas, textos, oralidad y lenguajes artísticos, en situaciones reales.',
 'Saberes y Pensamiento Científico':'Indagar, formular preguntas, explicar fenómenos y resolver situaciones con saberes científicos, matemáticos y comunitarios.',
 'Ética, Naturaleza y Sociedades':'Comprender relaciones sociales y ambientales, derechos, diversidad y responsabilidades para la convivencia y el cuidado.',
 'De lo Humano y lo Comunitario':'Favorecer identidad, bienestar, vínculos, participación y capacidades personales y colectivas en la comunidad.'}
EJES={
 'Inclusión':'Identificar barreras de acceso, participación y aprendizaje; organizar apoyos sin segregar ni reducir expectativas por una condición.',
 'Pensamiento crítico':'Contrastar ideas, preguntar por las razones, analizar situaciones y tomar decisiones fundamentadas.',
 'Interculturalidad crítica':'Reconocer lenguas, culturas y saberes locales, con diálogo y atención a desigualdades y discriminación.',
 'Igualdad de género':'Promover oportunidades y participación equitativas, sin estereotipos de género.',
 'Vida saludable':'Construir prácticas de cuidado, bienestar y relaciones saludables considerando el contexto.',
 'Apropiación de las culturas a través de la lectura y la escritura':'Participar en prácticas significativas de lectura y escritura, con apoyos de acceso pertinentes.',
 'Artes y experiencias estéticas':'Explorar, crear y apreciar expresiones artísticas y experiencias sensibles diversas.'}
FUENTES_BASE=[
 {'id':'SEP-PLAN2022','titulo':'Plan de Estudio 2022 para preescolar, primaria y secundaria','edicion':'Edición proporcionada 2025','organismo':'SEP','url':'https://educacionbasica.sep.gob.mx/materiales-de-apoyo-a-la-apropiacion-del-plan-y-programas-de-estudio-2022/','nota':'Campos, ejes, integración curricular y evaluación formativa. No equivale al catálogo de PDA.'},
 {'id':'SEGEY-USAER','titulo':'Manual de Operatividad del Servicio de Apoyo de Educación Especial USAER','edicion':'2021','organismo':'SEGEY Yucatán','url':'https://www.educacion.yucatan.gob.mx/multimedia/publicaciones/220121_Manual_USAER.pdf','nota':'Anexos XXI-XXVI: objetivos derivados de NEE/IEPP, barreras, apoyos, ajustes, contextos y seguimiento.'}]

@st.cache_data(show_spinner=False)
def catalogo():
    root=Path(__file__).resolve().parents[1]/'data'
    compressed=root/'curriculo_sep.json.gz'
    if compressed.exists():
        with gzip.open(compressed,'rt',encoding='utf-8') as f:return json.load(f)
    return json.loads((root/'curriculo_sep.json').read_text(encoding='utf-8'))

def grados(doc):
    values=set()
    for alumno in doc['datos']['Alumnos']:
        m=re.match(r'^\s*([1-6])(?:\D|$)',str(alumno.get('Grado','')))
        if m:values.add(int(m[1]))
    return values

def opciones(doc,campo):
    if campo not in CAMPOS:return []
    return [r for r in catalogo()['registros'] if r['grado'] in grados(doc) and r['campo']==campo]

def vincular(doc,campo,ejes,ids,contexto_local=''):
    if campo not in CAMPOS or not set(ejes).issubset(EJES):raise ValueError('Elige campos y ejes del catálogo oficial.')
    if len(ids)>6:raise ValueError('Elige hasta seis referentes prioritarios.')
    disponibles={r['id']:r for r in opciones(doc,campo)}
    if not set(ids).issubset(disponibles):raise ValueError('El referente no corresponde al campo y grado seleccionados.')
    selected=[deepcopy(disponibles[i]) for i in dict.fromkeys(ids)]
    result=deepcopy(doc)
    result['metadatos']['curriculo']={'campo':campo,'ejes':list(ejes),'registros':selected,'contexto_local':str(contexto_local)[:4000]}
    return result

def contexto_ia(doc):
    seleccion=doc['metadatos'].get('curriculo',{})
    campo=seleccion.get('campo','')
    if campo not in CAMPOS:return {'fuentes':FUENTES_BASE,'campos':CAMPOS,'ejes':EJES,'aviso':'Sin contenido o PDA seleccionado: no atribuir un PDA específico a una actividad.'}
    verified=vincular(doc,campo,seleccion.get('ejes',[]),[r['id'] for r in seleccion.get('registros',[])])
    registros=verified['metadatos']['curriculo']['registros']
    sources=FUENTES_BASE+[s for s in catalogo()['fuentes'] if s['id'] in {r['fuente'] for r in registros}]
    return {'fuentes':sources,'campo':{campo:CAMPOS[campo]},'ejes':{e:EJES[e] for e in seleccion.get('ejes',[])},'referentes_por_grado':registros,
            'guia_local':'Priorizar NEE documentadas y BAP; objetivo y descriptor: sujeto + verbo observable en presente + habilidad. Dosificar por contextos y registrar tiempos, recursos y evaluación. Trabajo Social aborda barreras y apoyos en aula, escuela, familia y comunidad. No convertir una condición en una NEE ni una propuesta en un logro.',
            'aviso':'La adaptación pedagógica no modifica el texto del PDA. El programa analítico escolar requiere confirmación del colectivo; no se presume cargado.'}
