"""Mapeos aditivos del expediente explícito y de la responsabilidad escolar."""
from collections import Counter
from datetime import date, datetime
import json
from zoneinfo import ZoneInfo

from sqlalchemy import select, update

from data.database import (AdjuntoExpedienteSPA, Alumno, Anexo3Deteccion, Anexo4Sugerencia, Anexo5Evento,
                           ApoyoAlumnoSPA, EPPDoc, ExpedienteHistoricoSPA, InformeEducativoSPA,
                           PlaneacionAlumnoSPA, RegistroVisita, RelacionHistoricaSPA, Usuario)
from data.sincronizacion_pg import huella
from tools.documentos_historicos import filas_de, obligatorio
from utils.text import normalizar_texto

ICHC = "ESC-002"
TABLAS_B01 = {"Expedientes", "Relaciones_Documentos", "Asignaciones_Apoyo"}
RESPONSABLES = {"CECI", "MARYCRUZ"}


def hoy_local():
    return datetime.now(ZoneInfo("America/Mexico_City")).date().isoformat()


def intervalo(fila):
    desde, hasta = fila.get("Desde", ""), fila.get("Hasta", "")
    for valor in (desde, hasta):
        if valor and date.fromisoformat(valor).isoformat() != valor:
            raise ValueError("Fecha de asignación inválida.")
    if desde and hasta and desde > hasta:
        raise ValueError("Vigencia invertida.")
    return desde, hasta


def asignaciones_revisadas(fuente, alumnos):
    filas = filas_de(fuente.get("Asignaciones_Apoyo", [[]]))
    ids = Counter(f.get("ID_Asignacion") for f in filas)
    cuentas = {r: {f.get("ID_Cuenta") for f in filas if f.get("Responsable") == r} for r in RESPONSABLES}
    revisadas, invalidas, compartidas = [], set(), set()
    for fila in filas:
        aid = fila.get("ID_Alumno", "")
        try:
            responsable = fila["Responsable"]
            ident = obligatorio(fila, "ID_Asignacion", 64)
            cuenta = obligatorio(fila, "ID_Cuenta", 64)
            desde, hasta = intervalo(fila)
            if (responsable not in RESPONSABLES or cuentas[responsable] != {cuenta}
                    or any(cuenta in valores for r, valores in cuentas.items() if r != responsable)
                    or fila.get("ID_Escuela") != ICHC or alumnos.get(aid, {}).get("id_escuela") != ICHC
                    or ids[ident] != 1):
                raise ValueError("Asignación ambigua.")
            revisadas.append(dict(id=ident, alumno_id=aid, escuela_id=ICHC, usuario_id=cuenta,
                                  responsable=responsable, desde=desde, hasta=hasta))
            if normalizar_texto(fila.get("Compartida", "")) == "SI":
                compartidas.add(ident)
        except (ValueError, KeyError):
            invalidas.add(aid)
    por_alumno = {}
    for fila in revisadas:
        por_alumno.setdefault(fila["alumno_id"], []).append(fila)
    for aid, filas in por_alumno.items():
        for i, a in enumerate(filas):
            for b in filas[i + 1:]:
                if (a["responsable"] != b["responsable"]
                        and max(a["desde"], b["desde"]) <= min(a["hasta"] or "9999-12-31", b["hasta"] or "9999-12-31")
                        and not {a["id"], b["id"]} <= compartidas):
                    invalidas.add(aid)
    return revisadas, invalidas


def conteo_ichc(fuente):
    alumnos = {r["ID_Alumno"]: {"id_escuela": ICHC} for r in filas_de(fuente["Alumnos"])
               if r.get("ID_Alumno") and r.get("ID_Escuela") == ICHC}
    revisadas, invalidas = asignaciones_revisadas(fuente, alumnos)
    activas = {}
    hoy = hoy_local()
    for fila in revisadas:
        if (not fila["desde"] or fila["desde"] <= hoy) and (not fila["hasta"] or fila["hasta"] >= hoy):
            activas.setdefault(fila["alumno_id"], set()).add(fila["responsable"])
    conteo = {"ceci": 0, "marycruz": 0, "compartidos": 0, "pendientes": 0}
    for aid in alumnos:
        responsables = activas.get(aid, set())
        grupo = ("pendientes" if aid in invalidas or not responsables else "compartidos"
                 if len(responsables) == 2 else next(iter(responsables)).lower())
        conteo[grupo] += 1
    return conteo


