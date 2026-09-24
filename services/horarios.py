"""Horarios de apoyo y avisos de cronogramas, con historial append-only."""

from __future__ import annotations

import re
from datetime import date, datetime, time
from uuid import uuid4
from zoneinfo import ZoneInfo

import pandas as pd

from config.settings import ESCUELAS_USAER
from data.google import clear_cache, ensure_headers, retry_google
from data import repository as repo
from services.asignaciones import escuelas_asignadas
from utils.text import normalizar_texto


ZONA = ZoneInfo("America/Mexico_City")
DIAS = ("Lunes", "Martes", "Miércoles", "Jueves", "Viernes")
HORARIOS_APOYO_HEADERS = [
    "ID_Version", "Guardado_En", "Maestra", "ID_Escuela", "Escuela",
    "Dia", "Inicio", "Fin", "Grupo", "Modalidad", "Espacio", "Actividad", "Estado",
]
RESTRICCIONES_HEADERS = [
    "ID_Version", "Cargado_En", "Cargado_Por", "ID_Escuela", "Escuela",
    "Dia", "Inicio", "Fin", "Grupo", "Actividad", "Responsable",
    "Archivo", "Estado",
]
AVISOS_HEADERS = [
    "ID_Aviso", "ID_Publicacion", "Fecha", "Destinatario", "Escuela",
    "Especialista", "Mes", "Resumen", "Estado", "Leida_En",
]

_ALIASES = {
    "Dia": ("DIA", "DIA DE LA SEMANA", "JORNADA"),
    "Inicio": ("INICIO", "HORA INICIO", "DESDE", "HORA"),
    "Fin": ("FIN", "HORA FIN", "HASTA", "TERMINO"),
    "Actividad": ("ACTIVIDAD", "ASIGNATURA", "MATERIA", "CLASE", "ESPACIO CURRICULAR"),
    "Grupo": ("GRUPO", "GRADO Y GRUPO", "GRADO GRUPO", "GRADO"),
    "Responsable": ("RESPONSABLE", "DOCENTE", "MAESTRO", "MAESTRA", "PROFESOR"),
    "Modalidad": ("MODALIDAD", "TIPO DE ATENCION", "TIPO DE ATENCIÓN"),
    "Espacio": ("ESPACIO", "LUGAR", "CONTEXTO", "ESPACIO DE ATENCION", "ESPACIO DE ATENCIÓN"),
}


def _ws(nombre, headers):
    return ensure_headers(nombre, headers)


def _leer(nombre, headers):
    ws = _ws(nombre, headers)
    values = retry_google(ws.get_all_values)
    if not values:
        return ws, list(headers), []
    cols = [str(value).strip() for value in values[0]]
    registros = []
    for fila_num, values_row in enumerate(values[1:], start=2):
        values_row = (list(values_row) + [""] * len(cols))[:len(cols)]
        row = dict(zip(cols, values_row))
        row["_fila"] = fila_num
        if any(str(value).strip() for key, value in row.items() if key != "_fila"):
            registros.append(row)
    return ws, cols, registros


def _a1(columna):
    salida = ""
    while columna:
        columna, resto = divmod(columna - 1, 26)
        salida = chr(65 + resto) + salida
    return salida


def _id_escuela(escuela):
    escuela_n = normalizar_texto(escuela)
    return next((codigo for nombre, codigo in ESCUELAS_USAER.items()
                 if normalizar_texto(nombre) == escuela_n), "")


def _hora_minutos(valor):
    if isinstance(valor, pd.Timestamp):
        valor = valor.time()
    if isinstance(valor, datetime):
        valor = valor.time()
    if isinstance(valor, time):
        return valor.hour * 60 + valor.minute
    if isinstance(valor, (int, float)) and 0 <= float(valor) < 1:
        return round(float(valor) * 24 * 60)
    texto = str(valor or "").strip().lower().replace("a. m.", "am").replace("p. m.", "pm")
    texto = texto.replace("a.m.", "am").replace("p.m.", "pm")
    texto = re.sub(r"\s+", "", texto)
    for fmt in ("%H:%M", "%H.%M", "%I:%M%p", "%I%p"):
        try:
            hora = datetime.strptime(texto, fmt).time()
            return hora.hour * 60 + hora.minute
        except ValueError:
            pass
    raise ValueError(f"Hora no reconocida: {valor!s}. Usa formato HH:MM, por ejemplo 08:00.")


