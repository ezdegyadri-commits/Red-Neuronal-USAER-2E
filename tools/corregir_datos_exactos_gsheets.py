"""Script Maestro de Corrección Relacional y Restauración 100% Fidedigna.
Fuente de la Verdad: Google Sheets (Base_Datos_USAER_2E)
ID: 15hEvBOkaUvUFvTPx38yn8D_O6zWpkDm6ReiQbNK3ewc

Corrige:
1. Escuelas oficiales (Zona 001) con sus CCTs canónicos.
2. Cuentas de Usuarios institucionales (USR-001 a USR-015) y permisos de cluster.
3. 263 Alumnos canónicos: ID, Escuela, CCT, Maestra de Apoyo, Grado, Grupo, Condición.
4. Anulación controlada de registros ficticios/dispersos fuera del padrón canónico.
5. Sincronización de semilla_historica_completa.json.gz.
"""
import gzip
import json
import logging
import os
from pathlib import Path
import sys

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from sqlalchemy.orm import Session
from data.database import get_engine, Alumno, Escuela, Usuario, Personal
from piloto_spa.backend.auth_service import hash_password

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("correccion_gsheets")

# 1. Catálogo Canónico de Escuelas (Zona 001, Mérida)
ESCUELAS_CANONICAS = {
    "ESC-001": {"cct": "31DPR0414P", "nombre": "Damián Carmona", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-002": {"cct": "31DPR0232G", "nombre": "Ichcaanziho", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-003": {"cct": "31DPR0466V", "nombre": "Gregorio Torres Quintero", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-004": {"cct": "31DPR0711P", "nombre": "Remigio Aguilar Sosa", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-005": {"cct": "31EPR0039A", "nombre": "Elvira Parra Ávila", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-006": {"cct": "31EPR0040Q", "nombre": "Manuel Sarrado", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-007": {"cct": "31EPR0075F", "nombre": "Domingo Solís Rodríguez", "nivel": "Primaria", "turno": "Matutino"},
    "ESC-008": {"cct": "31EPR0092W", "nombre": "Quintana Roo", "nivel": "Primaria", "turno": "Matutino"},
}

# 2. Catálogo Canónico de Maestras de Apoyo Titulares por Escuela
MAESTRAS_TITULARES = {
    "ESC-001": "Mtra. Cindy Mayanín Burgos González",
    "ESC-003": "Mtra. Dolores Eugenia Cortázar Navarrete",
    "ESC-004": "Mtra. Dianely de Sugeidy Caamal Tamay",
    "ESC-005": "Mtro. Luis Jorge García Herrera",
    "ESC-006": "Mtra. María del Rosario Pérez Vitorin",
    "ESC-007": "Mtra. Zuemmy del Carmen Pérez Basto",
    "ESC-008": "Mtro. Pedro Manuel Torres May",
}

def normalizar_grado(g: str) -> str:
    s = str(g or "").strip().replace("°", "").replace("o.", "").replace("º", "").strip()
    return s if s in ("1", "2", "3", "4", "5", "6") else (s or "1")

def ejecutar_correccion():
    snapshot_path = Path(ROOT_DIR) / "data" / "gsheet_alumnos_snapshot.json"
    if not snapshot_path.exists():
        raise FileNotFoundError(f"No se encontró el snapshot canónico en {snapshot_path}")

    with open(snapshot_path, encoding="utf-8") as f:
        alumnos_gsheet = json.load(f)

    logger.info("Cargados %d alumnos desde el snapshot de Google Sheets.", len(alumnos_gsheet))

    snapshot_usr_path = Path(ROOT_DIR) / "data" / "gsheet_usuarios_snapshot.json"
    usuarios_gsheet = []
    if snapshot_usr_path.exists():
        with open(snapshot_usr_path, encoding="utf-8") as f:
            usuarios_gsheet = json.load(f)

    engine = get_engine()
    reporte = {
        "escuelas_actualizadas": 0,
        "usuarios_actualizados": 0,
        "alumnos_actualizados": 0,
        "alumnos_desactivados_ficticios": 0,
        "detalle_por_escuela": {},
        "cambios_maestras": 0,
        "cambios_escuelas": 0,
        "cambios_cct": 0,
    }

    with Session(engine) as session:
        # A. CORRECCIÓN DE ESCUELAS
        logger.info("A. Actualizando catálogo de Escuelas con CCTs canónicos...")
        for eid, info in ESCUELAS_CANONICAS.items():
            esc = session.query(Escuela).filter_by(id=eid).first()
            if not esc:
                esc = Escuela(id=eid, cct=info["cct"], nombre_escuela=info["nombre"], nivel=info["nivel"], turno=info["turno"])
                session.add(esc)
                reporte["escuelas_actualizadas"] += 1
            else:
                cambio = False
                if esc.cct != info["cct"]:
                    esc.cct = info["cct"]
                    cambio = True
                if esc.nombre_escuela != info["nombre"]:
                    esc.nombre_escuela = info["nombre"]
                    cambio = True
                if esc.nivel != info["nivel"]:
                    esc.nivel = info["nivel"]
                    cambio = True
                if esc.turno != info["turno"]:
                    esc.turno = info["turno"]
                    cambio = True
                if cambio:
                    reporte["escuelas_actualizadas"] += 1

        # Eliminar escuelas de prueba
        for esc_test in session.query(Escuela).filter(Escuela.id.in_(["ESC-01", "ESC-02"])).all():
            session.delete(esc_test)

        session.commit()
        logger.info("Escuelas verificadas y actualizadas: %d", reporte["escuelas_actualizadas"])

        # B. CORRECCIÓN DE USUARIOS INSTITUCIONALES
        logger.info("B. Actualizando usuarios con RBAC exacto de Google Sheets...")
        for u_data in usuarios_gsheet:
            uid = u_data.get("ID_Usuario", "").strip()
            nom = u_data.get("Nombre", "").strip()
            usu = u_data.get("Usuario", "").strip()
            pwd = u_data.get("Password", "").strip()
            rol = u_data.get("Rol", "").strip().upper()
            esc = u_data.get("Escuelas_Permitidas", "").strip()

            if not usu:
                continue

            u = session.query(Usuario).filter_by(usuario=usu).first()
            pwd_h = hash_password(pwd) if not pwd.startswith("pbkdf2:") else pwd
            if not u:
                session.add(Usuario(id=uid or f"USR-{usu}", nombre=nom, usuario=usu, password=pwd_h, rol=rol, escuelas_permitidas=esc))
                reporte["usuarios_actualizados"] += 1
            else:
                cambio = False
                if u.nombre != nom:
                    u.nombre = nom
                    cambio = True
                if u.rol != rol:
                    u.rol = rol
                    cambio = True
                if u.escuelas_permitidas != esc:
                    u.escuelas_permitidas = esc
                    cambio = True
                if u.id != uid and uid:
                    u.id = uid
                    cambio = True
                if cambio:
                    reporte["usuarios_actualizados"] += 1

        session.commit()
        logger.info("Usuarios institucionales verificados: %d", reporte["usuarios_actualizados"])

        # C. CORRECCIÓN DE ALUMNOS (REFLEJO EXACTO DE GOOGLE SHEETS)
        logger.info("C. Ejecutando reconciliación y UPDATEs exactos en Alumnos...")
        canonical_ids = set()

        for a_data in alumnos_gsheet:
            aid = a_data.get("ID_Alumno", "").strip()
            nom_comp = a_data.get("Nombre_Completo", "").strip()
            if not aid or not nom_comp:
                continue

            canonical_ids.add(aid)

            # Resolver Escuela Canónica
            raw_esc = a_data.get("ID_Escuela", "").strip()
            raw_nom_esc = a_data.get("Nombre_Escuela", "").strip()
            raw_cct = a_data.get("CCT_Escuela", "").strip()

            if raw_esc == "MANUEL SARRADO" or "SARRADO" in raw_nom_esc.upper() or raw_cct == "31EPR0040Q":
                eid = "ESC-006"
            elif raw_esc.startswith("ESC-"):
                eid = raw_esc
            else:
                eid = "ESC-001"

            esc_meta = ESCUELAS_CANONICAS.get(eid, ESCUELAS_CANONICAS["ESC-001"])
            cct = esc_meta["cct"]
            nombre_escuela = esc_meta["nombre"]
            turno = esc_meta["turno"]

            # Resolver Maestra de Apoyo
            raw_maestra = a_data.get("Maestra de Apoyo", "").strip()
            grado_canon = normalizar_grado(a_data.get("Grado", "1"))
            grupo_canon = str(a_data.get("Grupo", "A") or "A").strip()

            if eid == "ESC-002":
                # Ichcaanziho: Marycruz Caamal Coral o María Cecilia Solís Vázquez
                if "CECILIA" in raw_maestra.upper() or "SOLIS" in raw_maestra.upper() or "SOLÍS" in raw_maestra.upper():
                    maestra = "Mtra. María Cecilia Solís Vázquez"
                elif "MARYCRUZ" in raw_maestra.upper() or "CAAMAL" in raw_maestra.upper():
                    maestra = "Mtra. Marycruz Caamal Coral"
                else:
                    # Distribución canónica por grado si venía en blanco
                    maestra = "Mtra. Marycruz Caamal Coral" if grado_canon in ("1", "2", "3") else "Mtra. María Cecilia Solís Vázquez"
            else:
                # Escuela con maestra titular única
                maestra = MAESTRAS_TITULARES.get(eid, MAESTRAS_TITULARES["ESC-001"])

            curp = a_data.get("CURP", "").strip()
            condicion = a_data.get("Condicion_Discapacidad", "").strip()
            tipo_atencion = a_data.get("Tipo_Atencion", "Grupal").strip() or "Grupal"
            edad = a_data.get("Edad_1_Septiembre", "").strip()
            sexo = "Hombre" if str(a_data.get("Sexo", "")).strip().upper() in ("H", "HOMBRE") else "Mujer"
            situacion = a_data.get("Situacion_Alumno", "ACTIVO").strip()

            # Buscar o crear Alumno en SQL
            alu = session.query(Alumno).filter_by(id=aid).first()
            if not alu:
                alu = Alumno(
                    id=aid,
                    nombre_completo=nom_comp,
                    curp=curp,
                    edad_1_septiembre=edad,
                    sexo=sexo,
                    situacion_alumno=situacion,
                    nivel_educativo="Primaria",
                    grado=grado_canon,
                    grupo=grupo_canon,
                    id_escuela=eid,
                    maestra_apoyo=maestra,
                    condicion_discapacidad=condicion,
                    estatus="ACTIVO",
                    tipo_atencion=tipo_atencion,
                    nombre_escuela=nombre_escuela,
                    turno_escuela=turno,
                    cct_escuela=cct,
                    direccion_escuela=a_data.get("Direccion_Escuela", ""),
                    localidad_escuela=a_data.get("Localidad_Escuela", "Mérida"),
                    municipio_escuela=a_data.get("Municipio_Escuela", "Mérida"),
                )
                session.add(alu)
                reporte["alumnos_actualizados"] += 1
            else:
                cambio = False
                if alu.nombre_completo != nom_comp:
                    alu.nombre_completo = nom_comp
                    cambio = True
                if alu.curp != curp:
                    alu.curp = curp
                    cambio = True
                if alu.id_escuela != eid:
                    reporte["cambios_escuelas"] += 1
                    alu.id_escuela = eid
                    cambio = True
                if alu.cct_escuela != cct:
                    reporte["cambios_cct"] += 1
                    alu.cct_escuela = cct
                    cambio = True
                if alu.nombre_escuela != nombre_escuela:
                    alu.nombre_escuela = nombre_escuela
                    cambio = True
                if alu.turno_escuela != turno:
                    alu.turno_escuela = turno
                    cambio = True
                if alu.maestra_apoyo != maestra:
                    reporte["cambios_maestras"] += 1
                    alu.maestra_apoyo = maestra
                    cambio = True
                if alu.grado != grado_canon:
                    alu.grado = grado_canon
                    cambio = True
                if alu.grupo != grupo_canon:
                    alu.grupo = grupo_canon
                    cambio = True
                if alu.condicion_discapacidad != condicion:
                    alu.condicion_discapacidad = condicion
                    cambio = True
                if alu.estatus != "ACTIVO":
                    alu.estatus = "ACTIVO"
                    cambio = True
                if alu.tipo_atencion != tipo_atencion:
                    alu.tipo_atencion = tipo_atencion
                    cambio = True
                if alu.edad_1_septiembre != edad:
                    alu.edad_1_septiembre = edad
                    cambio = True
                if alu.sexo != sexo:
                    alu.sexo = sexo
                    cambio = True

                if cambio:
                    reporte["alumnos_actualizados"] += 1

            reporte["detalle_por_escuela"].setdefault(eid, 0)
            reporte["detalle_por_escuela"][eid] += 1

        # D. ANULAR REGISTROS FICTICIOS O DISPERSOS QUE NO ESTÁN EN EL PADRÓN CANÓNICO
        logger.info("D. Desactivando registros ficticios o duplicados fuera de la fuente canónica...")
        extra_alumnos = session.query(Alumno).filter(
            Alumno.id.notin_(list(canonical_ids))
        ).all()

        for extra in extra_alumnos:
            extra.estatus = "ANULADO_MIGRACION"
            extra.id_escuela = ""
            extra.maestra_apoyo = ""
            reporte["alumnos_desactivados_ficticios"] += 1

        session.commit()
        logger.info("Total alumnos actualizados en base canónica: %d", reporte["alumnos_actualizados"])
        logger.info("Total registros ficticios anulados: %d", reporte["alumnos_desactivados_ficticios"])

    # E. ACTUALIZAR SEMILLA HISTÓRICA COMPLETA PARA DESPLIEGUES Y PERSISTENCIA CENTRAL
    logger.info("E. Sincronizando data/semilla_historica_completa.json.gz...")
    actualizar_semilla_historica(canonical_ids)

    return reporte

def actualizar_semilla_historica(canonical_ids):
    semilla_path = Path(ROOT_DIR) / "data" / "semilla_historica_completa.json.gz"
    engine = get_engine()
    
    with Session(engine) as s:
        alumnos_db = s.query(Alumno).filter(Alumno.id.in_(list(canonical_ids))).all()
        escuelas_db = s.query(Escuela).all()
        usuarios_db = s.query(Usuario).all()
        personal_db = s.query(Personal).all()

        alumnos_rows = []
        for a in alumnos_db:
            alumnos_rows.append({
                "ID_Alumno": a.id,
                "Nombre_Completo": a.nombre_completo,
                "CURP": a.curp,
                "Grado": a.grado,
                "Grupo": a.grupo,
                "ID_Escuela": a.id_escuela,
                "Maestra de Apoyo": a.maestra_apoyo,
                "Condicion_Discapacidad": a.condicion_discapacidad,
                "Estatus": a.estatus,
                "Tipo_Atencion": a.tipo_atencion,
                "Edad_1_Septiembre": a.edad_1_septiembre,
                "Sexo": a.sexo,
                "Situacion_Alumno": a.situacion_alumno,
                "Nivel_Educativo": a.nivel_educativo,
                "Nombre_Escuela": a.nombre_escuela,
                "Turno_Escuela": a.turno_escuela,
                "CCT_Escuela": a.cct_escuela,
                "Direccion_Escuela": a.direccion_escuela,
                "Localidad_Escuela": a.localidad_escuela,
                "Municipio_Escuela": a.municipio_escuela,
            })

    # Cargar semilla existente y actualizar la clave "Alumnos" y "Escuelas"
    if semilla_path.exists():
        with gzip.open(semilla_path, "rt", encoding="utf-8") as gf:
            semilla_data = json.load(gf)
    else:
        semilla_data = {}

    semilla_data["Alumnos"] = alumnos_rows
    semilla_data["Escuelas"] = [
        {"ID_Escuela": e.id, "CCT": e.cct, "Nombre_Escuela": e.nombre_escuela, "Nivel": e.nivel, "Turno": e.turno}
        for e in escuelas_db
    ]

    with gzip.open(semilla_path, "wt", encoding="utf-8") as gf:
        json.dump(semilla_data, gf, ensure_ascii=False)

    logger.info("semilla_historica_completa.json.gz actualizada exitosamente.")

if __name__ == "__main__":
    rep = ejecutar_correccion()
    print("\n" + "="*50)
    print("REPORTE DE CORRECCIÓN DE PRECISIÓN DE DATOS:")
    print("="*50)
    print(json.dumps(rep, ensure_ascii=False, indent=2))

