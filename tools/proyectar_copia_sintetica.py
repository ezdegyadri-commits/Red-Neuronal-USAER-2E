"""Proyección aditiva del padrón y los anexos tabulares hacia una SPA sintética local."""
from argparse import ArgumentParser
import json
import os
from pathlib import Path
import re
import sys

from sqlalchemy import select, text
from sqlalchemy.engine import make_url

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from data.sincronizacion_pg import DESTINOS, preparar as preparar_tablas
from tools.migracion_paralela import MAX_BYTES, preparar

TABLAS = ("Escuelas", "Alumnos", "Anexo3_Deteccion", "Anexo4_Sugerencias",
          "Anexo5_Eventos", "Anexo7_Derivacion", "Registro_Visitas")


def proyectar(engine, copia, *, aplicar=False):
    _, conciliacion = preparar(copia)
    fuente = copia["pestanas"]
    if any(any(conciliacion[n]["errores"].values()) for n in TABLAS if n in conciliacion):
        raise ValueError("Las pestañas operativas tienen identidades o relaciones sin conciliar.")
    if len(fuente["Escuelas"]) < 2:
        raise ValueError("La proyección requiere un catálogo de escuelas explícito.")
    plan, exclusiones = preparar_tablas({n: fuente[n] for n in TABLAS if n in fuente})
    if exclusiones:
        raise ValueError("La proyección no admite exclusiones automáticas de registros.")
    alumnos_origen = {r["id"] for r in plan["Alumnos"]}
    curps = [r["curp"].strip().upper() for r in plan["Alumnos"] if r.get("curp", "").strip()]
    if len(curps) != len(set(curps)):
        raise ValueError("Hay CURP repetidas en el origen.")
    for nombre in TABLAS[2:-1]:
        if any(r.get("id_alumno") not in alumnos_origen for r in plan.get(nombre, [])):
            raise ValueError(f"{nombre}: se requiere un alumno de origen conciliado.")
    resultado = {"aplicado": aplicar, "solo_archivo": sorted(set(fuente) - set(plan)), "tablas": {}}
    with engine.begin() as db:
        nombre, rol, marca = db.execute(text("""
            SELECT current_database(), current_user, shobj_description(oid, 'pg_database')
            FROM pg_database WHERE datname=current_database()
        """)).one()
        if (not re.fullmatch(r"usaer_spa_test_proyeccion_[a-z0-9_]+", nombre)
                or rol != nombre.replace("usaer_spa_test_", "spa_fixture_", 1)
                or marca != "USAER SPA synthetic only"):
            raise ValueError("El destino no corresponde a la proyección sintética independiente.")
        # Los nombres proceden del catálogo fijo, nunca del archivo.
        if aplicar:
            nombres = ", ".join(DESTINOS[n][0].__tablename__ for n in TABLAS if n in plan)
            db.execute(text(f"LOCK TABLE {nombres} IN SHARE ROW EXCLUSIVE MODE"))
        alumnos_en_conflicto = set()
        for nombre in (n for n in TABLAS if n in plan):
            filas = plan[nombre]
            tabla = DESTINOS[nombre][0].__table__
            existentes = {r["id"]: r for r in db.execute(select(tabla)).mappings()}
            curps_db = {str(r["curp"] or "").strip().upper(): aid for aid, r in existentes.items()
                        if nombre == "Alumnos" and r["curp"]}
            cuenta = {"nuevas": 0, "iguales": 0, "conflictos_preservados": 0}
            for fila in filas:
                actual = existentes.get(fila["id"])
                curp = fila.get("curp", "").strip().upper()
                if (fila.get("id_alumno") in alumnos_en_conflicto
                        or nombre == "Alumnos" and curp and curps_db.get(curp, fila["id"]) != fila["id"]):
                    cuenta["conflictos_preservados"] += 1
                    if nombre == "Alumnos":
                        alumnos_en_conflicto.add(fila["id"])
                elif actual is None:
                    cuenta["nuevas"] += 1
                    if aplicar:
                        db.execute(tabla.insert().values(**fila))
                elif all(str(actual[k] or "") == v for k, v in fila.items()):
                    cuenta["iguales"] += 1
                else:
                    cuenta["conflictos_preservados"] += 1
                    if nombre == "Alumnos":
                        alumnos_en_conflicto.add(fila["id"])
            resultado["tablas"][nombre] = cuenta
    return resultado


def main():
    parser = ArgumentParser(description=__doc__)
    parser.add_argument("archivo", type=Path)
    parser.add_argument("--aplicar", action="store_true")
    args = parser.parse_args()
    if args.archivo.stat().st_size > MAX_BYTES:
        parser.error("La copia supera el límite.")
    url = make_url(os.getenv("USAER_PROYECCION_TEST_URL") or "sqlite://")
    if not re.fullmatch(r"usaer_spa_test_proyeccion_[a-z0-9_]+", url.database or ""):
        parser.error("Configura una base dedicada de proyección sintética.")
    os.environ.update(DATABASE_URL=url.render_as_string(hide_password=False),
                      USAER_SPA_MODE="postgres-synthetic", USAER_SPA_ROLE="owner")
    from data.database import get_engine
    from piloto_spa.backend.main import verificar_base_piloto

    verificar_base_piloto()
    copia = json.loads(args.archivo.read_text(encoding="utf-8-sig"))
    print(json.dumps(proyectar(get_engine(initialize_schema=False), copia, aplicar=args.aplicar),
                     ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
