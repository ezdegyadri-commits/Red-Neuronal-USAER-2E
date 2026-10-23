"""Adaptación del instrumento de valoración aportado por Dirección.

Los catorce indicadores y la coherencia se valoran por separado. Una
respuesta pendiente nunca cuenta como cero ni genera una clasificación.
"""
from copy import deepcopy

VERSION = 'USAER-instrumento-planeacion-v1'
ESCALA = {0: 'No lo realiza', 1: 'Insuficiente', 2: 'Suficiente', 3: 'Satisfactorio'}
INDICADORES = (
    'Presenta los datos generales completos.',
    'Presenta las necesidades educativas específicas (NEE) a satisfacer con los alumnos.',
    'Establece los procesos de desarrollo de aprendizaje de los diferentes campos formativos, directamente relacionados con las NEE a satisfacer, de acuerdo con el programa de estudios vigente.',
    'Los descriptores de logro establecidos son concretos y posibles de medir, siguiendo la estructura: sujeto + verbo + complemento.',
    'Redacta descriptores de logro diferenciados para cada alumno o subgrupo de alumnos.',
    'Describe de forma clara las actividades a trabajar en los diferentes contextos.',
    'En la descripción de las actividades se incluyen los apoyos y ajustes razonables que dan respuesta a las NEE de los alumnos.',
    'Las actividades y estrategias didácticas planeadas llevan a que el alumno alcance lo propuesto en los descriptores de logro.',
    'Se consideran actividades diferenciadas en función de las características individuales, los ritmos y estilos de aprendizaje de los alumnos.',
    'Establece la temporalidad para el desarrollo de las actividades.',
    'Menciona los materiales y recursos que utilizará en su intervención.',
    'Describe las acciones que se realizarán dentro del grupo, contemplando la vinculación con el maestro de grupo regular.',
    'Describe las acciones que se realizarán con la familia para fortalecer el aprendizaje de los alumnos y a qué aspectos irán dirigidas.',
    'Describe las acciones y los instrumentos que se utilizarán para realizar la evaluación.',
)
COHERENCIA = '¿Los apoyos y ajustes razonables, los contenidos seleccionados, las actividades y la evaluación responden a las necesidades educativas específicas de los alumnos y se articulan para favorecer y valorar su aprendizaje?'
DESCRIPTORES = {
    3: 'Existe una vinculación clara y congruente entre las necesidades educativas específicas, los apoyos y ajustes razonables, los contenidos o PDA, las actividades y la evaluación. Los apoyos responden a las necesidades identificadas, las actividades favorecen el aprendizaje previsto y la evaluación permite valorar los avances del alumno respecto a los propósitos establecidos.',
    2: 'Los elementos de la planeación guardan una relación generalmente congruente; sin embargo, alguno de ellos requiere mayor precisión o articulación. Por ejemplo, los apoyos no se vinculan explícitamente con una necesidad identificada o la evaluación no permite valorar completamente el aprendizaje esperado.',
    1: 'La relación entre los elementos es parcial o poco clara. Se identifican necesidades, apoyos, contenidos, actividades o evaluación, pero existen inconsistencias importantes; por ejemplo, las actividades no responden a los contenidos seleccionados o los apoyos propuestos no atienden las necesidades identificadas.',
    0: 'No se identifica una relación entre las necesidades educativas específicas, los apoyos y ajustes razonables, los contenidos o PDA, las actividades y la evaluación. Los elementos están ausentes o se presentan de manera aislada, sin una articulación que permita reconocer cómo se favorecerá el aprendizaje del alumno.',
}


def vacia():
    return {'Version': VERSION, 'Indicadores': {str(i): None for i in range(1, 15)},
            'Coherencia': None, 'Observaciones': ''}


def validar(value):
    if not isinstance(value, dict) or set(value) != set(vacia()) or value.get('Version') != VERSION:
        raise ValueError('El instrumento no corresponde a la versión vigente.')
    if not isinstance(value['Indicadores'], dict) or set(value['Indicadores']) != set(vacia()['Indicadores']):
        raise ValueError('Conserva los catorce indicadores del instrumento.')
    for score in [*value['Indicadores'].values(), value['Coherencia']]:
        if score is not None and (type(score) is not int or score not in ESCALA):
            raise ValueError('Selecciona Pendiente o una valoración de 0 a 3.')
    if not isinstance(value['Observaciones'], str) or len(value['Observaciones']) > 2000:
        raise ValueError('Resume las observaciones a 2000 caracteres.')
    return deepcopy(value)


def resumen(value):
    value = validar(value)
    scores = [v for v in value['Indicadores'].values() if v is not None]
    return {'Respondidos': len(scores), 'Pendientes': 14-len(scores),
            'Subtotal': sum(scores), 'Total': sum(scores) if len(scores) == 14 else None,
            'Conteos': {s: scores.count(s) for s in ESCALA},
            'Coherencia': value['Coherencia']}


def editar(value, changes):
    result = validar(value)
    if changes.get('added_rows') or changes.get('deleted_rows'):
        raise ValueError('No se pueden agregar ni retirar indicadores.')
    for index, fields in changes.get('edited_rows', {}).items():
        if not str(index).isdigit() or not 0 <= int(index) < 14 or set(fields) != {'Valoración'}:
            raise ValueError('Solo se puede editar la valoración de los indicadores.')
        label = fields['Valoración']
        opciones = {'Pendiente': None, **{f'{s} · {t}': s for s, t in ESCALA.items()}}
        if label not in opciones:
            raise ValueError('Selecciona una opción del instrumento.')
        result['Indicadores'][str(int(index)+1)] = opciones[label]
    return validar(result)
