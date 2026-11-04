"""Sustituye referencias nominales heredadas para la imagen sintética."""
import ast
from pathlib import Path
import re
import sys
import unicodedata

raiz = Path(sys.argv[1]) if len(sys.argv) == 2 else Path("/src")
identidades = set()
titulos = re.compile(r"^(?:Mtra|Mtro|Psic|Lic|LTS)\. (.+)$", re.I)

for archivo, campos in {
    "services/planeacion_firmas.py": {"DIRECTOR_USAER", "DOCENTES_APOYO_POR_ESCUELA",
                                     "DOCENTES_APOYO_ALTERNOS", "ESPECIALISTAS_POR_AREA", "NOMBRES_FORMALES"},
    "services/asignaciones.py": {"ASIGNACIONES_ESPECIALISTAS", "PERSONAL_AUTORIZADO_ALTA",
                                "DIRECTIVO_AUTORIZADO_ALTA"},
    "services/alumnos.py": {"DOCENTES_ICHC_AANZIHO"},
}.items():
    arbol = ast.parse((raiz / archivo).read_text(encoding="utf-8"))
    for nodo in arbol.body:
        if not isinstance(nodo, (ast.Assign, ast.AnnAssign)):
            continue
        destinos = nodo.targets if isinstance(nodo, ast.Assign) else [nodo.target]
        if not any(isinstance(t, ast.Name) and t.id in campos for t in destinos):
            continue
        for valor in ast.walk(nodo.value):
            if isinstance(valor, ast.Constant) and isinstance(valor.value, str):
                nombre = titulos.sub(r"\1", valor.value)
                if len(nombre.split()) >= 3 and all(c.isalpha() or c in " .-" for c in nombre):
                    # Las claves escolares y las categorías siguen siendo las del catálogo.
                    if nombre in {"Gregorio Torres Quintero", "Remigio Aguilar Sosa", "Elvira Parra Ávila",
                                  "Domingo Solís Rodríguez", "TRABAJO SOCIAL"}:
                        continue
                    identidades.add(nombre)

alias = {}
for nombre in sorted(identidades):
    normalizado = "".join(c for c in unicodedata.normalize("NFD", nombre) if not unicodedata.combining(c))
    clave = normalizado.casefold()
    reemplazo = alias.get(clave, f"Personal ficticio {len(alias) + 1:02}")
    alias[clave] = reemplazo
    alias[nombre.casefold()] = reemplazo

patron = re.compile("|".join(re.escape(n) for n in sorted(alias, key=len, reverse=True)), re.I)
correo = re.compile(r"(?<![\w.])[\w.+-]+@[A-Za-z0-9.-]+\.(?:com|mx|net|org)\b", re.I)
secretos = re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----|AIza[\w-]{35}|gh[pousr]_[A-Za-z0-9]{30,}|GOCSPX-[\w-]{20,}")
for ruta in raiz.rglob("*"):
    if not ruta.is_file():
        continue
    rel = ruta.relative_to(raiz).as_posix()
    frontend = ruta.parent == raiz / "piloto_spa/frontend"
    codigo = ruta.suffix == ".py" and rel.startswith(
        ("ai/", "config/", "data/", "documents/", "services/", "utils/", "piloto_spa/backend/")
    )
    if not (codigo or frontend and ruta.suffix in {".js", ".cjs", ".css"} or rel in {
        "requirements.txt", "data/curriculo_sep.json.gz", "piloto_spa/backend/static/index.html",
        "piloto_spa/frontend/package.json", "piloto_spa/frontend/package-lock.json",
        "deploy/oracle/arranque.py", "deploy/oracle/sanear_imagen.py", "deploy/oracle/constraints.txt",
    }):
        raise SystemExit(f"Archivo fuera del contexto sintético: {rel}")
    if ruta.suffix not in {".py", ".html", ".js", ".cjs"} or ruta.name == Path(__file__).name:
        continue
    texto = ruta.read_text(encoding="utf-8-sig")
    limpio = patron.sub(lambda m: alias[m[0].casefold()].upper() if m[0].isupper() else alias[m[0].casefold()], texto)
    limpio = correo.sub("cuenta@example.invalid", limpio)
    if secretos.search(limpio):
        raise SystemExit(f"Posible secreto en {ruta.relative_to(raiz)}")
    if ruta.suffix == ".py":
        ast.parse(limpio, filename=str(ruta))
    if limpio != texto:
        ruta.write_text(limpio, encoding="utf-8")
