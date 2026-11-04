"""Proyección conservadora de documentos a las tablas que lee la SPA."""
import base64
from datetime import date, datetime, timezone
import hashlib
import json

from fastapi import HTTPException
from sqlalchemy import func, select

from data.database import (AdjuntoExpedienteSPA, CambioSPA, EPPDoc, InformeEducativoSPA, PlaneacionAlumnoSPA,
                           PlaneacionDoc, PlaneacionGrupoSPA, RegistroVisita, Usuario)
from data.sincronizacion_pg import huella
from services.epp_modelo import AREAS, clave, validar_parte


TABLAS_DOCUMENTOS = {"EPP_Versiones", "Informes", "Actas", "Planeaciones_Versiones"}
CAMPOS_INFORME = ("antecedentes", "avances", "dificultades", "intervenciones", "recomendaciones")


def fecha(valor):
    instante = datetime.fromisoformat(valor)
    if instante.tzinfo is None:
        raise ValueError("La fecha histórica requiere una zona horaria explícita.")
    return instante.astimezone(timezone.utc)


def obligatorio(fila, campo, limite):
    valor = fila.get(campo, "")
    if not valor.strip() or len(valor) > limite:
        raise ValueError(f"Campo histórico inválido: {campo}.")
    return valor


def filas_de(tabla):
    encabezados, *filas = tabla
    return [dict(zip(encabezados, fila)) for fila in filas if any(c.strip() for c in fila)]


def historial(tipo, documento, version, autor, anterior, instante):
    return dict(id=huella(["migracion-historica", tipo, documento, version["revision"]])[:32],
                tipo=tipo, documento_id=documento, autor=autor, revision_anterior=anterior or None,
                revision=version["revision"], fecha=instante, contenido=json.dumps(version, ensure_ascii=False))


def registrar(db, tabla, datos, versiones, *, aplicar):
    """Compara la cabecera y todas las revisiones. Una colisión conserva el destino."""
    cambios = CambioSPA.__table__
    actual = db.execute(select(tabla).where(tabla.c.id == datos["id"])).mappings().one_or_none()
    tipo = versiones[0]["tipo"]
    previas = db.execute(select(cambios).where(
        cambios.c.tipo == tipo, cambios.c.documento_id == datos["id"],
    )).mappings().all()
    if actual is not None or previas:
        por_id = {r["id"]: r for r in previas}
        mismas_versiones = len(previas) == len(versiones) and all(
            v["id"] in por_id and all(por_id[v["id"]][k] == v[k] for k in
                                      ("revision", "revision_anterior", "autor", "contenido", "fecha"))
            for v in versiones
        )
        mismos_campos = actual is not None and all(actual[k] == v for k, v in datos.items()
                                                   if k not in {"creado_en", "actualizado_en"})
        return "iguales" if mismas_versiones and mismos_campos else "conflictos_preservados"
    if aplicar:
        db.execute(tabla.insert().values(**datos))
        db.execute(cambios.insert(), versiones)
    return "nuevas"


def titular_autorizado(db, cuenta, escuela):
    usuarios = Usuario.__table__
    titular = db.execute(select(usuarios).where(usuarios.c.usuario == cuenta)).mappings().one_or_none()
    if not titular or (titular["rol"] != "DIRECTOR" and escuela not in
                       (titular["escuelas_permitidas"] or "").split(",")):
        raise ValueError("La autoría no se puede vincular a una cuenta autorizada del entorno sintético.")
    return titular


