"""Anexo XVII y catálogo de NEE confirmadas para el piloto SQL."""
from copy import deepcopy
from datetime import date, datetime, timezone
import uuid

from fastapi import HTTPException

from services.epp_modelo import AREAS, conclusion_vigente, pendientes, vacia, validar_parte
from services.planeacion_nee import es_bapse, es_diagnostico_puro


def anexo_epp(epp):
    meta = epp["partes"].get("META") or {}
    return {
        "id": epp["id"], "alumno": epp["alumno"], "ciclo": epp["ciclo"], "revision": epp["revision"],
        "partes": {area: deepcopy(meta.get("anexo_xvii", {}).get(area, {"contenido": vacia(area)}))
                   for area in (*AREAS, "Conclusión")},
    }


def editar_anexo(epp, area, valor, revision, user, nee, *, actualizar_externa=False):
    if revision != epp["revision"]:
        raise HTTPException(409, "La EPP cambió. Reabre el ciclo antes de guardar.")
    if area not in (*AREAS, "Conclusión") or (not user.director and area != user.area):
        raise HTTPException(403, "Esta sección corresponde a otra función.")
    anexo = anexo_epp(epp)
    try:
        contenido = validar_parte(area, deepcopy(valor))
    except (ValueError, PermissionError, TypeError) as exc:
        raise HTTPException(422, str(exc)) from exc
    contenido.pop("revisiones_areas", None)
    fecha = datetime.now(timezone.utc).isoformat()
    anterior = anexo["partes"][area]
    if not actualizar_externa:
        externas = [ev for ev in contenido["evaluaciones"] if ev.get("entrada") == "EXTERNA_REVISADA"]
        previas = [ev for ev in anterior["contenido"].get("evaluaciones", []) if ev.get("entrada") == "EXTERNA_REVISADA"]
        if externas != previas:
            raise HTTPException(422, "Edita las evaluaciones externas desde el vínculo con su PDF.")
    anexo["partes"][area] = {"contenido": contenido, "autor": user.nombre, "cuenta": user.usuario,
                            "fecha": fecha, "revision": uuid.uuid4().hex}
    if area == "Conclusión":
        if contenido["validada"]:
            faltantes = pendientes(anexo)
            if faltantes:
                raise HTTPException(422, " ".join(faltantes))
            textos = [str(row.get("NEE", "")).strip() for row in contenido["nee"] if str(row.get("NEE", "")).strip()]
            if len(textos) != len(set(textos)) or {r.texto.strip() for r in nee} != set(textos):
                raise HTTPException(422, "Registra fundamento y vigencia para cada NEE de la conclusión.")
            if len(nee) != len(textos):
                raise HTTPException(422, "Cada NEE requiere un único registro.")
            anteriores = {r["texto"]: r for r in anterior.get("nee_confirmadas", [])}
            registros = []
            for r in nee:
                texto = r.texto.strip()
                if es_bapse({"texto": texto}) or es_diagnostico_puro(texto):
                    raise HTTPException(422, "Una barrera o diagnóstico no equivale a una NEE.")
                if not r.fundamento.strip() or r.hasta < r.desde:
                    raise HTTPException(422, "Indica fundamento documental y vigencia válida.")
                previo = anteriores.get(texto, {})
                registros.append({"id": previo.get("id") or uuid.uuid4().hex, "alumno": epp["alumno"],
                                  "documento": epp["id"], "ciclo": epp["ciclo"], "texto": texto,
                                  "fundamento": r.fundamento.strip(), "profesional": user.nombre,
                                  "cuenta": user.usuario, "fecha": fecha, "estado": "CONFIRMADA",
                                  "desde": r.desde.isoformat(), "hasta": r.hasta.isoformat()})
            anexo["partes"][area]["nee_confirmadas"] = registros
            contenido["revisiones_areas"] = {a: anexo["partes"][a]["revision"] for a in AREAS}
    epp["partes"].setdefault("META", {})["anexo_xvii"] = anexo["partes"]
    return epp


def nee_vigentes(epp, hoy=None):
    anexo = anexo_epp(epp)
    if not conclusion_vigente(anexo):
        return []
    hoy = (hoy or date.today()).isoformat()
    return [r for r in anexo["partes"]["Conclusión"].get("nee_confirmadas", [])
            if r["desde"] <= hoy <= r["hasta"]]
