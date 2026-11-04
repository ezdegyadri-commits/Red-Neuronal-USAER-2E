"""Importa eventos versionados de un XLSX sintético local a PostgreSQL de pruebas."""
import argparse
from datetime import datetime, timezone
import hashlib
from pathlib import Path
import re

from openpyxl import load_workbook
from sqlalchemy import select

from data.database import Alumno, Anexo5Evento, CambioSPA, Usuario, get_session
from piloto_spa.backend.main import verificar_base_piloto
from data.sql_repository import _registrar_cambio_spa

COLUMNAS = ("ID_Evento", "ID_Alumno", "Revision", "Revision_Anterior",
            "Autor", "Fecha", "Fecha_Modificacion", "Evento")


def extraer(archivo):
    if archivo.suffix.lower() != ".xlsx" or archivo.stat().st_size > 2_000_000:
        raise ValueError("Usa un XLSX sintético de hasta 2 MB.")
    libro = load_workbook(archivo, read_only=True, data_only=False, keep_links=False)
    try:
        hoja = libro["EventosVersiones"]
        filas = hoja.iter_rows()
        if tuple(c.value for c in next(filas)) != COLUMNAS:
            raise ValueError("La hoja EventosVersiones no tiene las columnas esperadas.")
        for numero, celdas in enumerate(filas, 2):
            if numero > 10001 or any(c.data_type == "f" for c in celdas):
                raise ValueError(f"Fila {numero}: límite o fórmula no admitida.")
            if all(c.value is None for c in celdas):
                continue
            if len(celdas) != len(COLUMNAS):
                raise ValueError(f"Fila {numero}: número de columnas incorrecto.")
            valores = dict(zip(COLUMNAS, (str(c.value or "").strip() for c in celdas)))
            for campo in ("ID_Evento", "ID_Alumno", "Revision", "Autor"):
                if not re.fullmatch(r"[A-Za-z0-9_.:-]{1,64}", valores[campo]):
                    raise ValueError(f"Fila {numero}: {campo} inválido.")
            fecha = datetime.fromisoformat(valores["Fecha"]).date().isoformat()
            modificacion = datetime.fromisoformat(valores["Fecha_Modificacion"])
            if modificacion.tzinfo is None:
                raise ValueError(f"Fila {numero}: la fecha de modificación requiere zona horaria.")
            evento = valores["Evento"]
            if not evento or len(evento) > 10000:
                raise ValueError(f"Fila {numero}: evento vacío o demasiado extenso.")
            yield valores, fecha, modificacion.astimezone(timezone.utc)
    finally:
        libro.close()


def conciliar(archivo, *, aplicar=False):
    import os
    if os.environ.get("USAER_SPA_MODE") != "postgres-synthetic":
        raise RuntimeError("La carga requiere el perfil PostgreSQL sintético.")
    verificar_base_piloto()
    reporte = {"nuevas": 0, "repetidas": 0, "aplicado": aplicar}
    with get_session(initialize_schema=False) as db:
        for fila, fecha, modificacion in extraer(archivo):
            eid, aid, autor = (fila[k] for k in ("ID_Evento", "ID_Alumno", "Autor"))
            revision, anterior = fila["Revision"], fila["Revision_Anterior"] or None
            alumno = db.get(Alumno, aid)
            cuenta = db.scalar(select(Usuario).where(Usuario.usuario == autor))
            if not alumno or not cuenta:
                raise ValueError("Relación con alumno o cuenta inexistente.")
            if cuenta.rol != "DIRECTOR" and alumno.id_escuela not in {
                e.strip() for e in (cuenta.escuelas_permitidas or "").split(",")
            } and "TODAS" not in (cuenta.escuelas_permitidas or "").split(","):
                raise ValueError("La autoría no pertenece al ámbito del alumno.")
            actual = db.scalar(select(Anexo5Evento).where(Anexo5Evento.id == eid).with_for_update())
            if actual and actual.id_alumno != aid:
                raise ValueError("El evento pertenece a otro alumno.")
            registro = {"revision": revision, "alumno": aid, "campos": {"fecha": fecha, "evento": fila["Evento"]}}
            clave = hashlib.sha256(f"eventos-xlsx|{eid}|{revision}".encode()).hexdigest()[:32]
            anterior_importado = db.get(CambioSPA, clave)
            if anterior_importado:
                import json
                if (json.loads(anterior_importado.contenido) != registro or anterior_importado.autor != autor
                        or anterior_importado.revision_anterior != anterior or anterior_importado.fecha != modificacion):
                    raise ValueError("La fuente cambió una revisión que ya se importó.")
                reporte["repetidas"] += 1
                continue
            ultimo = db.scalar(select(CambioSPA).where(CambioSPA.tipo == "anexo5", CambioSPA.documento_id == eid)
                               .order_by(CambioSPA.fecha.desc(), CambioSPA.id.desc()).limit(1))
            if (ultimo.revision if ultimo else None) != anterior or (actual is not None and not ultimo):
                raise ValueError("La cadena de versiones diverge o el registro existente carece de historial conciliado.")
            if ultimo and modificacion <= ultimo.fecha:
                raise ValueError("La revisión incremental debe tener una fecha posterior.")
            if not actual:
                actual = Anexo5Evento(id=eid, id_alumno=aid, id_escuela=alumno.id_escuela,
                                      escuela=alumno.nombre_escuela, nombre_alumno=alumno.nombre_completo,
                                      grado_grupo=f"{alumno.grado} {alumno.grupo}", especialista=cuenta.nombre, estado="ACTIVO")
                db.add(actual)
            actual.fecha, actual.evento = fecha, fila["Evento"]
            _registrar_cambio_spa(db, "anexo5", eid, registro, autor, anterior,
                                 id_cambio=clave, fecha_cambio=modificacion)
            db.flush()
            reporte["nuevas"] += 1
        db.commit() if aplicar else db.rollback()
    return reporte


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    print(conciliar(args.archivo, aplicar=args.aplicar))