def informe(db, fila, alumno):
    documento = obligatorio(fila, "ID_Informe", 64)
    cuenta = obligatorio(fila, "Cuenta", 128)
    escuela = obligatorio(fila, "ID_Escuela", 64)
    autor = obligatorio(fila, "Autor", 128)
    titulo = obligatorio(fila, "Titulo", 255)
    ciclo = obligatorio(fila, "Ciclo", 16)
    inicio, fin = ciclo.split("-")
    if len(inicio) != 4 or len(fin) != 4 or int(fin) != int(inicio) + 1:
        raise ValueError("Ciclo de informe inválido.")
    tipo = fila.get("Tipo", "seguimiento")
    if tipo not in {"seguimiento", "evaluacion", "intervencion", "otro"} or escuela != alumno["id_escuela"]:
        raise ValueError("Tipo de informe o escuela sin conciliar.")
    titular = titular_autorizado(db, cuenta, escuela)
    contenido = {campo: fila.get(campo.capitalize(), "") for campo in CAMPOS_INFORME}
    if any(len(valor) > 20000 for valor in contenido.values()):
        raise ValueError("Informe demasiado extenso.")
    revision = obligatorio(fila, "Revision", 64)
    instante = fecha(fila["Fecha"])
    version = dict(id=documento, alumno_id=alumno["id"], ciclo=ciclo, tipo=tipo, titulo=titulo,
                   autor=autor, revision=revision, actualizado_en=instante.replace(tzinfo=None).isoformat(), **contenido)
    datos = dict(id=documento, id_alumno=alumno["id"], id_escuela=escuela, ciclo=ciclo, tipo=tipo,
                 titulo=titulo, contenido_json=json.dumps(contenido, ensure_ascii=False),
                 autor=autor, id_autor=titular["id"], revision=revision,
                 creado_en=instante.replace(tzinfo=None), actualizado_en=instante.replace(tzinfo=None))
    return datos, [historial("informe", documento, version, cuenta, fila.get("Anterior"), instante)]


def nee_confirmadas(filas, conclusion, alumno, documento, ciclo):
    from services.planeacion_nee import es_bapse, es_diagnostico_puro

    textos = {r.get("NEE", "").strip() for r in conclusion.get("nee", []) if r.get("NEE", "").strip()}
    confirmadas = []
    for fila in filas:
        texto = obligatorio(fila, "Texto", 1200)
        desde, hasta = date.fromisoformat(fila["Desde"]), date.fromisoformat(fila["Hasta"])
        if (fila["Estado"] != "CONFIRMADA" or texto not in textos or desde > hasta
                or es_bapse({"texto": texto}) or es_diagnostico_puro(texto)):
            raise ValueError("NEE histórica sin confirmar o con vigencia inválida.")
        confirmadas.append(dict(id=obligatorio(fila, "ID_NEE", 64), alumno=alumno, documento=documento,
                                 ciclo=ciclo, texto=texto, fundamento=obligatorio(fila, "Fundamento", 2500),
                                 profesional=obligatorio(fila, "Profesional", 128),
                                 cuenta=obligatorio(fila, "Cuenta", 128), fecha=fecha(fila["Fecha"]).isoformat(),
                                 estado="CONFIRMADA", desde=desde.isoformat(), hasta=hasta.isoformat()))
    if not conclusion.get("validada") or len(textos) != len(confirmadas) or textos != {r["texto"] for r in confirmadas}:
        raise ValueError("Las NEE no coinciden con la conclusión validada.")
    return confirmadas