def evidencia_ichc(fuente):
    from services.alumnos import _canonizar_docente_apoyo

    alias = {"PERSONAL FICTICIO 15": "ceci", "PERSONAL FICTICIO 19": "marycruz"}
    evidencia = Counter()
    for fila in filas_de(fuente["Alumnos"]):
        if fila.get("ID_Escuela") == ICHC:
            rol = alias.get(_canonizar_docente_apoyo(fila.get("Maestra de Apoyo", "")), "sin_evidencia_inequivoca")
            evidencia[rol] += 1
    return dict(evidencia)


def compatible(db, tabla, datos, aplicar):
    actual = db.execute(select(tabla).where(tabla.c.id == datos["id"])).mappings().one_or_none()
    if actual is not None:
        return "iguales" if all(actual[k] == v for k, v in datos.items()) else "conflictos_preservados"
    if aplicar:
        db.execute(tabla.insert().values(**datos))
    return "nuevas"


def proyectar_asignaciones(db, fuente, alumnos, aplicar):
    filas, invalidas = asignaciones_revisadas(fuente, alumnos)
    resultados = Counter({"no_conciliadas": len(invalidas)})
    cuentas = {r.id: r for r in db.execute(select(Usuario.id, Usuario.rol, Usuario.escuelas_permitidas))}
    tabla = ApoyoAlumnoSPA.__table__
    rechazados = set(invalidas)
    cierre = {}
    por_alumno = {}
    for fila in filas:
        por_alumno.setdefault(fila["alumno_id"], {})[fila["id"]] = fila
    previas = db.execute(select(tabla).where(tabla.c.alumno_id.in_(por_alumno))).mappings()
    for anterior in previas:
        aid = anterior["alumno_id"]
        siguiente = por_alumno[aid].get(anterior["id"])
        if siguiente is None:
            rechazados.add(aid)
            resultados["conflictos_preservados"] += 1
        elif any(anterior[k] != v for k, v in siguiente.items()):
            if (not anterior["hasta"] and siguiente["hasta"]
                    and all(anterior[k] == v for k, v in siguiente.items() if k != "hasta")):
                cierre[siguiente["id"]] = siguiente["hasta"]
            else:
                rechazados.add(aid)
                resultados["conflictos_preservados"] += 1
    for fila in filas:
        cuenta = cuentas.get(fila["usuario_id"])
        if (not cuenta or ICHC not in (cuenta.escuelas_permitidas or "").split(",")
                or "APOYO" not in normalizar_texto(cuenta.rol)):
            rechazados.add(fila["alumno_id"])
            continue
    for fila in filas:
        if fila["alumno_id"] not in rechazados:
            if fila["id"] in cierre:
                if aplicar:
                    db.execute(update(tabla).where(tabla.c.id == fila["id"]).values(hasta=cierre[fila["id"]]))
                resultados["vigencias_cerradas"] += 1
            else:
                resultados[compatible(db, tabla, fila, aplicar)] += 1
    hoy = hoy_local()
    activos = {f["alumno_id"] for f in filas if (not f["desde"] or f["desde"] <= hoy)
               and (not f["hasta"] or f["hasta"] >= hoy)}
    resultados["pendientes"] = sum(r["id_escuela"] == ICHC and (
        aid in rechazados or aid not in activos) for aid, r in alumnos.items())
    return dict(resultados)


