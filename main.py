"""Modulo main:app para USAER 2E 2.0 en Uppcoder."""
import os
import sys
import shutil
from pathlib import Path

os.environ["DATABASE_URL"] = "postgresql://ezdegyadri:pass@zja3x8j3-postgresql-17:5432/usaer_2e_2_0"

# Shim ligero de streamlit para el entorno FastAPI puro (web-fastapi) donde streamlit no está instalado
try:
    import streamlit as _st
except ImportError:
    import types as _types
    _st = _types.ModuleType("streamlit")
    def _noop_cache(func=None, **kwargs):
        if callable(func):
            func.clear = getattr(func, "clear", lambda: None)
            return func
        def _decorator(f):
            f.clear = getattr(f, "clear", lambda: None)
            return f
        return _decorator
    _st.cache_data = _noop_cache
    _st.cache_resource = _noop_cache
    _st.secrets = {}
    _st.session_state = {}
    sys.modules["streamlit"] = _st

# Eliminar cualquier directorio parcial piloto_spa en /home/uppcoder/app que pueda sombrear a /home/uppcoder/app/usaer2e/piloto_spa
raiz_app = Path(__file__).resolve().parent
raiz_usaer2e = raiz_app / "usaer2e"
if raiz_usaer2e.exists():
    sombra = raiz_app / "piloto_spa"
    if sombra.exists() and not (sombra / "backend" / "auth_service.py").exists():
        shutil.rmtree(sombra, ignore_errors=True)
    if str(raiz_usaer2e) not in sys.path:
        sys.path.insert(0, str(raiz_usaer2e))
elif str(raiz_app) not in sys.path:
    sys.path.insert(0, str(raiz_app))

# 1. Configurar deploy de forma tolerante
try:
    from deploy.uppcoder import cargar_spark, configurar
    cargar_spark()
    configurar()
except Exception as e:
    print(f"Aviso en deploy.uppcoder: {e}")

STARTUP_ERROR = None

# 2. Cargar auth_service y FastAPI app
try:
    from piloto_spa.backend.main import app
    import piloto_spa.backend.main as main_mod
    import piloto_spa.backend.auth_service as auth_svc
    from piloto_spa.backend.auth_service import SessionUser, emitir_token_sesion, USUARIOS_CANONICOS, autenticar_usuario

    # Unificar autenticación institucional
    main_mod.autenticar_usuario = auth_svc.autenticar_usuario
except Exception as exc:
    import traceback
    STARTUP_ERROR = f"{exc}\n{traceback.format_exc()}"
    print(f"Error crítico cargando backend: {STARTUP_ERROR}")
    from fastapi import FastAPI
    from fastapi.responses import HTMLResponse
    app = FastAPI(title="USAER 2E 2.0 Fallback")

    @app.get("/")
    def fallback_root():
        return HTMLResponse(f"<h1>USAER 2E 2.0</h1><pre>{STARTUP_ERROR}</pre>")


def reconciliar_base_datos():
    """Sincroniza e hidrata el 100% de la información histórica desde semilla_historica_completa.json.gz."""
    try:
        from piloto_spa.backend.main import reconciliar_base_datos as _rec
        return _rec()
    except Exception as exc:
        print(f"Aviso reconciliación DB: {exc}")
        return {"error": str(exc)}


@app.on_event("startup")
def startup_reconciliacion():
    try:
        reconciliar_base_datos()
    except Exception as e:
        print(f"Aviso startup DB: {e}")



@app.get("/favicon.ico", include_in_schema=False)
def favicon_root():
    from fastapi import Response, status
    return Response(status_code=status.HTTP_204_NO_CONTENT)

@app.get("/api/diag")
def diag():
    try:
        import os
        from data.database import get_session, Usuario, Alumno, Escuela
        xlsx_cands = [
            str(Path(p) / "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx")
            for p in ["/home/uppcoder/app", "/home/uppcoder/app/usaer2e", "/home/uppcoder/app/usaer2e/piloto_spa/backend", str(Path(__file__).resolve().parent)]
        ]
        xlsx_found = [p for p in xlsx_cands if Path(p).exists()]
        with get_session() as s:
            return {
                "status": "OK",
                "startup_error": STARTUP_ERROR,
                "usuarios": s.query(Usuario).count(),
                "alumnos": s.query(Alumno).count(),
                "escuelas": s.query(Escuela).count(),
                "xlsx_found": xlsx_found,
                "xlsx_cands": xlsx_cands,
                "cwd": os.getcwd(),
                "file": __file__,
            }
    except Exception as e:
        return {"status": "ERROR_DB", "startup_error": STARTUP_ERROR, "detalle": str(e)}