def epp(filas, alumno, necesidades, adjuntos):
    primera = filas[0]
    ciclo = primera["Ciclo"]
    inicio, fin = ciclo.split("-")
    if int(fin) != int(inicio) + 1:
        raise ValueError("Ciclo EPP inválido.")
    documento = clave(alumno["id"], ciclo)
    partes, revisiones, versiones = {}, {}, []
    anexo = {}
    anterior_doc, conocidas = "", set()
    for fila in filas:
        parte = fila["Parte"]
        revision = obligatorio(fila, "Revision", 64)
        if revision in conocidas:
            raise ValueError("Revisión EPP ambigua.")
        conocidas.add(revision)
        if fila.get("Anterior", "") != revisiones.get(parte, ""):
            raise ValueError("Cadena histórica EPP incompleta o en conflicto.")
        instante = fecha(fila["Fecha"])
        cuenta = obligatorio(fila, "Cuenta", 128)
        autor = obligatorio(fila, "Autor", 128)
        estado = obligatorio(fila, "Estado", 32)
        contenido = json.loads(fila["Contenido"])
        if not isinstance(contenido, dict) or parte not in ("META", *AREAS, "Conclusión"):
            raise ValueError("Apartado EPP fuera del formato.")
        if parte == "META":
            partes["META"] = {**contenido, "estado": estado, "autor": autor, "cuenta": cuenta,
                              "revision": revision, "anterior": fila.get("Anterior", ""), "fecha": fila["Fecha"]}
        else:
            anexo[parte] = {"contenido": validar_parte(parte, contenido), "revision": revision,
                            "autor": autor, "cuenta": cuenta, "fecha": fila["Fecha"], "estado": estado,
                            "anterior": fila.get("Anterior", "")}
            for evaluacion in anexo[parte]["contenido"]["evaluaciones"]:
                if evaluacion.get("entrada") == "EXTERNA_REVISADA":
                    vinculo = adjuntos.get(evaluacion.get("adjunto_id"))
                    if not vinculo or vinculo[0] != alumno["id"] or vinculo[1] != evaluacion.get("archivo_sha256"):
                        raise ValueError("Falta el PDF conciliado de la evaluación externa.")
                    evaluacion["adjunto_id"] = vinculo[2]
            if parte == "Conclusión" and (relacionadas := necesidades.get((alumno["id"], ciclo, revision))):
                anexo[parte]["nee_confirmadas"] = nee_confirmadas(
                    relacionadas, anexo[parte]["contenido"], alumno["id"], documento, ciclo,
                )
        meta = {**partes.get("META", {}), "anexo_xvii": anexo}
        version = dict(id=documento, alumno=alumno["id"], ciclo=ciclo, revision=revision,
                       fecha=fila["Fecha"], partes={"META": meta})
        versiones.append(historial("epp", documento, version, cuenta, anterior_doc, instante))
        anterior_doc = revision
        revisiones[parte] = revision
    if "META" not in partes or partes["META"]["estado"] == "ELIMINADO":
        raise ValueError("EPP histórica sin cabecera activa.")
    return dict(id=documento, alumno=alumno["id"], ciclo=ciclo, estado=meta["estado"],
                revision=revision, fecha=version["fecha"], partes_json=json.dumps(version["partes"], ensure_ascii=False),
                actualizado_en=instante.replace(tzinfo=None)), versiones


def acta(fila, alumno):
    documento = obligatorio(fila, "ID_Acta", 64)
    cuenta = obligatorio(fila, "Cuenta", 128)
    revision = obligatorio(fila, "Revision", 64)
    instante = fecha(fila["Fecha"])
    if obligatorio(fila, "ID_Escuela", 64) != alumno["id_escuela"]:
        raise ValueError("Escuela del acta sin conciliar.")
    datos = dict(id=documento, fecha=datetime.fromisoformat(fila["Fecha"]).date().isoformat(),
                 escuela=obligatorio(fila, "Escuela", 255), personal=obligatorio(fila, "Personal", 255),
                 tipo_acta=obligatorio(fila, "Tipo_Acta", 64), lugar=fila.get("Lugar", ""),
                 motivo=fila.get("Motivo", ""), observaciones=fila.get("Observaciones", ""),
                 estatus="GUARDADA")
    if len(datos["lugar"]) > 255:
        raise ValueError("Lugar del acta demasiado extenso.")
    extras = dict(acuerdos=fila.get("Acuerdos", ""), seguimiento=fila.get("Seguimiento", ""),
                  responsable=fila.get("Responsable", ""), alumno_id=alumno["id"])
    version = dict(revision=revision, **datos, **extras)
    datos["evidencia"] = json.dumps(extras, ensure_ascii=False)
    return datos, [historial("acta", documento, version, cuenta, fila.get("Anterior"), instante)]


