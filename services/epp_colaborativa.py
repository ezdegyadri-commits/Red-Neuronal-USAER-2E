"""Permisos por campo compartido; cada cambio conserva el área canónica."""
from copy import deepcopy
from services.epp_modelo import campos, GENERALES

COMPARTIDOS={
 ('Comunicación','Aprendizaje','campos'):{'4.1. Orientación temporal'},
 ('Comunicación','Psicología','campos'):{'4.3. Coordinación motriz fina','4.3. Coordinación motriz gruesa'},
 ('Trabajo Social','Aprendizaje','generales'):set(GENERALES),
}

def puede(actor,area,seccion,campo):
    if actor.get('director'):return False
    if area==actor.get('area'):return True
    return campo in COMPARTIDOS.get((actor.get('area'),area,seccion),set())

def comparte(actor,area):
    return not actor.get('director') and any(a==actor.get('area') and b==area for a,b,_ in COMPARTIDOS)

def validar_cambios(actor,area,anterior,nuevo):
    if area==actor.get('area') or area=='Conclusión':return
    for key in set(anterior)|set(nuevo):
        a,b=anterior.get(key),nuevo.get(key)
        if a==b:continue
        if key=='validada' and b is False:continue
        if key=='generales_editados' and set(b or [])-set(a or [])<=COMPARTIDOS.get((actor.get('area'),area,'generales'),set()):continue
        if key in ('campos','generales','origen_generales','no_requeridos','textos_previos_no_requeridos') and isinstance(a or {},dict) and isinstance(b or {},dict):
            section='campos' if key in ('no_requeridos','textos_previos_no_requeridos') else 'generales' if key=='origen_generales' else key
            for campo in set(a or {})|set(b or {}):
                if (a or {}).get(campo)!=(b or {}).get(campo) and not puede(actor,area,section,campo):
                    raise PermissionError('Este apartado no está compartido con tu función.')
            continue
        raise PermissionError('Puedes editar solo los campos compartidos; la revisión y el resto del área conservan a su responsable.')

def no_requiere(value,campo,activar):
    result=deepcopy(value)
    if campo not in result.get('campos',{}):raise ValueError('Apartado no reconocido.')
    flags=result.setdefault('no_requeridos',{});previos=result.setdefault('textos_previos_no_requeridos',{})
    if activar and not flags.get(campo):
        previos[campo]=result['campos'][campo];result['campos'][campo]='No se requiere';flags[campo]=True
    elif not activar and flags.get(campo):
        result['campos'][campo]=previos.pop(campo,'');flags.pop(campo,None)
    result['validada']=False
    return result

def omitido(value,campo):
    return value.get('no_requeridos',{}).get(campo) is True
