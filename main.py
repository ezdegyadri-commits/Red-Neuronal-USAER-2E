"""Modulo main:app para USAER 2E 2.0 en Uppcoder."""
import os
import sys
import json
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://ezdegyadri:pass@zja3x8j3-postgresql-17:5432/usaer_2e_2_0"

# Asegurar todas las rutas base en sys.path
raiz_usaer2e = Path(__file__).resolve().parent / "usaer2e"
raiz_app = Path(__file__).resolve().parent

for r in [raiz_usaer2e, raiz_app]:
    if str(r) not in sys.path:
        sys.path.insert(0, str(r))

# 1. Configurar deploy de forma tolerante
try:
    from deploy.uppcoder import cargar_spark, configurar
    cargar_spark()
    configurar()
except Exception as e:
    pass

# 2. Cargar auth_service y FastAPI app
try:
    from piloto_spa.backend.auth_service import SessionUser, emitir_token_sesion, USUARIOS_CANONICOS, autenticar_usuario
    import piloto_spa.backend.auth_service as auth_svc
    from piloto_spa.backend.main import app
    import piloto_spa.backend.main as main_mod

    # Unificar autenticación institucional
    main_mod.autenticar_usuario = auth_svc.autenticar_usuario
except Exception as exc:
    print(f"Error crítico cargando backend: {exc}")
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    app = FastAPI(title="USAER 2E 2.0 Fallback")
    @app.get("/")
    def fallback_root():
        return HTMLResponse(f"<h1>USAER 2E 2.0</h1><p>Iniciando servicio... ({exc})</p>")

def reconciliar_base_datos():
    """Garantiza la correspondencia canónica de alumnos, escuelas y maestras de apoyo."""
    try:
        from data.database import get_session, Alumno, Usuario, Escuela, Base, get_engine
        engine = get_engine()
        Base.metadata.create_all(engine)
        with get_session() as s:
            # 1. Asegurar usuarios oficiales
            for u_acc, u_info in USUARIOS_CANONICOS.items():
                u = s.query(Usuario).filter_by(usuario=u_acc).first()
                pwd_principal = u_info["passwords"][0]
                if not u:
                    s.add(Usuario(
                        id=u_info["id"],
                        nombre=u_info["nombre"],
                        usuario=u_acc,
                        password=pwd_principal,
                        rol=u_info["rol"],
                        escuelas_permitidas=",".join(u_info["escuelas"])
                    ))
                else:
                    u.nombre = u_info["nombre"]
                    u.password = pwd_principal
                    u.rol = u_info["rol"]
                    u.escuelas_permitidas = ",".join(u_info["escuelas"])

            # 2. Reconciliar escuelas y alumnos por nombre_escuela
            alumnos = s.query(Alumno).all()
            for alu in alumnos:
                nom_esc = str(alu.nombre_escuela or "").strip().upper()
                if "CARMONA" in nom_esc:
                    alu.id_escuela = "ESC-001"
                    alu.nombre_escuela = "Damián Carmona"
                    alu.maestra_apoyo = "Mtra. Cindy Mayanín Burgos González"
                elif "ICHCAAN" in nom_esc:
                    alu.id_escuela = "ESC-002"
                    alu.nombre_escuela = "Ichcaanziho"
                    grado_limpio = str(alu.grado or "").strip().replace("o.", "").replace("°", "")
                    if grado_limpio in ("1", "2", "3") or alu.id in ("ALU-089", "ALU-099", "ALU-106"):
                        alu.maestra_apoyo = "Mtra. Marycruz Caamal Coral"
                    else:
                        alu.maestra_apoyo = "Mtra. María Cecilia Solís Vázquez"
                elif "TORRES" in nom_esc:
                    alu.id_escuela = "ESC-003"
                    alu.nombre_escuela = "Gregorio Torres Quintero"
                    alu.maestra_apoyo = "Mtra. Dolores Eugenia Cortázar Navarrete"
                elif "REMIGIO" in nom_esc:
                    alu.id_escuela = "ESC-004"
                    alu.nombre_escuela = "Remigio Aguilar Sosa"
                    alu.maestra_apoyo = "Mtra. Dianely de Sugeidy Caamal Tamay"
                elif "ELVIRA" in nom_esc or "PARRA" in nom_esc:
                    alu.id_escuela = "ESC-005"
                    alu.nombre_escuela = "Elvira Parra Ávila"
                    alu.maestra_apoyo = "Mtro. Luis Jorge García Herrera"
                elif "SARRADO" in nom_esc:
                    alu.id_escuela = "ESC-006"
                    alu.nombre_escuela = "Manuel Sarrado"
                    alu.maestra_apoyo = "Mtra. María del Rosario Pérez Vitorin"
                elif "DOMINGO" in nom_esc or "SOLIS" in nom_esc or "SOLÍS" in nom_esc:
                    alu.id_escuela = "ESC-007"
                    alu.nombre_escuela = "Domingo Solís Rodríguez"
                    alu.maestra_apoyo = "Mtra. Zuemmy del Carmen Pérez Basto"
                elif "QUINTANA" in nom_esc:
                    alu.id_escuela = "ESC-008"
                    alu.nombre_escuela = "Quintana Roo"
                    alu.maestra_apoyo = "Mtro. Pedro Manuel Torres May"

            s.commit()
            print(">>> Reconciliación de base de datos relacional PostgreSQL completada exitosamente <<<")
    except Exception as exc:
        print(f"Aviso reconciliación DB: {exc}")

# Reconciliación no bloqueante en startup
@app.on_event("startup")
def startup_reconciliacion():
    try:
        reconciliar_base_datos()
    except Exception as e:
        print(f"Aviso startup DB: {e}")

@app.get("/api/diag")
def diag():
    try:
        from data.database import get_session, Usuario, Alumno, Escuela
        with get_session() as s:
            return {
                "status": "OK",
                "usuarios": s.query(Usuario).count(),
                "alumnos": s.query(Alumno).count(),
                "escuelas": s.query(Escuela).count(),
            }
    except Exception as e:
        return {"status": "ERROR_DB", "detalle": str(e)}