def planeacion(filas, alumnos):
    from data.sql_repository import actualizar_revisiones_celda
    from piloto_spa.backend.grupal import actualizar_guia
    from services.planeacion import HEADERS, reconstruir
    from services.planeacion_modelo import FORMATOS
    from utils.escolar import grado_canonico, grupo_canonico

    por_revision = {fila["Revision"]: fila for fila in filas}
    docs = reconstruir([HEADERS, *[[fila.get(k, "") for k in HEADERS] for fila in filas]])
    if not docs or len(docs) != len(por_revision):
        raise ValueError("Versiones de planeación incompletas o con SHA inválido.")
    versiones, anterior, alcance = [], "", None
    for doc in docs:
        doc.pop("_orden", None)
        fila = por_revision[doc["revision"]]
        if doc["anterior"] != anterior or doc["formato"] not in FORMATOS:
            raise ValueError("Cadena o formato de planeación incompatible.")
        obligatorio(fila, "Documento", 64)
        obligatorio(fila, "Revision", 64)
        obligatorio(fila, "Autor", 128)
        obligatorio(fila, "Cuenta", 128)
        obligatorio(fila, "Fecha", 32)
        obligatorio(fila, "Estado", 32)
        instante = fecha(fila["Fecha"])
        ids = tuple(sorted(a["ID_Alumno"] for a in doc["datos"]["Alumnos"]))
        if not ids or len(set(ids)) != len(ids) or ids != tuple(sorted(json.loads(fila["Alumnos_JSON"]))):
            raise ValueError("Destinatarios de planeación sin conciliar.")
        if any(a not in alumnos or alumnos[a]["id_escuela"] != fila["Escuela_ID"] for a in ids):
            raise ValueError("La escuela histórica no coincide con el padrón conciliado.")
        if doc["datos"].get("ID_Escuela") != fila["Escuela_ID"]:
            raise ValueError("La escuela interna de la planeación no coincide con su manifiesto.")
        meta = doc["metadatos"]
        modalidad = meta.get("modalidad_planeacion")
        if modalidad not in ("individual", "grupal") or (modalidad == "individual" and len(ids) != 1):
            raise ValueError("Modalidad histórica sin conciliar.")
        ciclo = doc["datos"]["Curso escolar"]
        grupo = None
        if modalidad == "grupal":
            grupos = {(grado_canonico(alumnos[a].get("grado")), grupo_canonico(alumnos[a].get("grupo"))) for a in ids}
            if len(grupos) != 1 or not all(next(iter(grupos))) or doc["formato"] == "XXI":
                raise ValueError("Matrícula histórica grupal sin conciliar.")
            grado, letra = next(iter(grupos))
            if any((grado_canonico(a.get("Grado")), grupo_canonico(a.get("Grupo"))) != (grado, letra)
                   for a in doc["datos"]["Alumnos"]):
                raise ValueError("El grupo histórico difiere de la matrícula conciliada.")
            grupo = (fila["Escuela_ID"], grado, letra, ciclo)
            meta.update(grupo_compartido=True, periodicidad="anual", alcance_grupal={"grado": grado, "grupo": letra})
            actualizar_guia(doc)
            actualizar_revisiones_celda(doc, {})
        else:
            meta.pop("grupo_compartido", None)
        meta["plantilla_spa"] = True
        identidad = (ids, doc["cuenta"], modalidad, fila["Escuela_ID"], ciclo, grupo)
        if alcance is not None and identidad != alcance:
            raise ValueError("La cadena contiene un cambio de destinatarios, autoría o ámbito.")
        alcance = identidad
        versiones.append(historial("planeacion", doc["id"], doc, fila["Autor"], anterior, instante))
        anterior = doc["revision"]
    datos = dict(id=doc["id"], cuenta=doc["cuenta"], formato=doc["formato"], estado=doc["estado"],
                 revision=doc["revision"], guardado_en=doc["guardado_en"],
                 observaciones_director=doc.get("observaciones_director", ""),
                 actualizado_en=instante.replace(tzinfo=None), payload_json=json.dumps(doc, ensure_ascii=False))
    datos.update({f"{k}_json": json.dumps(doc[k], ensure_ascii=False) for k in ("datos", "metadatos", "tablas", "textos")})
    return datos, versiones, ids, grupo