def _hora_texto(valor):
    minutos = _hora_minutos(valor)
    return f"{minutos // 60:02d}:{minutos % 60:02d}"


def normalizar_dia(valor):
    dia = normalizar_texto(valor)
    claves = {
        "LUNES": "Lunes", "LUN": "Lunes",
        "MARTES": "Martes", "MAR": "Martes",
        "MIERCOLES": "Miércoles", "MIE": "Miércoles", "MIE.": "Miércoles",
        "JUEVES": "Jueves", "JUE": "Jueves",
        "VIERNES": "Viernes", "VIE": "Viernes",
    }
    if dia not in claves:
        raise ValueError(f"Día no reconocido: {valor!s}. Usa lunes a viernes.")
    return claves[dia]


def normalizar_tabla_horario(frame):
    """Convierte una tabla de Excel/CSV a Día, Inicio, Fin, Actividad, Grupo, Responsable."""
    if frame is None or frame.empty:
        raise ValueError("El archivo no contiene filas de horario.")
    originales = {normalizar_texto(col).replace("_", " "): col for col in frame.columns}
    mapeo = {}
    for destino, candidatos in _ALIASES.items():
        for encabezado, original in originales.items():
            if encabezado in candidatos:
                mapeo[destino] = original
                break
    faltantes = {"Dia", "Inicio", "Fin", "Actividad"} - set(mapeo)
    if faltantes:
        etiquetas = {"Dia": "Día", "Inicio": "Inicio", "Fin": "Fin", "Actividad": "Actividad o materia"}
        raise ValueError("Faltan columnas: " + ", ".join(etiquetas[c] for c in sorted(faltantes)) + ".")
    salida = []
    def valor_celda(fila, campo):
        if campo not in mapeo:
            return ""
        valor = fila.get(mapeo[campo], "")
        if pd.isna(valor):
            return ""
        return str(valor).strip()

    for indice, row in frame.iterrows():
        actividad = valor_celda(row, "Actividad")
        if not actividad:
            continue
        dia = normalizar_dia(valor_celda(row, "Dia"))
        inicio = _hora_texto(valor_celda(row, "Inicio"))
        fin = _hora_texto(valor_celda(row, "Fin"))
        if _hora_minutos(fin) <= _hora_minutos(inicio):
            raise ValueError(f"Fila {indice + 2}: la hora de fin debe ser posterior a la de inicio.")
        salida.append({
            "Dia": dia, "Inicio": inicio, "Fin": fin,
            "Actividad": actividad,
            "Grupo": valor_celda(row, "Grupo"),
            "Responsable": valor_celda(row, "Responsable"),
            "Modalidad": valor_celda(row, "Modalidad"),
            "Espacio": valor_celda(row, "Espacio"),
        })
    if not salida:
        raise ValueError("No encontré filas con actividad y horario válidos.")
    return pd.DataFrame(salida)


def _coincide_escuela(row, escuela):
    buscada = normalizar_texto(escuela)
    return buscada in {
        normalizar_texto(row.get("Escuela", "")),
        normalizar_texto(row.get("ID_Escuela", "")),
    }


def cargar_restricciones(escuela):
    _, _, rows = _leer("Horarios_Restricciones", RESTRICCIONES_HEADERS)
    activos = [row for row in rows if _coincide_escuela(row, escuela)
               and str(row.get("Estado", "ACTIVO")).upper() == "ACTIVO"]
    return pd.DataFrame(activos).drop(columns=["_fila"], errors="ignore")


