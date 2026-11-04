"""Proyección de escuelas equivalentes; nunca reescribe el padrón histórico."""
from config.settings import ESCUELAS_USAER
from utils.text import normalizar_texto


ALIASES_ESCUELAS = {
    "ELVIRA PARRA": "ESC-005",
    "ELVIRA PARRA AVILA": "ESC-005",
    "DAMIAN CARMONA": "ESC-001",
    "ICHCAANZIHO": "ESC-002",
    "GREGORIO TORRES QUINTERO": "ESC-003",
    "REMIGIO AGUILAR SOSA": "ESC-004",
    "MANUEL SARRADO": "ESC-006",
    "DOMINGO SOLIS RODRIGUEZ": "ESC-007",
    "DOMINGO SOLIS": "ESC-007",
    "QUINTANA ROO": "ESC-008",
}

def clave_escuela(valor):
    if not valor:
        return ""
    normal = normalizar_texto(str(valor).strip())
    if normal in ALIASES_ESCUELAS:
        return ALIASES_ESCUELAS[normal]
    for nombre,clave in ESCUELAS_USAER.items():
        if normal in {normalizar_texto(nombre),normalizar_texto(clave)}:
            return clave
    for alias, clave in ALIASES_ESCUELAS.items():
        if alias in normal or normal in alias:
            return clave
    return str(valor or '').strip()


resolver_escuela = clave_escuela


def preparar(frame):
    """Agrupa la misma escuela por su clave, después de aplicar permisos."""
    result=frame.copy()
    if result.empty or 'ID_Escuela' not in result:return result
    from utils.escolar import grado_canonico,grupo_canonico
    if 'Grado' in result:result['Grado']=result['Grado'].map(grado_canonico)
    if 'Grupo' in result:result['Grupo']=result['Grupo'].map(grupo_canonico)
    if 'ID_Alumno' in result:result['ID_Alumno']=result['ID_Alumno'].astype(str).str.strip()
    if 'Nombre_Completo' in result:result['Nombre_Completo']=result['Nombre_Completo'].astype(str).str.strip().str.upper()
    result['ID_Escuela']=result['ID_Escuela'].map(clave_escuela)
    if 'Nombre_Escuela' in result:
        for idx in result.index:
            esc_act = result.at[idx, 'ID_Escuela']
            if not esc_act or esc_act not in ESCUELAS_USAER.values():
                c_nom = clave_escuela(result.at[idx, 'Nombre_Escuela'])
                if c_nom in ESCUELAS_USAER.values():
                    result.at[idx, 'ID_Escuela'] = c_nom
    nombres={clave:nombre for nombre,clave in ESCUELAS_USAER.items()}
    if 'Nombre_Escuela' in result:
        result['Nombre_Escuela']=[nombres.get(clave,str(nombre).strip()) for clave,nombre in
                                  zip(result['ID_Escuela'],result['Nombre_Escuela'])]
    return result
