"""Archivo privado versionado: metadatos separados de binarios y lectura acotada.

Clasificación institucional: manual USAER, anexos VI (pp.120–121) y IX
(pp.125–126). Nunca envía documentos a motores de IA ni crea enlaces públicos.
"""
import base64
import hashlib
import json
import re
from datetime import datetime,timezone
from io import BytesIO
import streamlit as st
from data import repository as repo
from data.google import ensure_sheet,worksheet,retry_google,clear_cache
from services.padron_movimientos import visibles
from services.planeacion_estabilidad import candado
from utils.escolar import grado_canonico,grupo_canonico
from utils.text import normalizar_texto

HOJA='Documentos_Expediente';PARTES='Archivos_Expediente'
HEADERS=['ID_Documento','Ambito','ID_Alumnos_JSON','ID_Escuela','Grado','Grupo','Ciclo','Tipo','Nombre','Mime','SHA256','Rango','Partes','Fecha','Cuenta','Fuente','Estado']
PH=['ID_Documento','Indice','Total','Contenido']
INDIVIDUAL=('Ficha de identidad','Consentimiento de atención','Acta de nacimiento','CURP','Solicitud de estudio o apoyo','Canalización','Informe a otra institución','Baja o alta','Entrevista','EPP','Plan de intervención','Estilo de aprendizaje y motivación','Competencia curricular','Informe pedagógico inicial','Informe pedagógico final','Estudio psicológico','Informe psicológico inicial','Informe psicológico final','Evaluación de comunicación y lenguaje','Informe de comunicación inicial','Informe de comunicación final','Estudio social','BAP familiar','Visita institucional','Informe médico','Reporte de atención médica')
GRUPAL=('Lista del grupo','BAP áulico','Evaluación diagnóstica','Planeación grupal','Planeación grupal AS','Actividades exploratorias AS','Productos y evidencias AS')
CONTEXTUAL=('Derivación','Agote de recursos','Sugerencias','Eventos significativos','Planeación del servicio','Otro documento educativo')
TIPOS=GRUPAL+INDIVIDUAL+CONTEXTUAL


def sugerir_tipo(nombre):
    """Solo una ayuda de selección por título; nunca identifica al destinatario."""
    titulo=normalizar_texto(str(nombre).replace('_',' '))
    reglas=[(('CURP',),'CURP'),(('CONSENTIMIENTO',),'Consentimiento de atención'),
        (('ACTA DE NACIMIENTO',),'Acta de nacimiento'),(('EPP','IEPP','PSICOPEDAGOG'),'EPP'),
        (('ESTUDIO SOCIAL',),'Estudio social'),(('INFORME MEDICO',),'Informe médico'),
        (('DERIVACION',),'Derivación'),(('SUGERENCIA',),'Sugerencias'),
        (('EVENTO',),'Eventos significativos'),(('PLANEACION GRUPAL',),'Planeación grupal'),
        (('PLAN DE INTERVENCION',),'Plan de intervención'),(('LISTA','LISTADO'),'Lista del grupo')]
    return next((tipo for tokens,tipo in reglas if any(token in titulo for token in tokens)),None)


def _rows():
    try:return repo.read(HOJA).fillna('').to_dict('records')
    except Exception as exc:
        if type(exc).__name__=='WorksheetNotFound':return []
        raise


def _actor():
    if not st.session_state.get('autenticado') or not st.session_state.get('usuario'):raise PermissionError('Inicia sesión.')
    return str(st.session_state['usuario'])


def contexto(ids,tipo,ciclo,etapa=''):
    _actor()
    if tipo not in TIPOS:raise ValueError('Elige un tipo documental del manual.')
    ids=list(dict.fromkeys(str(i) for i in ids))
    if not ids:raise ValueError('Selecciona los destinatarios; no se deducen por el nombre del archivo.')
    frame=visibles().fillna('');rows={str(r['ID_Alumno']):r for r in frame.to_dict('records')}
    if not set(ids).issubset(rows):raise PermissionError('Documento fuera de tu asignación actual.')
    alumnos=[rows[i] for i in ids]
    escuelas={str(r.get('ID_Escuela','')) for r in alumnos}
    if len(escuelas)!=1:raise ValueError('Un archivo no puede mezclar escuelas.')
    ciclo=re.sub(r'\s+','',str(ciclo)).replace('–','-').replace('—','-')
    if not re.fullmatch(r'20\d\d-20\d\d',ciclo) or int(ciclo[-4:])!=int(ciclo[:4])+1:raise ValueError('Confirma el ciclo escolar.')
    individuales=all(normalizar_texto(r.get('Tipo_Atencion',''))=='INDIVIDUAL' for r in alumnos)
    ambito='individual' if tipo in INDIVIDUAL or tipo not in GRUPAL and (individuales or etapa=='EPP iniciada') else 'grupal'
    grupos={(grado_canonico(r.get('Grado','')),grupo_canonico(r.get('Grupo',''))) for r in alumnos}
    if ambito=='grupal' and len(grupos)!=1:raise ValueError('Selecciona un único grado y grupo para el expediente grupal.')
    grado,grupo=next(iter(grupos)) if len(grupos)==1 else ('','')
    return {'Ambito':ambito,'ID_Alumnos_JSON':json.dumps(ids),'ID_Escuela':next(iter(escuelas)),
        'Grado':grado,'Grupo':grupo,'Ciclo':str(ciclo),'Tipo':tipo}