def guardar_restricciones(escuela, cargado_por, archivo, frame):
    """Anexa la revisión del horario; la versión anterior queda marcada, nunca se borra."""
    rows = frame.to_dict("records") if isinstance(frame, pd.DataFrame) else list(frame)
    if not rows:
        raise ValueError("No hay filas de horario para guardar.")
    ws, headers, existentes = _leer("Horarios_Restricciones", RESTRICCIONES_HEADERS)
    version = uuid4().hex
    now = datetime.now(ZONA).isoformat(timespec="seconds")
    nuevos = []
    for item in rows:
        dia = normalizar_dia(item.get("Dia", ""))
        inicio, fin = _hora_texto(item.get("Inicio")), _hora_texto(item.get("Fin"))
        if _hora_minutos(fin) <= _hora_minutos(inicio):
            raise ValueError("Hay una fila cuyo fin no es posterior a su inicio.")
        actividad = str(item.get("Actividad", "")).strip()
        if not actividad:
            continue
        nuevos.append({
            "ID_Version": version, "Cargado_En": now, "Cargado_Por": cargado_por,
            "ID_Escuela": _id_escuela(escuela), "Escuela": escuela, "Dia": dia,
            "Inicio": inicio, "Fin": fin, "Grupo": str(item.get("Grupo", "")).strip(),
            "Actividad": actividad, "Responsable": str(item.get("Responsable", "")).strip(),
            "Archivo": archivo, "Estado": "ACTIVO",
        })
    if not nuevos:
        raise ValueError("No quedaron actividades válidas para guardar.")
    retry_google(lambda: ws.append_rows(
        [[row.get(header, "") for header in headers] for row in nuevos],
        value_input_option="USER_ENTERED",
    ))
    # A reemplazo del mismo archivo, se preservan las filas anteriores como historial.
    old = [row for row in existentes
           if _coincide_escuela(row, escuela)
           and str(row.get("Archivo", "")).strip() == archivo
           and str(row.get("Estado", "ACTIVO")).upper() == "ACTIVO"]
    if old and "Estado" in headers:
        pos = headers.index("Estado") + 1
        changes = [{"range": f"{_a1(pos)}{row['_fila']}", "values": [["SUSTITUIDO"]]} for row in old]
        try:
            retry_google(lambda: ws.batch_update(changes, value_input_option="RAW"))
        except Exception:
            # Se conserva la nueva versión; los duplicados de consulta se limitan a la más reciente.
            pass
    clear_cache("Horarios_Restricciones")
    return version, len(nuevos)


def cargar_horarios_apoyo(escuela):
    """Retorna la última versión por maestra en la escuela, conservando todo el historial."""
    _, _, rows = _leer("Horarios_Apoyo", HORARIOS_APOYO_HEADERS)
    rows = [row for row in rows if _coincide_escuela(row, escuela)
            and str(row.get("Estado", "ACTIVO")).upper() == "ACTIVO"]
    latest = {}
    for row in rows:
        latest[str(row.get("Maestra", "")).strip()] = str(row.get("ID_Version", ""))
    rows = [row for row in rows if latest.get(str(row.get("Maestra", "")).strip()) == str(row.get("ID_Version", ""))]
    return pd.DataFrame(rows).drop(columns=["_fila"], errors="ignore")


def guardar_horario_apoyo(maestra, escuela, frame):
    rows = frame.to_dict("records") if isinstance(frame, pd.DataFrame) else list(frame)
    if not rows:
        raise ValueError("Agrega al menos una sesión al horario.")
    ws, headers, _ = _leer("Horarios_Apoyo", HORARIOS_APOYO_HEADERS)
    version = uuid4().hex
    now = datetime.now(ZONA).isoformat(timespec="seconds")
    nuevos = []
    for item in rows:
        dia = normalizar_dia(item.get("Dia", ""))
        inicio, fin = _hora_texto(item.get("Inicio")), _hora_texto(item.get("Fin"))
        if _hora_minutos(fin) <= _hora_minutos(inicio):
            raise ValueError("Hay una sesión cuyo fin no es posterior a su inicio.")
        grupo = str(item.get("Grupo", "")).strip()
        actividad = str(item.get("Actividad", "")).strip()
        if not actividad:
            continue
        nuevos.append({
            "ID_Version": version, "Guardado_En": now, "Maestra": maestra,
            "ID_Escuela": _id_escuela(escuela), "Escuela": escuela, "Dia": dia,
            "Inicio": inicio, "Fin": fin, "Grupo": grupo,
            "Modalidad": str(item.get("Modalidad", "")).strip(),
            "Espacio": str(item.get("Espacio", "")).strip(),
            "Actividad": actividad, "Estado": "ACTIVO",
        })
    if not nuevos:
        raise ValueError("No hay sesiones completas para guardar.")
    retry_google(lambda: ws.append_rows(
        [[row.get(header, "") for header in headers] for row in nuevos],
        value_input_option="USER_ENTERED",
    ))
    clear_cache("Horarios_Apoyo")
    return version, len(nuevos)


