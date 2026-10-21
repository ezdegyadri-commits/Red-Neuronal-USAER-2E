"""Resuelve referencias de grupo sin usar nombres ni depender de la interfaz."""
def clave_grupo(identificador):
    from config.settings import ESCUELAS_USAER
    from utils.escolar import grado_canonico,grupo_canonico
    for codigo in ESCUELAS_USAER.values():
        prefijo='GRUPO-'+str(codigo)+'-'
        if not str(identificador).startswith(prefijo):continue
        partes=str(identificador)[len(prefijo):].rsplit('-',1)
        if len(partes)!=2:return None
        grado,grupo=grado_canonico(partes[0]),grupo_canonico(partes[1])
        if grado not in tuple(f'{i}°' for i in range(1,7)) or not grupo:return None
        return str(codigo),grado,grupo
    return None


def ids_contexto(frame,identificador):
    from config.settings import ESCUELAS_USAER
    from utils.escolar import grado_canonico,grupo_canonico
    identificador=str(identificador)
    if not identificador.startswith('GRUPO-'):
        return [identificador] if identificador in set(frame.get('ID_Alumno',[])) else []
    for codigo in ESCUELAS_USAER.values():
        prefijo='GRUPO-'+str(codigo)+'-'
        if not identificador.startswith(prefijo):continue
        tokens=identificador[len(prefijo):].rsplit('-',1)
        if len(tokens)!=2:return []
        return [str(r['ID_Alumno']) for r in frame.fillna('').to_dict('records')
            if str(r.get('ID_Escuela',''))==str(codigo)
            and grado_canonico(r.get('Grado'))==grado_canonico(tokens[0])
            and grupo_canonico(r.get('Grupo'))==grupo_canonico(tokens[1])]
    return []
