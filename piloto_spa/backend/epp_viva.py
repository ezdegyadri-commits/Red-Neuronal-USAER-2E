"""Formato vivo de EPP y propuestas sustentadas en evidencia local."""
import base64
import binascii
from copy import deepcopy
from hashlib import sha256
from io import BytesIO
from pathlib import PurePath
import re
from zipfile import BadZipFile, ZipFile

from services.epp_modelo import AREAS, BAP, CONCLUSION, NEE, vacia


ALIAS = dict(zip((*AREAS, "Conclusión"),
                 ("APRENDIZAJE", "PSICOLOGIA", "COMUNICACION", "TRABAJO_SOCIAL", "CONCLUSION")))
MAX_BYTES = 3 * 1024 * 1024
MAX_BASE64 = MAX_BYTES * 4 // 3


def vista_partes(doc):
    """Conserva contenido, revisión y autoría de las estructuras históricas."""
    guardadas = doc.get("partes") or {}
    resultado = {}
    for area, alias in ALIAS.items():
        parte = guardadas.get(area) or guardadas.get(alias) or {}
        if isinstance(parte, str):
            parte = {"sintesis": parte}
        contenido = parte.get("contenido")
        if not isinstance(contenido, dict):
            contenido = parte
        base = vacia(area)
        claves = base["campos"]
        anteriores = contenido.get("campos") or {}
        campos = {k: anteriores.get(k, contenido.get(k, "")) or "" for k in claves}
        base.update(deepcopy(contenido))
        base["campos"] = campos
        if not base.get("instrumentos") and contenido.get("instrumentos_aplicados"):
            base["instrumentos"] = contenido["instrumentos_aplicados"]
        for tabla in ("nee", "bap", "historia", "familia", "evaluaciones"):
            if tabla in base and not isinstance(base[tabla], list):
                base[tabla] = []
        resultado[area] = {
            "contenido": base,
            "autor": parte.get("autor") or parte.get("Autor") or "",
            "cuenta": parte.get("cuenta") or parte.get("Cuenta") or "",
            "revision": parte.get("revision") or parte.get("Revision") or "",
            "fecha": parte.get("fecha") or parte.get("Fecha") or "",
        }
    return resultado


def editables(doc, user):
    if user.director or user.area not in AREAS:
        return []
    partes = vista_partes(doc)
    propias = [user.area] if partes[user.area]["cuenta"] in ("", user.usuario) else []
    meta = doc.get("partes", {}).get("META") or {}
    configuracion = meta.get("contenido", meta)
    coordinacion = configuracion.get("creada_por") or ""
    if user.area == "Aprendizaje" and coordinacion in ("", user.usuario) and propias:
        if partes["Conclusión"]["cuenta"] in ("", user.usuario):
            propias.append("Conclusión")
    return propias


def extraer(nombre, codificado):
    if len(codificado) > MAX_BASE64:
        raise ValueError("El archivo supera 3 MB.")
    try:
        data = base64.b64decode(codificado, validate=True)
    except (ValueError, binascii.Error) as exc:
        raise ValueError("El archivo está incompleto o no es válido.") from exc
    if not data or len(data) > MAX_BYTES:
        raise ValueError("Carga un archivo no vacío de hasta 3 MB.")
    extension = PurePath(nombre).suffix.lower()
    try:
        if extension == ".txt":
            texto = data.decode("utf-8-sig")
        elif extension == ".pdf" and data.startswith(b"%PDF-"):
            import fitz
            with fitz.open(stream=data, filetype="pdf") as pdf:
                if pdf.needs_pass or len(pdf) > 25:
                    raise ValueError("Usa un PDF sin contraseña y de hasta 25 páginas.")
                texto = "\n".join(page.get_text() for page in pdf)
        elif extension == ".docx":
            with ZipFile(BytesIO(data)) as zipdoc:
                miembros = zipdoc.infolist()
                if len(miembros) > 350 or sum(f.file_size for f in miembros) > 16 * MAX_BYTES:
                    raise ValueError("El DOCX supera el límite de procesamiento.")
            from docx import Document
            doc = Document(BytesIO(data))
            lineas = [p.text for p in doc.paragraphs]
            for tabla in doc.tables:
                lineas.extend(" | ".join(c.text for c in fila.cells) for fila in tabla.rows)
            texto = "\n".join(lineas)
        else:
            raise ValueError("Usa un archivo PDF con texto, DOCX o TXT.")
    except (BadZipFile, UnicodeError) as exc:
        raise ValueError("El contenido del archivo no corresponde al formato indicado.") from exc
    except (ImportError, ValueError):
        raise
    except Exception as exc:
        raise ValueError("No se pudo extraer texto de este archivo.") from exc
    texto = texto.strip()
    if not texto or "\x00" in texto:
        raise ValueError("No se encontró texto legible. Si es un escaneo, carga la transcripción.")
    if len(texto) > 48000:
        raise ValueError("El documento supera 48 000 caracteres. Separa el apartado pertinente.")
    return texto, sha256(data).hexdigest()


def propuesta_campo(campo, texto):
    """Selecciona fragmentos pertinentes. El docente revisa la interpretación."""
    palabras = set(re.findall(r"[^\W\d_]{4,}", campo.casefold())) - {"campo", "para", "según"}
    fragmentos = [re.sub(r"\s+", " ", f).strip()
                 for f in re.split(r"\n+|(?<=[.!?])\s+", texto) if len(f.strip()) >= 12]
    if not fragmentos:
        raise ValueError("Agrega hallazgos observados o un archivo con texto legible.")
    ordenados = sorted(enumerate(fragmentos), key=lambda p: (
        -len(palabras & set(re.findall(r"[^\W\d_]+", p[1].casefold()))), p[0]))
    seleccion = [f for _, f in ordenados[:4]]
    return "En el registro consultado se documenta lo siguiente. " + " ".join(seleccion)[:3000]


def propuesta_conclusion(doc):
    partes = vista_partes(doc)
    hallazgos, faltantes = [], []
    nee, bap = [], []
    for area in AREAS:
        p = partes[area]["contenido"]
        textos = [str(v).strip() for k, v in p["campos"].items()
                  if v and not p.get("no_requeridos", {}).get(k) and v != "No se requiere"]
        if p.get("sintesis"):
            textos.insert(0, p["sintesis"])
        if textos:
            estado = "revisado" if p.get("validada") else "pendiente de revisión"
            hallazgos.append(f"{area} ({estado}). " + " ".join(textos)[:1250])
        else:
            faltantes.append(area)
        for t in textos:
            for linea in t.splitlines():
                if re.match(r"^\s*NEE\s*:", linea, re.I):
                    valor = linea.split(":", 1)[1].strip()
                    if valor:
                        nee.append(dict.fromkeys(NEE, "") | {"Aspectos": area, "NEE": valor})
                if re.match(r"^\s*BAP\s*:", linea, re.I):
                    valor = linea.split(":", 1)[1].strip()
                    if valor:
                        bap.append(dict.fromkeys(BAP, "") | {"Tipo de barrera": valor})
    if not hallazgos:
        raise ValueError("Registra al menos un hallazgo antes de generar una propuesta.")
    c = partes["Conclusión"]["contenido"]
    return {"campos": {CONCLUSION[0]: "\n\n".join(hallazgos)}, "faltantes": faltantes,
            "nee": [*c.get("nee", []), *nee], "bap": [*c.get("bap", []), *bap]}
