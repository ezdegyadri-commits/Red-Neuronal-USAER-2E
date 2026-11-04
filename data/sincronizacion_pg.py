"""Copia verificable y aditiva del libro central; no contiene escrituras a Google."""
from collections import Counter
from datetime import datetime, timezone
import hashlib, json, re
from sqlalchemy import Column, String, Integer, DateTime, JSON, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import declarative_base
from data import database as db

Base = declarative_base()
J = JSON().with_variant(JSONB(), "postgresql")

class Copia(Base):
    __tablename__ = "sincronizacion_copias"
    id = Column(String(64), primary_key=True)
    origen = Column(String(128), nullable=False)
    iniciado_en = Column(DateTime(timezone=True), nullable=False)
    verificado_en = Column(DateTime(timezone=True))
    estado = Column(String(32), nullable=False)
    manifiesto = Column(J, nullable=False)

class Pestana(Base):
    __tablename__ = "sincronizacion_pestanas"
    copia = Column(String(64), primary_key=True)
    nombre = Column(String(256), primary_key=True)
    sha256 = Column(String(64), nullable=False)
    filas = Column(Integer, nullable=False)
    valores = Column(J, nullable=False)

class Integridad(RuntimeError):
    pass

# Destinos operativos preexistentes. No se cambia el identificador del origen.
DESTINOS = {
    "Alumnos": (db.Alumno, "ID_Alumno"),
    "Escuelas": (db.Escuela, "ID_Escuela"),
    "Personal": (db.Personal, "ID_Personal"),
    "Asignaciones": (db.Asignacion, "ID_Asignacion"),
    "Usuarios": (db.Usuario, "ID_Usuario"),
    "Anexo3_Deteccion": (db.Anexo3Deteccion, "ID_Anexo3"),
    "Anexo4_Sugerencias": (db.Anexo4Sugerencia, "ID_Anexo4"),
    "Anexo5_Eventos": (db.Anexo5Evento, "ID_Evento"),
    "Anexo7_Derivacion": (db.Anexo7Derivacion, "ID_Anexo7"),
    "Registro_Visitas": (db.RegistroVisita, "ID_Visita"),
    "Oficios_Comision": (db.OficioComision, "ID_Oficio"),
    "Configuracion_Oficios": (db.ConfiguracionOficio, "ID_Configuracion"),
    "Docentes_Regulares": (db.DocenteRegular, "ID_Registro"),
}

def huella(value):
    return hashlib.sha256(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()).hexdigest()

def registros(values):
    if not values:
        return []
    used = Counter(); headers = []
    for i, cell in enumerate(values[0]):
        name = str(cell).strip() or f"Columna_{i+1}"
        used[name] += 1
        headers.append(name if used[name] == 1 else f"{name}_{used[name]}")
    rows = []
    for row in values[1:]:
        if any(str(v).strip() for v in row):
            if any(str(v).strip() for v in row[len(headers):]):
                raise Integridad("Hay celdas con datos fuera de los encabezados; la copia original se conserva pero no se truncará el mapeo.")
            rows.append(dict(zip(headers, (list(row)+[""]*len(headers))[:len(headers)])))
    return rows

def manifiesto(snapshot):
    return {name: {"sha256": huella(values), "filas": len(registros(values))} for name, values in sorted(snapshot.items())}