def proyectar_adjuntos(db, fuente, alumnos, *, aplicar):
    from piloto_spa.backend.adjuntos import LIMITE_BYTES, validar_pdf

    tabla = AdjuntoExpedienteSPA.__table__
    partes = {}
    for fila in filas_de(fuente.get("Archivos_Expediente", [[]])):
        partes.setdefault(fila["ID_Documento"], []).append(fila)
    cuenta = dict(nuevas=0, iguales=0, conflictos_preservados=0, no_conciliadas=0)
    vinculos, previstos = {}, {}
    for fila in filas_de(fuente["Documentos_Expediente"]):
        try:
            original = obligatorio(fila, "ID_Documento", 128)
            alumnos_doc = json.loads(fila["ID_Alumnos_JSON"])
            if (fila["Ambito"] != "individual" or fila["Estado"] != "VIGENTE"
                    or fila["Mime"] != "application/pdf" or not isinstance(alumnos_doc, list)
                    or len(alumnos_doc) != 1 or alumnos[alumnos_doc[0]]["id_escuela"] != fila["ID_Escuela"]):
                raise ValueError("Adjunto individual sin conciliar.")
            aid = alumnos_doc[0]
            n = int(fila["Partes"])
            fragmentos = sorted(partes.get(original, []), key=lambda p: int(p["Indice"]))
            if (not 1 <= n <= 234 or len(fragmentos) != n
                    or any(int(p["Indice"]) != i or int(p["Total"]) != n or len(p["Contenido"]) > 30000
                           for i, p in enumerate(fragmentos))):
                raise ValueError("Archivo incompleto.")
            contenido = base64.b64decode("".join(p["Contenido"] for p in fragmentos), validate=True)
            suma = hashlib.sha256(contenido).hexdigest()
            if suma != fila["SHA256"] or len(contenido) > LIMITE_BYTES:
                raise ValueError("Huella o tamaño de PDF inválido.")
            nombre = obligatorio(fila, "Nombre", 120)
            validar_pdf(nombre, contenido)
            instante = fecha(fila["Fecha"])
            autor = obligatorio(fila, "Cuenta", 128)
        except (ValueError, TypeError, KeyError, HTTPException):
            cuenta["no_conciliadas"] += 1
            continue
        ident = original if len(original) <= 32 else huella(["adjunto-historico", original])[:32]
        previo = db.scalar(select(tabla.c.id).where(tabla.c.alumno_id == aid, tabla.c.sha256 == suma))
        if (previo and previo != ident) or (aid, suma) in previstos:
            cuenta["conflictos_preservados"] += 1
            continue
        datos = dict(id=ident, alumno_id=aid, nombre=nombre, bytes=len(contenido), sha256=suma,
                     autor=autor, fecha=instante, contenido=contenido)
        version = dict(id=ident, revision=suma, origen=original, alumno_id=aid, tipo=fila.get("Tipo", ""),
                       ciclo=fila.get("Ciclo", ""), fuente=fila.get("Fuente", ""))
        if not previo:
            total, peso = db.execute(select(func.count(), func.coalesce(func.sum(tabla.c.bytes), 0))
                                     .where(tabla.c.alumno_id == aid)).one()
            simulados = [v for (alumno, _), v in previstos.items() if alumno == aid]
            if total + len(simulados) >= 20 or peso + sum(simulados) + len(contenido) > 25 * 1024 * 1024:
                cuenta["no_conciliadas"] += 1
                continue
        estado = registrar(db, tabla, datos, [historial("adjunto_historico", ident, version, autor, None, instante)],
                           aplicar=aplicar)
        cuenta[estado] += 1
        if estado != "conflictos_preservados":
            vinculos[original] = (aid, suma, ident)
        if not aplicar and estado == "nuevas":
            previstos[aid, suma] = len(contenido)
    return cuenta, vinculos


