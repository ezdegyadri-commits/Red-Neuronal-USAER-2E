"""Servicio de gestión y registro de maestros regulares de escuelas primarias."""
import json
import os
from datetime import datetime
from uuid import uuid4
import pandas as pd
from zoneinfo import ZoneInfo
from config.settings import ESCUELAS_USAER, SCHOOL_YEAR
from utils.escolar import grado_canonico, grupo_canonico
from utils.text import normalizar_texto

ZONA = ZoneInfo("America/Merida")

# Las 7 escuelas primarias atendidas por la USAER 02E
ESCUELAS_PRIMARIAS = [
    "Damián Carmona",
    "Ichcaanziho",
    "Gregorio Torres Quintero",
    "Remigio Aguilar Sosa",
    "Elvira Parra Ávila",
    "Manuel Sarrado",
    "Domingo Solís Rodríguez",
]

GRADOS = ["1°", "2°", "3°", "4°", "5°", "6°"]
GRUPOS = ["A", "B", "C", "D", "E"]
TURNOS = ["Matutino", "Vespertino", "Jornada Completa / Tiempo Completo"]

HEADERS_DOCENTES_REGULARES = [
    "ID_Registro",
    "Fecha_Registro",
    "Ciclo_Escolar",
    "ID_Escuela",
    "Nombre_Escuela",
    "Turno",
    "Grado",
    "Grupo",
    "Nombre_Docente",
    "Telefono",
    "Email",
    "Observaciones",
    "Actualizado_Por",
]

_LOCAL_BACKUP_PATH = os.path.join(os.path.dirname(__file__), "..", "data", "docentes_regulares_backup.json")


def _guardar_local(registro):
    """Respaldo de contingencia local para no perder nunca un registro."""
    registros = _leer_local()
    # Las correcciones también se conservan como versiones en contingencia.
    if registro not in registros:
        registros.append(registro)
    try:
        os.makedirs(os.path.dirname(_LOCAL_BACKUP_PATH), exist_ok=True)
        with open(_LOCAL_BACKUP_PATH, "w", encoding="utf-8") as f:
            json.dump(registros, f, ensure_ascii=False, indent=2)
        return True
    except Exception:
        return False


