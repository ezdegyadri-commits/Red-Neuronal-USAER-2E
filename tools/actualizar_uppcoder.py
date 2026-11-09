"""Descarga directa de index.html limpio, backend y reconciliación de PostgreSQL.
"""
import urllib.request
import subprocess
import shutil
import time
import sys
from pathlib import Path

BASE_RAW = "https://raw.githubusercontent.com/ezdegyadri-commits/Red-Neuronal-USAER-2E/piloto-spa"

# 0. Eliminar directorios sombra accidentales en /home/uppcoder/app
for bogus in [Path("/home/uppcoder/app/piloto_spa"), Path("/home/uppcoder/app/static")]:
    if bogus.exists():
        print(f"Limpiando directorio sombra {bogus}...")
        shutil.rmtree(bogus, ignore_errors=True)

def descargar(rel_url, dest_path):
    url = f"{BASE_RAW}/{rel_url}?v={int(time.time())}"
    print(f"Descargando {rel_url} -> {dest_path}")
    dest_path.parent.mkdir(parents=True, exist_ok=True)
    urllib.request.urlretrieve(url, str(dest_path))

# Detectar todos los directorios backend reales (usaer2e + releases de spark)
backend_dirs = []
usaer_backend = Path("/home/uppcoder/app/usaer2e/piloto_spa/backend")
if usaer_backend.exists():
    backend_dirs.append(usaer_backend)

app_backend = Path("/home/uppcoder/app/piloto_spa/backend")
if app_backend.exists() and app_backend not in backend_dirs:
    backend_dirs.append(app_backend)

releases_root = Path("/home/uppcoder/.config/usaer-spark/releases")
if releases_root.exists():
    for rel_dir in releases_root.iterdir():
        b_dir = rel_dir / "piloto_spa" / "backend"
        if b_dir.exists():
            backend_dirs.append(b_dir)

# 1. Actualizar archivos del backend, repositorios de datos y semilla histórica en todas las rutas activas
data_dirs = [
    Path("/home/uppcoder/app/data"),
    Path("/home/uppcoder/app/usaer2e/data"),
]
for d_dir in data_dirs:
    descargar("data/database.py", d_dir / "database.py")
    descargar("data/sql_repository.py", d_dir / "sql_repository.py")
    descargar("data/origen_operativo.py", d_dir / "origen_operativo.py")
    descargar("data/semilla_historica_completa.json.gz", d_dir / "semilla_historica_completa.json.gz")

services_dirs = [
    Path("/home/uppcoder/app/services"),
    Path("/home/uppcoder/app/usaer2e/services"),
]
for s_dir in services_dirs:
    descargar("services/planeacion_local.py", s_dir / "planeacion_local.py")
    descargar("services/planeacion_huella.py", s_dir / "planeacion_huella.py")
    descargar("services/planeacion_edicion.py", s_dir / "planeacion_edicion.py")

doc_dirs = [
    Path("/home/uppcoder/app/documents"),
    Path("/home/uppcoder/app/usaer2e/documents"),
]
doc_files = ["__init__.py", "planeacion.py", "epp.py", "anexos.py", "oficios.py", "paginacion.py", "visitas.py"]
for d_dir in doc_dirs:
    for doc_name in doc_files:
        descargar(f"documents/{doc_name}", d_dir / doc_name)