def proyectar_documentos(db, fuente, alumnos_conciliados, *, aplicar):
    resultado = {}
    adjuntos = {}
    if "Documentos_Expediente" in fuente:
        resultado["Documentos_Expediente"], adjuntos = proyectar_adjuntos(
            db, fuente, alumnos_conciliados, aplicar=aplicar,
        )
    necesidades = {}
    if "NEE" in fuente:
        for fila in filas_de(fuente["NEE"]):
            llave = (fila.get("ID_Alumno"), fila.get("Ciclo"), fila.get("Revision_EPP"))
            necesidades.setdefault(llave, []).append(fila)
    for nombre in sorted(TABLAS_DOCUMENTOS & fuente.keys()):
        cuenta = dict(nuevas=0, iguales=0, conflictos_preservados=0, no_conciliadas=0)
        grupos = {}
        for fila in filas_de(fuente[nombre]):
            if nombre == "EPP_Versiones":
                llave = (fila.get("Alumno"), fila.get("Ciclo"))
            elif nombre == "Planeaciones_Versiones":
                llave = (None, fila.get("Documento"))
            else:
                llave = (fila.get("ID_Alumno"), fila.get("ID_Informe") or fila.get("ID_Acta"))
            grupos.setdefault(llave, []).append(fila)
        for (aid, _), filas in grupos.items():
            alumno = alumnos_conciliados.get(aid)
            if not alumno and nombre != "Planeaciones_Versiones":
                cuenta["no_conciliadas"] += 1
                continue
            ids, grupo = (), None
            try:
                if nombre == "EPP_Versiones":
                    datos, versiones = epp(filas, alumno, necesidades, adjuntos)
                    tabla = EPPDoc.__table__
                    otro = db.scalar(select(tabla.c.id).where(
                        tabla.c.alumno == aid, tabla.c.ciclo == datos["ciclo"], tabla.c.id != datos["id"],
                    ).limit(1))
                    if otro:
                        cuenta["conflictos_preservados"] += 1
                        continue
                elif nombre == "Informes":
                    datos, versiones = informe(db, filas[0], alumno)
                    tabla = InformeEducativoSPA.__table__
                elif nombre == "Actas":
                    datos, versiones = acta(filas[0], alumno)
                    tabla = RegistroVisita.__table__
                else:
                    datos, versiones, ids, grupo = planeacion(filas, alumnos_conciliados)
                    titular_autorizado(db, datos["cuenta"], alumnos_conciliados[ids[0]]["id_escuela"])
                    tabla = PlaneacionDoc.__table__
                    if grupo:
                        grupos_sql = PlaneacionGrupoSPA.__table__
                        existente = db.scalar(select(grupos_sql.c.planeacion_id).where(
                            grupos_sql.c.escuela == grupo[0], grupos_sql.c.grado == grupo[1],
                            grupos_sql.c.grupo == grupo[2], grupos_sql.c.ciclo == grupo[3],
                        ))
                        if existente and existente != datos["id"]:
                            cuenta["conflictos_preservados"] += 1
                            continue
            except (ValueError, TypeError, KeyError, AttributeError, PermissionError):
                cuenta["no_conciliadas"] += 1
                continue
            estado = registrar(db, tabla, datos, versiones, aplicar=aplicar)
            cuenta[estado] += 1
            if aplicar and estado == "nuevas" and ids:
                db.execute(PlaneacionAlumnoSPA.__table__.insert(),
                           [{"planeacion_id": datos["id"], "alumno_id": a} for a in ids])
                if grupo:
                    db.execute(PlaneacionGrupoSPA.__table__.insert().values(
                        escuela=grupo[0], grado=grupo[1], grupo=grupo[2], ciclo=grupo[3], planeacion_id=datos["id"],
                    ))
        resultado[nombre] = cuenta
    return resultado