def detectar_choques(propuesta, restricciones=None, horarios_apoyo=None):
    """Detecta solapes con clases cargadas y sesiones de apoyo del mismo grupo."""
    restricciones = restricciones if restricciones is not None else pd.DataFrame()
    horarios_apoyo = horarios_apoyo if horarios_apoyo is not None else pd.DataFrame()
    conflictos = []
    propuesta = list(propuesta)
    for indice, item in enumerate(propuesta):
        dia = normalizar_dia(item.get("Dia", ""))
        ini, fin = _hora_minutos(item.get("Inicio")), _hora_minutos(item.get("Fin"))
        grupo = normalizar_texto(item.get("Grupo", ""))
        # Evita también que la propuesta de una sola maestra se cruce consigo misma.
        for anterior in propuesta[:indice]:
            if normalizar_dia(anterior.get("Dia", "")) != dia:
                continue
            a_ini, a_fin = _hora_minutos(anterior.get("Inicio")), _hora_minutos(anterior.get("Fin"))
            mismo_grupo = normalizar_texto(anterior.get("Grupo", "")) == grupo
            if ini < a_fin and a_ini < fin:
                conflictos.append({
                    "Día": dia, "Grupo": item.get("Grupo", ""),
                    "Horario propuesto": f"{item.get('Inicio')}–{item.get('Fin')}",
                    "Actividad que se cruza": (
                        "Otra sesión propuesta para el mismo grupo" if mismo_grupo
                        else "Otra sesión propuesta para la misma maestra"
                    ),
                    "Horario existente": f"{anterior.get('Inicio')}–{anterior.get('Fin')}",
                })
        for _, bloque in restricciones.iterrows() if not restricciones.empty else []:
            if normalizar_dia(bloque.get("Dia", "")) != dia:
                continue
            b_ini, b_fin = _hora_minutos(bloque.get("Inicio")), _hora_minutos(bloque.get("Fin"))
            b_grupo = normalizar_texto(bloque.get("Grupo", ""))
            mismo_grupo_o_general = not b_grupo or b_grupo == grupo
            if mismo_grupo_o_general and ini < b_fin and b_ini < fin:
                conflictos.append({
                    "Día": dia, "Grupo": item.get("Grupo", ""),
                    "Horario propuesto": f"{item.get('Inicio')}–{item.get('Fin')}",
                    "Actividad que se cruza": str(bloque.get("Actividad", "Horario escolar")),
                    "Horario existente": f"{bloque.get('Inicio')}–{bloque.get('Fin')}",
                })
        if not horarios_apoyo.empty:
            peer = horarios_apoyo
            if "Maestra" in peer.columns:
                peer = peer.loc[peer["Maestra"].astype(str).ne(str(item.get("Maestra", "")))]
            for _, bloque in peer.iterrows():
                if normalizar_dia(bloque.get("Dia", "")) != dia:
                    continue
                if normalizar_texto(bloque.get("Grupo", "")) != grupo:
                    continue
                b_ini, b_fin = _hora_minutos(bloque.get("Inicio")), _hora_minutos(bloque.get("Fin"))
                if ini < b_fin and b_ini < fin:
                    conflictos.append({
                        "Día": dia, "Grupo": item.get("Grupo", ""),
                        "Horario propuesto": f"{item.get('Inicio')}–{item.get('Fin')}",
                        "Actividad que se cruza": f"Horario de apoyo de {bloque.get('Maestra', 'otra maestra')}",
                        "Horario existente": f"{bloque.get('Inicio')}–{bloque.get('Fin')}",
                    })
    return pd.DataFrame(conflictos, columns=["Día", "Grupo", "Horario propuesto", "Actividad que se cruza", "Horario existente"])


def proponer_horario(grupos, sesiones_por_grupo, duracion, inicio, fin, restricciones, apoyo_existente,
                     maestra="", modalidad="Grupal", espacio="Aula regular"):
    """Propone una distribución determinista, sin IA, y valida restricciones locales."""
    grupos = [str(g).strip() for g in grupos if str(g).strip()]
    if not grupos:
        raise ValueError("Escribe al menos un grupo, por ejemplo 2A, 3B.")
    ini, limite = _hora_minutos(inicio), _hora_minutos(fin)
    if duracion < 15 or limite <= ini:
        raise ValueError("Verifica la duración y el horario escolar.")
    peticiones = [{"Grupo": grupo} for grupo in grupos for _ in range(int(sesiones_por_grupo))]
    candidates = []
    for dia in DIAS:
        cursor = ini
        while cursor + duracion <= limite:
            candidates.append({"Dia": dia, "Inicio": f"{cursor // 60:02d}:{cursor % 60:02d}",
                               "Fin": f"{(cursor + duracion) // 60:02d}:{(cursor + duracion) % 60:02d}"})
            cursor += duracion + 10
    if not candidates:
        raise ValueError("No hay bloques disponibles con esa duración.")

    # Un primer borrador determinista permite operar sin depender del servicio de IA.
    propuesta = []
    usados = set()
    for peticion in peticiones:
        elegido = None
        for slot in candidates:
            key = (slot["Dia"], slot["Inicio"])
            if key in usados:
                continue
            candidate = {
                **slot, **peticion, "Actividad": "Atención de apoyo", "Maestra": maestra,
                "Modalidad": modalidad, "Espacio": espacio,
            }
            if not detectar_choques([candidate], restricciones, apoyo_existente).empty:
                continue
            elegido = candidate
            usados.add(key)
            break
        if elegido is None:
            raise ValueError(f"No encontré suficientes espacios sin cruces para el grupo {peticion['Grupo']}.")
        propuesta.append(elegido)

    return pd.DataFrame(propuesta), "propuesta automática sin IA; puedes editarla antes de guardar"


