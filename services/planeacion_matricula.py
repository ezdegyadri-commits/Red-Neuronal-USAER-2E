"""Proyección de escuelas equivalentes; nunca reescribe el padrón histórico."""
from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto


def clave_escuela(valor):
    normal=normalizar_texto(valor)
    for nombre,clave in ESCUELAS_USAER.items():
        if normal in {normalizar_texto(nombre),normalizar_texto(clave)}:
            return clave
    return str(valor or '').strip()


def preparar(frame):
    """Agrupa la misma escuela por su clave, después de aplicar permisos."""
    result=frame.copy()
    if result.empty or 'ID_Escuela' not in result:return result
    from utils.escolar import grado_canonico,grupo_canonico
    if 'Grado' in result:result['Grado']=result['Grado'].map(grado_canonico)
    if 'Grupo' in result:result['Grupo']=result['Grupo'].map(grupo_canonico)
    result['ID_Escuela']=result['ID_Escuela'].map(clave_escuela)
    nombres={clave:nombre for nombre,clave in ESCUELAS_USAER.items()}
    if 'Nombre_Escuela' in result:
        result['Nombre_Escuela']=[nombres.get(clave,nombre) for clave,nombre in
                                  zip(result['ID_Escuela'],result['Nombre_Escuela'])]
    return result