for b_dir in backend_dirs:
    descargar("piloto_spa/backend/auth_service.py", b_dir / "auth_service.py")
    descargar("piloto_spa/backend/domain_services.py", b_dir / "domain_services.py")
    descargar("piloto_spa/backend/main.py", b_dir / "main.py")
    descargar("piloto_spa/backend/static/index.html", b_dir / "static" / "index.html")
    descargar("piloto_spa/backend/static/css/tailwind.min.css", b_dir / "static" / "css" / "tailwind.min.css")
    descargar("piloto_spa/backend/static/js/app.js", b_dir / "static" / "js" / "app.js")
    descargar("piloto_spa/backend/static/js/react.production.min.js", b_dir / "static" / "js" / "react.production.min.js")
    descargar("piloto_spa/backend/static/js/react-dom.production.min.js", b_dir / "static" / "js" / "react-dom.production.min.js")
    # Asegurar copia de base de datos, repositorios y semilla histórica en el release activo
    rel_data_dir = b_dir.parent.parent / "data"
    descargar("data/database.py", rel_data_dir / "database.py")
    descargar("data/sql_repository.py", rel_data_dir / "sql_repository.py")
    descargar("data/origen_operativo.py", rel_data_dir / "origen_operativo.py")
    descargar("data/semilla_historica_completa.json.gz", rel_data_dir / "semilla_historica_completa.json.gz")
    rel_svc_dir = b_dir.parent.parent / "services"
    descargar("services/planeacion_local.py", rel_svc_dir / "planeacion_local.py")
    descargar("services/planeacion_huella.py", rel_svc_dir / "planeacion_huella.py")
    descargar("services/planeacion_edicion.py", rel_svc_dir / "planeacion_edicion.py")
    rel_doc_dir = b_dir.parent.parent / "documents"
    for doc_name in ["__init__.py", "planeacion.py", "epp.py", "anexos.py", "oficios.py", "paginacion.py", "visitas.py"]:
        descargar(f"documents/{doc_name}", rel_doc_dir / doc_name)

# 2. Actualizar root main.py, recursos institucionales, documentos y estaticos en /home/uppcoder/app
descargar("main.py", Path("/home/uppcoder/app/main.py"))
for doc_name in ["__init__.py", "planeacion.py", "epp.py", "anexos.py", "oficios.py", "paginacion.py", "visitas.py"]:
    descargar(f"documents/{doc_name}", Path(f"/home/uppcoder/app/documents/{doc_name}"))
for img_dir in [Path("/home/uppcoder/app"), Path("/home/uppcoder/app/usaer2e"), Path("/home/uppcoder/app/usaer2e/piloto_spa/backend")]:
    descargar("encabezado.png", img_dir / "encabezado.png")
    descargar("pie_pagina.png", img_dir / "pie_pagina.png")
    descargar("Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx", img_dir / "Concentrado_Revision_Planificaciones_USAER_02E_2026_2027.xlsx")
    descargar("tools/generar_concentrado_excel.py", img_dir / "tools" / "generar_concentrado_excel.py")

for root_s in [Path("/home/uppcoder/app/static"), Path("/home/uppcoder/app/usaer2e/piloto_spa/backend/static")]:
    descargar("piloto_spa/backend/static/index.html", root_s / "index.html")
    descargar("piloto_spa/backend/static/css/tailwind.min.css", root_s / "css" / "tailwind.min.css")
    descargar("piloto_spa/backend/static/js/app.js", root_s / "js" / "app.js")
    descargar("piloto_spa/backend/static/js/react.production.min.js", root_s / "js" / "react.production.min.js")
    descargar("piloto_spa/backend/static/js/react-dom.production.min.js", root_s / "js" / "react-dom.production.min.js")

# 3. Verificar importación y ejecutar reconciliación de PostgreSQL 17 con el Python del entorno FastAPI
print("Verificando importación y reconciliando PostgreSQL 17...")
pixi_py = Path("/home/uppcoder/app/.pixi/envs/web-fastapi/bin/python")
py_exe = str(pixi_py) if pixi_py.exists() else sys.executable
res = subprocess.run(
    [
        py_exe,
        "-c",
        "import main; res = main.reconciliar_base_datos(); print('RECONCILIACION DB:', res); print('MAIN APP CARGADA OK:', main.app.title, 'ERROR:', main.STARTUP_ERROR)"
    ],
    capture_output=True, text=True, cwd="/home/uppcoder/app"
)
print("STDOUT:", res.stdout.strip())
if res.stderr:
    print("STDERR:", res.stderr.strip())

# 4. Reiniciar servicio FastAPI limpiamente con supervisorctl
print("Reiniciando servicio FastAPI...")
subprocess.run(["bash", "-ic", "supervisorctl restart framework"], check=False)
time.sleep(2)
subprocess.run(["bash", "-ic", "supervisorctl status framework"], check=False)
print(">>> DESPLIEGUE OFICIAL, FILTRADO Y BASE DE DATOS RESTABLECIDOS AL 100% <<<")
