"""Sonda de IA con un caso sintético constante; no accede al padrón ni al expediente."""
from ai.planeacion_prompt import INSTRUCCIONES
CAMPOS=('objetivo','inicio','desarrollo','cierre','apoyos_dua','evidencia')
ESQUEMA={'type':'object','properties':{k:{'type':'string'} for k in CAMPOS},'required':list(CAMPOS),'additionalProperties':False}
CASO_FICTICIO=('PRUEBA TÉCNICA CON DATOS COMPLETAMENTE FICTICIOS. No corresponde a una persona real. '
    'Un estudiante ficticio participa en conversaciones breves y necesita apoyos visuales para pedir ayuda y esperar su turno. '
    'En un aula regular hay tarjetas de turnos y un horario visual; se dispone de 20 minutos. '
    'Propón UNA estrategia educativa inclusiva con objetivo observable, inicio, desarrollo, cierre, opciones DUA y evidencia de seguimiento. '
    'No emitas diagnósticos, puntuaciones ni afirmes resultados obtenidos. Devuelve exclusivamente el JSON del esquema solicitado.')
def validar(value):
    if not isinstance(value,dict) or set(value)!=set(CAMPOS):raise ValueError('La prueba no recibió todos los apartados de la estrategia.')
    if any(not isinstance(value[k],str) or not 15<=len(value[k].strip())<=5000 for k in CAMPOS):raise ValueError('La estrategia no tiene contenido verificable suficiente.')
    return {k:value[k].strip() for k in CAMPOS}
def generar(config):
    from ai.documento_json import generar as transportar
    return transportar(INSTRUCCIONES+'\n\n'+CASO_FICTICIO,ESQUEMA,validar,config,max_tokens=2500)