def _leer_local():
    """Lee registros del respaldo local si existe."""
    if os.path.exists(_LOCAL_BACKUP_PATH):
        try:
            with open(_LOCAL_BACKUP_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            return []
    return []


def registrar_docente_regular(
    escuela,
    grado,
    grupo,
    nombre_docente,
    turno="Matutino",
    telefono="",
    email="",
    observaciones="",
    ciclo_escolar=None,
    actualizado_por='',
):
    """Registra o actualiza a un maestro de grupo en Google Sheets y respaldo."""
    escuela = str(escuela or "").strip()
    grado = grado_canonico(grado)
    grupo = grupo_canonico(grupo)
    nombre_docente = str(nombre_docente or "").strip()
    turno = str(turno or "Matutino").strip()

    if not escuela:
        raise ValueError("Debes seleccionar una escuela primaria.")
    if not grado:
        raise ValueError("Debes especificar el grado escolar (ej. 1°, 2°).")
    if not grupo:
        raise ValueError("Debes especificar el grupo escolar (ej. A, B).")
    if not nombre_docente:
        raise ValueError("Debes ingresar el nombre completo del docente de grupo.")
    if escuela not in ESCUELAS_PRIMARIAS or grado not in GRADOS or grupo not in GRUPOS or turno not in TURNOS:
        raise ValueError('Utiliza las escuelas, grados, grupos y turnos del catálogo.')

    id_escuela = ESCUELAS_USAER.get(escuela, "")
    ahora = datetime.now(ZONA).isoformat(timespec="microseconds")
    ciclo = _ciclo(ciclo_escolar or SCHOOL_YEAR)

    registro = {
        "ID_Registro": f"DOC-{uuid4().hex[:8].upper()}",
        "Fecha_Registro": ahora,
        "Ciclo_Escolar": ciclo,
        "ID_Escuela": id_escuela,
        "Nombre_Escuela": escuela,
        "Turno": turno,
        "Grado": grado,
        "Grupo": grupo,
        "Nombre_Docente": nombre_docente,
        "Telefono": str(telefono or "").strip(),
        "Email": str(email or "").strip(),
        "Observaciones": str(observaciones or "").strip(),
        "Actualizado_Por":str(actualizado_por or '').strip(),
    }

    return _persistir(registro)


def _persistir(registro):
    """Append de otra versión; jamás borra ni reescribe filas anteriores."""
    respaldo=_guardar_local(registro)
    confirmado=False
    try:
        from data.google import ensure_headers, append_dict, clear_cache
        ensure_headers("Docentes_Regulares", HEADERS_DOCENTES_REGULARES)
        append_dict("Docentes_Regulares", registro)
        clear_cache('Docentes_Regulares')
        confirmado=True
    except Exception:
        # Si no hay credenciales o está offline, el respaldo local asegura persistencia
        pass

    if not confirmado and not respaldo:raise RuntimeError('No se confirmó el guardado ni el respaldo local. La captura sigue abierta; vuelve a intentar.')
    return {**registro,'_guardado_central':confirmado}


def _ciclo(valor):
    return str(valor or '').replace('–','-').replace(' ','')


def _fecha_orden(registro):
    try:
        fecha=datetime.fromisoformat(str(registro.get('Fecha_Registro','')).replace('Z','+00:00'))
        return (fecha if fecha.tzinfo else fecha.replace(tzinfo=ZONA)).timestamp()
    except (TypeError,ValueError):return 0


def escuelas_del_actor(actor):
    """El formulario no ofrece escuelas fuera de la asignación de la cuenta."""
    from services.asignaciones import escuelas_asignadas, es_direccion
    if not actor.get('autenticado') or not actor.get('cuenta'):
        raise PermissionError('Inicia sesión para identificar tu escuela asignada.')
    rol=actor.get('rol','')
    if es_direccion(rol):return ESCUELAS_PRIMARIAS.copy()
    if 'APOYO' not in normalizar_texto(rol):
        raise PermissionError('El catálogo lo actualizan las maestras de apoyo y Dirección.')
    oficiales=escuelas_asignadas(actor.get('nombre',''),rol)
    # Las asignaciones oficiales prevalecen sobre una selección del navegador.
    permitidas=oficiales or str(actor.get('escuelas_permitidas','')).split(',')
    from services.planeacion_matricula import clave_escuela
    claves={clave_escuela(e) for e in permitidas}
    return [e for e in ESCUELAS_PRIMARIAS if ESCUELAS_USAER[e] in claves]


def guardar_docente_asignado(actor,escuela,**campos):
    if escuela not in escuelas_del_actor(actor):
        raise PermissionError('Sólo puedes registrar docentes de tu escuela asignada.')
    # La identidad se registra en las correcciones; el alta usa el mismo servicio.
    return registrar_docente_regular(escuela=escuela,actualizado_por=actor['cuenta'],**campos)


def editar_docente_regular(id_registro,cambios,actor):
    permitidas=escuelas_del_actor(actor)
    anterior=next((r for r in listar_docentes_regulares() if r.get('ID_Registro')==str(id_registro)),None)
    if not anterior or anterior.get('Nombre_Escuela') not in permitidas:
        raise PermissionError('Este docente no pertenece a tu escuela asignada.')
    campos={'Nombre_Docente','Grado','Grupo','Turno','Telefono','Email','Observaciones'}
    if not cambios or set(cambios)-campos:raise ValueError('Conserva la escuela, el ciclo y la identidad del registro.')
    nuevo={k:anterior.get(k,'') for k in HEADERS_DOCENTES_REGULARES}
    nuevo.update({k:str(v or '').strip() for k,v in cambios.items()})
    nuevo['Grado']=grado_canonico(nuevo['Grado']);nuevo['Grupo']=grupo_canonico(nuevo['Grupo'])
    if not nuevo['Nombre_Docente'] or nuevo['Grado'] not in GRADOS or nuevo['Grupo'] not in GRUPOS or nuevo['Turno'] not in TURNOS:
        raise ValueError('Revisa el nombre, grado, grupo y turno del docente.')
    for r in listar_docentes_regulares(escuela=nuevo['Nombre_Escuela']):
        if (r.get('ID_Registro')!=nuevo['ID_Registro'] and _ciclo(r.get('Ciclo_Escolar'))==_ciclo(nuevo.get('Ciclo_Escolar'))
            and (r.get('Turno'),r.get('Grado'),r.get('Grupo'))==(nuevo['Turno'],nuevo['Grado'],nuevo['Grupo'])):
            raise ValueError('Ya hay otro maestro registrado para ese grado, grupo y turno. Corrige su registro para evitar duplicados.')
    nuevo.update(Fecha_Registro=datetime.now(ZONA).isoformat(timespec='microseconds'),Actualizado_Por=actor['cuenta'])
    return _persistir(nuevo)


def registrar_lote_docentes(escuela, turno, lista_docentes, ciclo_escolar=None):
    """Registra múltiples docentes para una misma escuela y turno."""
    guardados = []
    for d in lista_docentes:
        nom = d.get("Nombre_Docente", "").strip()
        grd = d.get("Grado", "").strip()
        grp = d.get("Grupo", "").strip()
        if nom and grd and grp:
            reg = registrar_docente_regular(
                escuela=escuela,
                grado=grd,
                grupo=grp,
                nombre_docente=nom,
                turno=turno,
                telefono=d.get("Telefono", ""),
                email=d.get("Email", ""),
                observaciones=d.get("Observaciones", ""),
                ciclo_escolar=ciclo_escolar,
            )
            guardados.append(reg)
    return guardados


def listar_docentes_regulares(escuela=None):
    """Obtiene el listado consolidado de docentes regulares registrados."""
    registros = []
    # 1. Intentar leer de Google Sheets
    try:
        from data.google import df_sheet
        df = df_sheet("Docentes_Regulares")
        if not df.empty:
            registros = df.to_dict("records")
    except Exception:
        pass

    # 2. Combinar con registros locales de contingencia
    locales = _leer_local()
    from services.planeacion_matricula import clave_escuela
    porid={}
    for indice,r in enumerate(registros+locales):
        r=dict(r)
        r['Grado']=grado_canonico(r.get('Grado'));r['Grupo']=grupo_canonico(r.get('Grupo'))
        r['Ciclo_Escolar']=_ciclo(r.get('Ciclo_Escolar'))
        r['ID_Escuela']=clave_escuela(r.get('ID_Escuela') or r.get('Nombre_Escuela'))
        r['Nombre_Escuela']=next((n for n,c in ESCUELAS_USAER.items() if c==r['ID_Escuela']),r.get('Nombre_Escuela',''))
        key=r.get('ID_Registro') or ('sin-id',indice)
        if key not in porid or _fecha_orden(r)>_fecha_orden(porid[key]):porid[key]=r
    mapa={}
    for r in porid.values():
        k=(r.get('Ciclo_Escolar',''),r['ID_Escuela'],r.get('Turno',''),r['Grado'],r['Grupo'])
        if k not in mapa or _fecha_orden(r)>_fecha_orden(mapa[k]):mapa[k]=r

    todos = list(mapa.values())
    # Omitir cualquier registro generado por pruebas o con palabras clave de test
    todos = [
        r for r in todos
        if not any(token in str(r.get("Nombre_Docente", "")).lower() for token in ("prueba", "test", "ficticio"))
    ]
    if escuela:
        todos = [r for r in todos if r['ID_Escuela']==clave_escuela(escuela)]

    # Ordenar por Escuela, Turno, Grado, Grupo
    todos.sort(key=lambda x: (
        x.get("Nombre_Escuela", ""),
        x.get("Turno", ""),
        x.get("Grado", ""),
        x.get("Grupo", ""),
    ))
    return todos


def eliminar_docente_regular(id_registro):
    """Elimina un registro de docente del respaldo local y de Sheets si aplica."""
    id_registro = str(id_registro).strip()
    locales = _leer_local()
    nuevos = [r for r in locales if r.get("ID_Registro") != id_registro]
    if len(nuevos) != len(locales):
        try:
            with open(_LOCAL_BACKUP_PATH, "w", encoding="utf-8") as f:
                json.dump(nuevos, f, ensure_ascii=False, indent=2)
        except Exception:
            pass


def resumen_cobertura_escuelas():
    """Calcula cuántos grupos tienen maestro registrado por escuela."""
    docentes = listar_docentes_regulares()
    resumen = []
    for esc in ESCUELAS_PRIMARIAS:
        regs = [d for d in docentes if d.get("Nombre_Escuela") == esc]
        grupos_cubiertos = len(regs)
        resumen.append({
            "Escuela": esc,
            "CCT": ESCUELAS_USAER.get(esc, ""),
            "Docentes_Registrados": grupos_cubiertos,
            "Detalle": regs,
        })
    return resumen
