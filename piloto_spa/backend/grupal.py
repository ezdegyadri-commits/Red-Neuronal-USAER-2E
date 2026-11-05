"""Reglas de edición de la guía anual, independientes de React."""
from copy import deepcopy

from fastapi import HTTPException

from services.planeacion_modalidad import GUIA_XIX, GUIA_XX, guia_grupal
from utils.text import normalizar_texto


def area_compartida(user):
    rol = normalizar_texto(user.rol).replace("_", " ")
    return user.director or (
        rol in {"MAESTRA DE APOYO", "MAESTRO DE APOYO", "APOYO", "APRENDIZAJE", "PARADOCENTE",
                "PSICOLOGIA", "COMUNICACION", "TRABAJO SOCIAL"}
    )


def alcance_grupo(user, escuela):
    return area_compartida(user) and (
        user.director or "TODAS" in user.escuelas_permitidas or escuela in user.escuelas_permitidas
    )


def puede_coordinar(user):
    return user.director or user.area == "Aprendizaje"


def columnas_editables(user):
    if user.director:
        return GUIA_XIX[2:]
    if user.area == "Aprendizaje":
        return ["Fecha derivación", "Aprendizaje", "Situación inicial", "Situación final"]
    return [user.area]


def actualizar_guia(doc):
    guia = guia_grupal(doc)
    filas_sin_id = [r for r in guia["as"] if not r.get("ID_Alumno")]
    anteriores = {r["ID_Alumno"]: r for r in guia["as"] if r.get("ID_Alumno")}
    for alumno in doc["datos"]["Alumnos"]:
        aid = alumno["ID_Alumno"]
        if "APTITUD" in normalizar_texto(alumno.get("Condición") or "") or aid in anteriores:
            fila = anteriores.setdefault(aid, {"ID_Alumno": aid})
            fila["Nombre alumno"] = alumno["Nombre del alumno"]
            fila.setdefault("Fecha derivación", alumno.get("Fecha_Derivacion", ""))
    guia["as"] = filas_sin_id + list(anteriores.values())
    doc["metadatos"]["guia_grupal_manual"] = guia


def _editar_filas(actuales, enviadas, campos):
    if not isinstance(enviadas, list):
        raise HTTPException(422, "Las filas de la guía son inválidas.")
    actuales_id = {r.get("ID_Alumno"): r for r in actuales if r.get("ID_Alumno")}
    vistas = set()
    for fila in enviadas:
        if isinstance(fila, dict) and not fila.get("ID_Alumno") and fila in actuales:
            continue
        if not isinstance(fila, dict) or not isinstance(fila.get("ID_Alumno"), str):
            raise HTTPException(422, "Cada fila requiere el identificador del alumno.")
        aid = fila["ID_Alumno"]
        if aid in vistas or aid not in actuales_id:
            raise HTTPException(422, "La fila no pertenece a la matrícula de esta guía.")
        vistas.add(aid)
        original = actuales_id[aid]
        for k, v in fila.items():
            if k in campos:
                if not isinstance(v, str) or len(v) > 12000:
                    raise HTTPException(422, "El texto de la guía es inválido.")
                original[k] = v
            elif v != original.get(k, ""):
                raise HTTPException(403, "Esa columna pertenece a otra función.")


def editar_grupo(actual, cambios, user):
    if cambios.get("revision") != actual["revision"]:
        raise HTTPException(409, "La guía cambió. Reabre el documento antes de guardar.")
    doc = deepcopy(actual)
    meta = doc["metadatos"]
    entrada = cambios["metadatos"]
    guia = meta["guia_grupal_manual"]
    edicion = entrada.get("guia_grupal_manual", {})
    if not isinstance(edicion, dict):
        raise HTTPException(422, "La guía es inválida.")
    coordina = puede_coordinar(user)
    _editar_filas(guia["filas"], edicion.get("filas", []), columnas_editables(user))
    _editar_filas(guia["as"], edicion.get("as", []), GUIA_XX[1:] if coordina else [])
    if "contexto_aulico" in entrada and entrada["contexto_aulico"] != meta.get("contexto_aulico"):
        if not coordina:
            raise HTTPException(403, "La observación áulica corresponde a la coordinación de la guía.")
        from piloto_spa.backend.contexto_aulico import validar
        meta["contexto_aulico"] = validar(entrada["contexto_aulico"], user.usuario)
    if coordina:
        doc["tablas"] = cambios["tablas"]
        doc["textos"] = cambios["textos"]
        for key in ("titulo", "spa_pda_id", "spa_campo_pda"):
            if key in entrada:
                if not isinstance(entrada[key], str) or len(entrada[key]) > 300:
                    raise HTTPException(422, "Dato de planeación inválido.")
                meta[key] = entrada[key]
    elif (
        cambios["tablas"] != doc["tablas"] or cambios["textos"] != doc["textos"]
        or entrada.get("titulo", meta.get("titulo")) != meta.get("titulo")
    ):
        raise HTTPException(403, "Edita únicamente la columna de tu área.")
    return doc


def sincronizar_matricula(doc, registros):
    from services.planeacion_compartida import alumno_padron
    from services.planeacion_modalidad import modalidad
    from utils.escolar import grado_canonico, grupo_canonico

    datos, meta = doc["datos"], doc["metadatos"]
    alcance = meta["alcance_grupal"]
    padron = {r["ID_Alumno"]: r for r in registros}
    guia = meta["guia_grupal_manual"]
    retirados = meta.setdefault("alumnos_retirados_del_grupo", {})
    activos = []
    for alumno in datos["Alumnos"]:
        aid = alumno["ID_Alumno"]
        row = padron.get(aid)
        if row is not None and (
            normalizar_texto(row.get("Estatus")) in {"BAJA", "INACTIVO", "RETIRADO", "ELIMINADO"}
            or row["ID_Escuela"] != datos["ID_Escuela"]
            or grado_canonico(row["Grado"]) != alcance["grado"]
            or grupo_canonico(row["Grupo"]) != alcance["grupo"]
        ):
            retirados[aid] = {"alumno": alumno, "motivo": "Cambio de matrícula",
                             "fila": next((r for r in guia["filas"] if r["ID_Alumno"] == aid), None),
                             "fila_as": next((r for r in guia["as"] if r.get("ID_Alumno") == aid), None)}
        else:
            activos.append(alumno)
    presentes = {a["ID_Alumno"] for a in activos}
    for aid, r in padron.items():
        if (aid not in presentes and r["ID_Escuela"] == datos["ID_Escuela"]
                and grado_canonico(r["Grado"]) == alcance["grado"]
                and grupo_canonico(r["Grupo"]) == alcance["grupo"]
                and modalidad(r) == "grupal"
                and normalizar_texto(r.get("Estatus")) not in {"BAJA", "INACTIVO", "RETIRADO", "ELIMINADO"}):
            activos.append(alumno_padron(r))
            presentes.add(aid)
            anterior = retirados.pop(aid, {})
            for tabla, key in (("filas", "fila"), ("as", "fila_as")):
                if anterior.get(key):
                    guia[tabla].append(anterior[key])
    datos["Alumnos"] = activos
    guia["as"] = [r for r in guia["as"] if not r.get("ID_Alumno") or r["ID_Alumno"] in presentes]
    actualizar_guia(doc)
    return list(presentes)
