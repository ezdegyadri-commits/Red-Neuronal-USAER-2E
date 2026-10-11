"""Adaptador del formato familiar sobre el documento canónico existente."""
from copy import deepcopy
from services.planeacion_modelo import FORMATOS

TITULOS={'aprendizajes':'Necesidades educativas específicas, aprendizaje y descriptor de logro',
 'dosificacion':'Organización de las actividades de aprendizaje','barreras':'Barreras para el aprendizaje y la participación',
 'necesidades':'Necesidades educativas específicas y apoyos','curriculo':'Apoyos y ajustes al currículo',
 'participantes':'Personas implicadas','evaluacion_final':'Evaluación final del plan de intervención'}

def editar_celda(doc,tabla,indice,campo,valor):
    if campo not in FORMATOS[doc['formato']]['tablas'].get(tabla,[]):raise ValueError('Campo fuera del formato.')
    if not 0<=indice<len(doc['tablas'][tabla]):raise ValueError('La fila cambió; vuelve a abrir el documento.')
    if doc['tablas'][tabla][indice].get('_sesion_equipo'):raise ValueError('Edita esta actividad en sus sesiones vinculadas.')
    result=deepcopy(doc);result['tablas'][tabla][indice][campo]=str(valor or '');return result

def nueva_fila(doc,tabla):
    headers=FORMATOS[doc['formato']]['tablas'].get(tabla)
    if headers is None:raise ValueError('Tabla fuera del formato.')
    if len(doc['tablas'][tabla])>=100:raise ValueError('Revisa las cien filas existentes antes de añadir otra.')
    result=deepcopy(doc);result['tablas'][tabla].append(dict.fromkeys(headers,''));return result

def quitar_fila(doc,tabla,indice):
    if tabla not in FORMATOS[doc['formato']]['tablas']:raise ValueError('Tabla fuera del formato.')
    if not 0<=indice<len(doc['tablas'][tabla]):raise ValueError('La fila cambió.')
    if doc['tablas'][tabla][indice].get('_sesion_equipo'):raise ValueError('Retira esta actividad desde sus sesiones vinculadas.')
    result=deepcopy(doc);result['tablas'][tabla].pop(indice);return result

def editar_guia(doc,parche,base):
    if doc['metadatos'].get('guia_compartida'):raise PermissionError('Edita la guía compartida desde sus aportaciones.')
    from services.planeacion_modalidad import GUIA_XIX
    permitidos=set(GUIA_XIX)-{'Nombre alumno','Discapacidad o condición'}
    ids={a['ID_Alumno'] for a in doc['datos']['Alumnos']}
    if any(r.get('ID_Alumno') not in ids for r in base):raise PermissionError('La guía incluye alumnos ajenos.')
    result=deepcopy(doc);rows=deepcopy(base)
    for i,campos in parche.get('edited_rows',{}).items():
        if 0<=int(i)<len(rows):rows[int(i)].update({k:str(v or '') for k,v in campos.items() if k in permitidos})
    previo=result['metadatos'].get('guia_grupal_manual',{})
    result['metadatos']['guia_grupal_manual']={**previo,'filas':rows};return result


# Tabla y columna donde una evidencia del expediente se vuelve punto de partida
# del formato. Solo se copia la necesidad/barrera; objetivos y apoyos los redacta
# la docente (no se infieren desde la evidencia).
DESTINO_EVIDENCIA={'XXIII':('aprendizajes','Necesidades educativas específicas'),
                   'XXV':('barreras','Barreras para el Aprendizaje y la Participación'),
                   'XXI':('necesidades','NEE')}


def usar_evidencia(doc,fuente,limite=300):
    """Copia una evidencia ya registrada como nueva fila editable (capturar una vez)."""
    tabla,campo=DESTINO_EVIDENCIA[doc['formato']]
    texto=' '.join(str(fuente.get('texto','')).split())[:limite]
    if not texto:raise ValueError('La evidencia no tiene texto para usar.')
    valor='['+str(fuente.get('tipo','EVIDENCIA'))+' · '+str(fuente.get('referencia',''))+'] '+texto
    if any(r.get(campo)==valor for r in doc['tablas'][tabla]):raise ValueError('Esta evidencia ya está en tu borrador.')
    result=nueva_fila(doc,tabla);result['tablas'][tabla][-1][campo]=valor;return result


def periodo_sugerido(hoy):
    """Ciclo (año de inicio) y trimestre según el calendario escolar SEP.

    Agosto–diciembre: trimestre 1 del ciclo que inicia ese año; enero–marzo: 2;
    abril–julio: 3 (ambos del ciclo iniciado el año anterior).
    """
    if hoy.month>=8:return hoy.year,1
    return hoy.year-1,(2 if hoy.month<=3 else 3)

