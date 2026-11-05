"""Contextos oficiales: captura única en el Anexo XVII."""
from copy import deepcopy
from fastapi import HTTPException
from pydantic import BaseModel, ConfigDict, Field
from piloto_spa.backend.evaluacion import anexo_epp, editar_anexo
from services.epp_modelo import FAMILIA, FAMILIA_OFICIAL, HISTORIA

APARTADOS = {
    'escolar': ('Aprendizaje', ('6.1. Contexto escolar', '6.1. Historia escolar'), 'historia'),
    'sociofamiliar': ('Trabajo Social', ('6.2. Contexto familiar', '6.3. Contexto social'), 'familia'),
}

class CapturaContexto(BaseModel):
    model_config = ConfigDict(extra='forbid')
    revision: str = Field(max_length=64)
    campos: dict[str, str]
    filas: list[dict[str, str]] = Field(default_factory=list, max_length=100)

def consultar(epp, tipo, user):
    if tipo not in APARTADOS:
        raise HTTPException(404, 'Contexto no disponible.')
    area, campos, tabla = APARTADOS[tipo]
    parte = anexo_epp(epp)['partes'][area]
    contenido = parte['contenido']
    return {'revision': epp['revision'], 'ciclo': epp['ciclo'], 'area': area,
            'editable': user.director or user.area == area,
            'autor': parte.get('autor', ''), 'fecha': parte.get('fecha', ''),
            'campos': {k: contenido['campos'].get(k, '') for k in campos},
            'filas': deepcopy(contenido.get(tabla, [])), 'tabla': tabla,
            'columnas': list(HISTORIA if tabla == 'historia' else FAMILIA_OFICIAL),
            'columnas_adicionales': list(FAMILIA) if tabla == 'familia' else []}

def guardar(epp, tipo, payload, user):
    actual = consultar(epp, tipo, user)
    if not actual['editable']:
        raise HTTPException(403, 'La captura corresponde a otra función.')
    area, campos, tabla = APARTADOS[tipo]
    if set(payload.campos) != set(campos):
        raise HTTPException(422, 'Conserva los apartados originales del contexto.')
    contenido = anexo_epp(epp)['partes'][area]['contenido']
    contenido['campos'].update(payload.campos)
    contenido[tabla] = deepcopy(payload.filas)
    contenido['validada'] = False
    return editar_anexo(epp, area, contenido, payload.revision, user, [])

def fuentes(epp):
    # Reutiliza únicamente la narrativa; nunca agrega la tabla de familiares.
    partes = anexo_epp(epp)['partes']
    salida = []
    for tipo, (area, campos, _) in APARTADOS.items():
        parte = partes[area]
        texto = '\n'.join(k + ': ' + parte['contenido']['campos'].get(k, '')
                          for k in campos if parte['contenido']['campos'].get(k, '').strip())
        if texto:
            salida.append(('Contexto ' + tipo,
                           f"{epp['id']} · rev. {epp['revision']} · {parte.get('fecha', '')}", texto))
    return salida