def documento_operativo(db, tipo, documento, ficha, ciclo):
    aid = ficha["alumno_id"]
    if tipo == "Planeaciones_Versiones":
        t = PlaneacionAlumnoSPA.__table__
        return documento if db.scalar(select(t.c.alumno_id).where(
            t.c.planeacion_id == documento, t.c.alumno_id == aid)) else None
    if tipo == "EPP_Versiones":
        t = EPPDoc.__table__
        filas = db.execute(select(t.c.id).where(t.c.alumno == aid,
            (t.c.ciclo == ciclo) if ciclo else (t.c.id == documento))).scalars().all()
        return filas[0] if len(filas) == 1 and documento in (aid, filas[0]) else None
    if tipo == "Actas":
        t = RegistroVisita.__table__
        evidencia = db.scalar(select(t.c.evidencia).where(t.c.id == documento))
        return documento if evidencia and json.loads(evidencia).get("alumno_id") == aid else None
    if tipo == "Documentos_Expediente":
        t = AdjuntoExpedienteSPA.__table__
        ident = documento if len(documento) <= 32 else huella(["adjunto-historico", documento])[:32]
        return ident if db.scalar(select(t.c.alumno_id).where(t.c.id == ident)) == aid else None
    modelo = {"Informes": InformeEducativoSPA, "Anexo3_Deteccion": Anexo3Deteccion,
              "Anexo4_Sugerencias": Anexo4Sugerencia, "Anexo5_Eventos": Anexo5Evento}.get(tipo)
    if not modelo:
        return None
    t = modelo.__table__
    return documento if db.scalar(select(t.c.id_alumno).where(t.c.id == documento)) == aid else None


def proyectar_expedientes(db, fuente, alumnos, aplicar):
    resultado, fichas = {}, {}
    tabla = ExpedienteHistoricoSPA.__table__
    if "Expedientes" in fuente:
        cuenta = Counter()
        filas = filas_de(fuente["Expedientes"])
        repeticiones = Counter(f.get("ID_Expediente") for f in filas)
        for fila in filas:
            try:
                if repeticiones[fila.get("ID_Expediente")] != 1:
                    raise ValueError("Expediente duplicado.")
                alumno = alumnos[fila["ID_Alumno"]]
                escuela = fila.get("ID_Escuela") or alumno["id_escuela"]
                if escuela != alumno["id_escuela"]:
                    raise ValueError("Escuela histórica no conciliada.")
                datos = dict(id=obligatorio(fila, "ID_Expediente", 64), alumno_id=alumno["id"],
                             escuela_id=escuela, estado=obligatorio(fila, "Estatus", 64),
                             apertura=obligatorio(fila, "Fecha_Apertura", 32),
                             actualizado=obligatorio(fila, "Ultima_Actualizacion", 32))
                estado = compatible(db, tabla, datos, aplicar)
                if estado != "conflictos_preservados":
                    fichas[datos["id"]] = datos
                cuenta[estado] += 1
            except (KeyError, ValueError):
                cuenta["no_conciliadas"] += 1
        resultado["Expedientes"] = dict(cuenta)
    if "Relaciones_Documentos" in fuente:
        cuenta = Counter()
        filas = filas_de(fuente["Relaciones_Documentos"])
        repeticiones = Counter(f.get("ID_Relacion") for f in filas)
        for fila in filas:
            try:
                if repeticiones[fila.get("ID_Relacion")] != 1:
                    raise ValueError("Relación duplicada.")
                if fila["Origen_Tipo"] == "Expedientes":
                    ficha = fichas[fila["Origen_ID"]]
                    tipo, doc = fila["Destino_Tipo"], fila["Destino_ID"]
                elif fila["Destino_Tipo"] == "Expedientes":
                    ficha = fichas[fila["Destino_ID"]]
                    tipo, doc = fila["Origen_Tipo"], fila["Origen_ID"]
                else:
                    raise ValueError("Relación sin expediente.")
                destino = documento_operativo(db, tipo, doc, ficha, fila.get("Ciclo"))
                if not destino:
                    raise ValueError("Documento ajeno o pendiente de proyección.")
                datos = dict(id=obligatorio(fila, "ID_Relacion", 64), expediente_id=ficha["id"],
                             tipo_documento=tipo, documento_id=destino, documento_origen_id=doc)
                cuenta[compatible(db, RelacionHistoricaSPA.__table__, datos, aplicar)] += 1
            except (KeyError, ValueError, AttributeError):
                cuenta["no_conciliadas"] += 1
        resultado["Relaciones_Documentos"] = dict(cuenta)
    return resultado