def preparar(snapshot):
    result = {}; excluded = 0
    for name, (model, id_key) in DESTINOS.items():
        if name not in snapshot: continue
        values = snapshot[name]; rows = registros(values); prepared = {}; originales = {}
        if name == "Escuelas" and not rows:
            from config.settings import ESCUELAS_USAER
            rows = [{"ID_Escuela": ident, "Nombre_Escuela": label} for label, ident in ESCUELAS_USAER.items()]
        for row in rows:
            ident = str(row.get(id_key, ""))
            # Exclusión ya autorizada: comprobar otra vez que sigue vacía.
            if name == "Alumnos" and ident == "ALU-276":
                meaningful = {k: v for k, v in row.items() if k != id_key and str(v).strip() and not (k in {"Afrodescendiente", "Migrante", "Lengua_Indigena_Mayahablante"} and str(v).casefold() in {"no", "false", "0"})}
                if meaningful:
                    raise Integridad("La fila antes vacía ahora contiene datos; no se puede excluir automáticamente.")
                excluded += 1
                continue
            if not ident:
                raise Integridad(f"Falta identidad estable en {name}; no se generarán identificadores nuevos.")
            canonical = {"id": ident}
            for key, value in row.items():
                attr = "maestra_apoyo" if key == "Maestra de Apoyo" else re.sub(r"[^a-z0-9]+", "_", key.lower()).strip("_")
                if attr in model.__table__.columns and attr not in {"id", "creado_en", "actualizado_en"}:
                    col = model.__table__.columns[attr]
                    value = str(value)
                    if isinstance(col.type, String) and col.type.length and len(value) > col.type.length:
                        raise Integridad(f"El campo {name}.{key} tiene {len(value)} caracteres y el destino admite {col.type.length}; no se truncará.")
                    canonical[attr] = value
            if ident in originales and originales[ident] != row:
                raise Integridad(f"Identificador repetido con contenido diferente en {name}.")
            prepared[ident] = canonical
            originales[ident] = row
        if name == "Usuarios":
            usernames = [r.get("usuario", "") for r in prepared.values()]
            if any(not u for u in usernames) or len(usernames) != len(set(usernames)):
                raise Integridad("El catálogo de usuarios tiene identidades ambiguas.")
            if any(not all(r.get(k) for k in ("password", "nombre", "rol")) for r in prepared.values()):
                raise Integridad("El catálogo de usuarios está incompleto.")
        result[name] = list(prepared.values())
    return result, excluded

def crear_esquema(connection):
    Base.metadata.create_all(connection)
    db.Base.metadata.create_all(connection, tables=[m.__table__ for m, _ in DESTINOS.values()])

def importar(session, snapshot, origen, *, test_fail=False):
    """Una transacción externa abarca copia, destinos, validación y commit.

    En conflicto se detiene todo: no elimina ni actualiza capturas PostgreSQL.
    Se conserva la posición de cada fila y cada celda, incluso duplicados/vacías.
    """
    plan, excluded = preparar(snapshot); manifest = manifiesto(snapshot)
    ident = huella({"origen": origen, "manifiesto": manifest})
    copia = session.get(Copia, ident)
    if copia is None:
        copia = Copia(id=ident, origen=origen, iniciado_en=datetime.now(timezone.utc), estado="COPIANDO", manifiesto=manifest)
        session.add(copia)
    report = {}
    for name, values in snapshot.items():
        key = (ident, name); old = session.get(Pestana, key)
        if old is not None:
            if old.sha256 != huella(values) or huella(old.valores) != huella(values):
                raise Integridad("La copia conservada difiere del origen; se detuvo la operación.")
        else:
            session.add(Pestana(copia=ident, nombre=name, sha256=huella(values), filas=manifest[name]["filas"], valores=values))
        report[name] = {"origen": manifest[name]["filas"], "copia_pg": manifest[name]["filas"]}
    for name, rows in plan.items():
        model = DESTINOS[name][0]
        existing = {r.id: r for r in session.scalars(select(model))}; new = []
        for row in rows:
            old = existing.get(row["id"])
            if old is not None:
                if any(str(getattr(old, key) or "") != value for key, value in row.items()):
                    raise Integridad(f"Hay una captura distinta en PostgreSQL para {name}; se preservan ambas fuentes sin sobrescribir.")
            else:
                new.append(row)
        for start in range(0, len(new), 100):
            session.execute(model.__table__.insert(), new[start:start+100])
        session.flush()
        current = {r.id: r for r in session.scalars(select(model))}
        for row in rows:
            if any(str(getattr(current[row["id"]], key) or "") != value for key, value in row.items()):
                raise Integridad(f"Falló la comprobación de contenido en {name}.")
        report[name].update(identidades_repetidas_conservadas_en_copia=max(0, len(registros(snapshot[name]))-len(rows)-(excluded if name == "Alumnos" else 0)), destino_operativo=model.__tablename__, coincidentes=len(rows), insertados=len(new), total_pg=len(current), solo_pg=len(set(current)-{r["id"] for r in rows}))
    session.flush()
    for name, values in snapshot.items():
        item = session.get(Pestana, (ident, name))
        session.refresh(item)
        if item.sha256 != huella(values) or huella(item.valores) != huella(values) or item.filas != len(registros(values)):
            raise Integridad(f"Falló la lectura de verificación de {name}.")
    if test_fail:
        raise Integridad("Fallo simulado antes del commit.")
    copia.estado = "COPIA_VERIFICADA"; copia.verificado_en = datetime.now(timezone.utc)
    return {"copia": ident, "pestanas": report, "fila_vacia_excluida_del_padron": excluded, "google_sheets_escrito": False, "conexion_streamlit_cambiada": False}
