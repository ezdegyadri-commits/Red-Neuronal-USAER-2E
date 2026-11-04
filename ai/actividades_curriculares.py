"""Contrato optativo para un futuro proveedor de actividades basadas en el catálogo público."""

from collections.abc import Callable
import json
import os
import re

from pydantic import BaseModel, ConfigDict, Field

from services.curriculo import catalogo


class ActividadCurricular(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)

    actividad: str = Field(min_length=1, max_length=2400)
    apoyos: str = Field(min_length=1, max_length=1200)
    recursos: str = Field(min_length=1, max_length=1200)
    evaluacion: str = Field(min_length=1, max_length=1200)


def sugerir_actividad_publica(
    pda_id: str, proveedor: Callable[[dict], dict], *, autorizado: bool = False,
) -> ActividadCurricular:
    """Solo acepta un identificador oficial y envía campos recuperados del catálogo público."""
    if not autorizado:
        raise PermissionError("El uso del proveedor externo requiere autorización explícita.")
    pda = next((fila for fila in catalogo()["registros"] if fila["id"] == pda_id), None)
    if pda is None:
        raise ValueError("El PDA no pertenece al catálogo oficial.")
    solicitud = {k: pda[k] for k in ("grado", "campo", "contenido", "pda")}
    return ActividadCurricular.model_validate(proveedor(solicitud))


def sugerir_con_gemini(pda_id: str, *, autorizado: bool = False) -> ActividadCurricular:
    """Adaptador optativo. Recibe exclusivamente un ID del catálogo público."""
    if not autorizado or os.getenv("USAER_IA_CURRICULAR_HABILITADA") != "1":
        raise PermissionError("La generación externa requiere habilitación y autorización explícitas.")
    clave = os.getenv("USAER_IA_GEMINI_API_KEY", "")
    modelo = os.getenv("USAER_IA_GEMINI_MODELO", "")
    if not clave or not re.fullmatch(r"gemini-[a-zA-Z0-9.-]{1,80}", modelo):
        raise ValueError("Configura la clave institucional y un modelo Gemini autorizado.")

    def proveedor(solicitud):
        from ai.documento_json import generar

        campos = ("actividad", "apoyos", "recursos", "evaluacion")
        esquema = {"type": "object", "required": list(campos),
                   "properties": {campo: {"type": "string"} for campo in campos}}
        prompt = ("Sugiere una actividad curricular general para revisión docente. "
                  "Incluye apoyos, recursos y evaluación. No atribuyas observaciones a un estudiante. "
                  "Utiliza únicamente este referente público de la SEP:\n"
                  + json.dumps(solicitud, ensure_ascii=False))
        return generar(prompt, esquema, lambda datos: ActividadCurricular.model_validate(datos).model_dump(),
                       {"gemini": clave, "modelos": [modelo]}, max_tokens=1400)

    return sugerir_actividad_publica(pda_id, proveedor, autorizado=True)