def _autorizado(row,frame):
    ids=json.loads(row['ID_Alumnos_JSON'])
    porid={str(r['ID_Alumno']):r for r in frame.fillna('').to_dict('records')}
    if not ids:return False
    # Individual sigue al ID al trasladarse. Un colectivo nunca sale de la
    # escuela de origen ni se revela a quien solo recibe uno de sus alumnos.
    if row['Ambito']=='individual':return set(ids).issubset(porid)
    if row['Ambito']!='grupal':return False
    # Un traslado no hace desaparecer el archivo colectivo del grupo de origen.
    if any(i in porid and str(porid[i].get('ID_Escuela',''))==str(row['ID_Escuela']) for i in ids):return True
    from services.asignaciones import escuelas_asignadas
    from config.settings import ESCUELAS_USAER
    asignadas={str(ESCUELAS_USAER[e]) for e in escuelas_asignadas(st.session_state.get('nombre',''),st.session_state.get('rol','')) if e in ESCUELAS_USAER}
    return str(row['ID_Escuela']) in asignadas and (row.get('Cuenta')==_actor() or 'APOYO' not in normalizar_texto(st.session_state.get('rol','')))


def listar():
    _actor();frame=visibles();salida={}
    for row in _rows():
        if row.get('Estado')=='VIGENTE' and _autorizado(row,frame):salida[row['ID_Documento']]=row
    from services.expediente_automatico import orden_cronologico,seccion
    return orden_cronologico([{**r,'Seccion':seccion(r['Tipo'])} for r in salida.values()])


def validar_binario(data):
    if not data or len(data)>5*1024*1024:raise ValueError('El archivo debe pesar como máximo 5 MB.')
    if data.startswith(b'%PDF-'):
        import pymupdf
        with pymupdf.open(stream=data,filetype='pdf') as doc:
            if doc.is_encrypted or not len(doc):raise ValueError('El PDF debe ser legible y no estar cifrado.')
        return 'application/pdf'
    from PIL import Image
    with Image.open(BytesIO(data)) as image:
        if image.format not in ('JPEG','PNG') or image.width*image.height>25000000:raise ValueError('Usa PDF, JPG o PNG, hasta 25 megapíxeles.')
        mime=Image.MIME[image.format];image.verify();return mime


def guardar(ids,tipo,ciclo,nombre,data,fuente='',etapa=''):
    cuenta=_actor();destino=contexto(ids,tipo,ciclo,etapa);mime=validar_binario(data)
    digest=hashlib.sha256(data).hexdigest()
    key=hashlib.sha256((json.dumps(destino,sort_keys=True)+digest).encode()).hexdigest()
    with candado('archivo:'+key):
        if any(r['ID_Documento']==key for r in listar()):return key
        for name,headers in ((HOJA,HEADERS),(PARTES,PH)):
            ws=ensure_sheet(name,headers)
            if retry_google(lambda:ws.row_values(1))!=headers:raise ValueError('El archivo existente tiene otro esquema. Dirección debe revisarlo; no se ha sobrescrito.')
        encoded=base64.b64encode(data).decode('ascii');chunks=[encoded[i:i+30000] for i in range(0,len(encoded),30000)]
        respuesta=retry_google(lambda:worksheet(PARTES).append_rows([[key,str(i),str(len(chunks)),chunk] for i,chunk in enumerate(chunks)],value_input_option='RAW'))
        rango=respuesta.get('updates',{}).get('updatedRange','').split('!')[-1]
        if not re.fullmatch(r'A\d+:D\d+',rango):raise RuntimeError('No se confirmó la ubicación del archivo. No se registró como completo.')
        row={**destino,'ID_Documento':key,'Nombre':str(nombre).replace('\\','/').split('/')[-1][:180],
            'Mime':mime,'SHA256':digest,'Rango':rango,'Partes':str(len(chunks)),
            'Fecha':datetime.now(timezone.utc).isoformat(),'Cuenta':cuenta,'Fuente':str(fuente)[:200],'Estado':'VIGENTE'}
        # Verifica las partes antes de publicar la ficha; las escrituras truncas
        # no aparecen como documentos recuperables y se conservan para revisión.
        _contenido(row)
        retry_google(lambda:worksheet(HOJA).append_rows([[row.get(h,'') for h in HEADERS]],value_input_option='RAW'))
        clear_cache(HOJA)
        if not any(r['ID_Documento']==key for r in listar()):raise RuntimeError('No se confirmó el índice del documento; reintenta sin crear una copia.')
        return key


def _contenido(row):
    rango=str(row['Rango'])
    if not re.fullmatch(r'A\d+:D\d+',rango):raise ValueError('Rango de archivo no válido.')
    n=int(row['Partes'])
    if not 1<=n<=234:raise ValueError('Archivo fuera del límite permitido.')
    partes=retry_google(lambda:worksheet(PARTES).get(rango))
    if len(partes)!=n or any(len(r)!=4 or r[:3]!=[row['ID_Documento'],str(i),str(n)] for i,r in enumerate(partes)):
        raise ValueError('El archivo está incompleto; no se puede descargar.')
    data=base64.b64decode(''.join(r[3] for r in partes),validate=True)
    if hashlib.sha256(data).hexdigest()!=row['SHA256']:raise ValueError('La integridad del archivo no coincide.')
    return data


def descargar(key):
    row=next((r for r in listar() if r['ID_Documento']==key),None)
    if not row:raise PermissionError('Archivo fuera de tu ámbito actual.')
    return row,_contenido(row)