def avisar_maestras_apoyo(publicacion_id, especialista, mes, agenda):
    """Crea avisos en la plataforma para maestras asignadas a escuelas publicadas."""
    escuelas = sorted({str(row.get("escuela", row.get("Escuela", ""))).strip()
                       for row in agenda if str(row.get("escuela", row.get("Escuela", ""))).strip()
                       and normalizar_texto(row.get("escuela", row.get("Escuela", ""))) != normalizar_texto("Junta General (Sede)")})
    if not escuelas:
        return 0
    usuarios = repo.usuarios()
    if usuarios is None or usuarios.empty:
        return 0
    ws, headers, existentes = _leer("Avisos_Cronogramas", AVISOS_HEADERS)
    llaves = {(str(row.get("ID_Publicacion", "")), normalizar_texto(row.get("Destinatario", "")), normalizar_texto(row.get("Escuela", ""))) for row in existentes}
    nuevos = []
    now = datetime.now(ZONA).isoformat(timespec="seconds")
    for user in usuarios.to_dict("records"):
        nombre = str(user.get("Nombre", user.get("Nombre_Completo", ""))).strip()
        rol = normalizar_texto(user.get("Rol", ""))
        if not nombre or "APOYO" not in rol or "DIRECTOR" in rol:
            continue
        asignadas = escuelas_asignadas(nombre, str(user.get("Rol", "")))
        permitidas = {normalizar_texto(item) for item in asignadas}
        for escuela in escuelas:
            if normalizar_texto(escuela) not in permitidas:
                continue
            key = (str(publicacion_id), normalizar_texto(nombre), normalizar_texto(escuela))
            if key in llaves:
                continue
            nuevos.append({
                "ID_Aviso": uuid4().hex, "ID_Publicacion": str(publicacion_id), "Fecha": now,
                "Destinatario": nombre, "Escuela": escuela, "Especialista": especialista,
                "Mes": mes, "Resumen": f"Se publicó un cronograma del equipo especialista para {escuela}.",
                "Estado": "PENDIENTE", "Leida_En": "",
            })
            llaves.add(key)
    if nuevos:
        retry_google(lambda: ws.append_rows(
            [[row.get(header, "") for header in headers] for row in nuevos],
            value_input_option="USER_ENTERED",
        ))
        clear_cache("Avisos_Cronogramas")
    return len(nuevos)


def cargar_avisos_apoyo(nombre):
    _, _, rows = _leer("Avisos_Cronogramas", AVISOS_HEADERS)
    return [row for row in rows if normalizar_texto(row.get("Destinatario", "")) == normalizar_texto(nombre)]


def marcar_avisos_leidos(ids_aviso):
    if not ids_aviso:
        return 0
    ws, headers, rows = _leer("Avisos_Cronogramas", AVISOS_HEADERS)
    col_id, col_state, col_date = (headers.index(key) + 1 for key in ("ID_Aviso", "Estado", "Leida_En"))
    ahora = datetime.now(ZONA).isoformat(timespec="seconds")
    selected = {str(value) for value in ids_aviso}
    updates = []
    for row in rows:
        if str(row.get("ID_Aviso", "")) in selected and str(row.get("Estado", "")).upper() == "PENDIENTE":
            updates.extend([
                {"range": f"{_a1(col_state)}{row['_fila']}", "values": [["LEIDA"]]},
                {"range": f"{_a1(col_date)}{row['_fila']}", "values": [[ahora]]},
            ])
    if updates:
        retry_google(lambda: ws.batch_update(updates, value_input_option="USER_ENTERED"))
        clear_cache("Avisos_Cronogramas")
    return len(updates) // 2

