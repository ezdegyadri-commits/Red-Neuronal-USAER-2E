"""Ensayo de migración documental sobre el clúster PostgreSQL temporal."""
import hashlib
import base64
from io import BytesIO
import json
import os
import secrets

from fastapi.testclient import TestClient
from sqlalchemy import insert

from data.database import Usuario, get_engine
from piloto_spa.backend.auth_service import hash_password
from piloto_spa.backend.main import app
from services.epp_modelo import AREAS, vacia
from services.planeacion import HEADERS
from services.planeacion_modelo import crear_plantilla
from tools.migracion_paralela import MARCA
from tools.proyectar_copia_sintetica import proyectar


def probar():
    engine = get_engine()
    password = os.getenv("USAER_DOCUMENTAL_PASSWORD") or secrets.token_urlsafe(24)
    with engine.begin() as db:
        for cuenta, escuela, rol in (("maestra.historia", "esc-sint", "MAESTRA DE APOYO"),
                                     ("otra.historia", "esc-otra", "MAESTRA DE APOYO"),
                                     ("direccion.historia", "", "DIRECTOR")):
            db.execute(insert(Usuario).values(id=cuenta, usuario=cuenta, nombre="Persona ficticia",
                                             password=hash_password(password), rol=rol,
                                             escuelas_permitidas=escuela))
    aid, grupo = "alu-sint", "alu-grupal"
    fecha = "2026-08-20T12:00:00+00:00"
    ciclo = "2026-2027"
    hojas = {
        "Escuelas": [["ID_Escuela", "Nombre_Escuela"], ["esc-sint", "Escuela ficticia"]],
        "Alumnos": [["ID_Alumno", "ID_Escuela", "Nombre_Completo", "Grado", "Grupo", "Tipo_Atencion"],
                    [aid, "esc-sint", "Estudiante ficticio", "3", "A", "Individual"],
                    [grupo, "esc-sint", "Estudiante grupal", "3", "A", "Grupal"]],
        "EPP_Versiones": [["Alumno", "Ciclo", "Parte", "Revision", "Anterior", "Fecha", "Cuenta", "Autor", "Estado", "Contenido"]],
        "Informes": [["ID_Informe", "ID_Alumno", "ID_Escuela", "Cuenta", "Autor", "Titulo", "Ciclo", "Tipo", "Revision", "Fecha", "Avances"],
                     ["informe-historico", aid, "esc-sint", "maestra.historia", "Maestra ficticia", "Informe histórico",
                      ciclo, "seguimiento", "inf-v1", fecha, "Avance ficticio"]],
        "Actas": [["ID_Acta", "ID_Alumno", "ID_Escuela", "Cuenta", "Revision", "Fecha", "Escuela", "Personal",
                   "Tipo_Acta", "Acuerdos", "Seguimiento"],
                  ["acta-historica", aid, "esc-sint", "direccion.historia", "acta-v1", fecha, "Escuela ficticia",
                   "Dirección ficticia", "Acta de reunión", "Acuerdo ficticio", "Seguimiento ficticio"]],
        "Planeaciones_Versiones": [HEADERS],
    }
    from reportlab.pdfgen.canvas import Canvas
    memoria = BytesIO()
    pdf = Canvas(memoria)
    pdf.drawString(72, 720, "Evaluación ficticia")
    pdf.save()
    binario = memoria.getvalue()
    suma_pdf = hashlib.sha256(binario).hexdigest()
    origen_pdf = "a" * 64
    hojas["Documentos_Expediente"] = [[
        "ID_Documento", "Ambito", "ID_Alumnos_JSON", "ID_Escuela", "Estado", "Mime", "Partes",
        "SHA256", "Nombre", "Fecha", "Cuenta", "Ciclo", "Tipo",
    ], [origen_pdf, "individual", json.dumps([aid]), "esc-sint", "VIGENTE", "application/pdf", "1",
        suma_pdf, "evaluacion-ficticia.pdf", fecha, "maestra.historia", ciclo, "Evaluación"]]
    hojas["Archivos_Expediente"] = [["ID_Documento", "Indice", "Total", "Contenido"],
                                  [origen_pdf, "0", "1", base64.b64encode(binario).decode()]]
    def parte(area, revision, anterior, valor):
        hojas["EPP_Versiones"].append([aid, ciclo, area, revision, anterior, fecha, "maestra.historia",
                                      "Maestra ficticia", "BORRADOR", json.dumps(valor)])
    parte("META", "epp-meta", "", {})
    for area in AREAS:
        valor = {**vacia(area), "sintesis": "Hallazgo ficticio"}
        if area == "Aprendizaje":
            valor["evaluaciones"] = [{"id": "eval-ficticia", "texto": "Resultado ficticio", "nombre": "Evaluación",
                                      "entrada": "EXTERNA_REVISADA", "adjunto_id": origen_pdf,
                                      "archivo_sha256": suma_pdf}]
        parte(area, f"v-{area}", "", valor)
    conclusion = {**vacia("Conclusión"), "validada": True, "revisiones_areas": {a: f"v-{a}" for a in AREAS}}
    necesidad = "Fortalecer la lectura de palabras con apoyos visuales"
    conclusion["nee"] = [{"NEE": necesidad}]
    parte("Conclusión", "epp-cierre", "", conclusion)
    hojas["NEE"] = [["ID_NEE", "ID_Alumno", "Ciclo", "Revision_EPP", "Estado", "Texto", "Fundamento",
                     "Profesional", "Cuenta", "Fecha", "Desde", "Hasta"],
                    ["nee-sint", aid, ciclo, "epp-cierre", "CONFIRMADA", necesidad, "Observación ficticia",
                     "Maestra ficticia", "maestra.historia", fecha, "2026-08-01", "2099-08-01"]]
    for alumno, modalidad in ((aid, "individual"), (grupo, "grupal")):
        doc = crear_plantilla("XXIII", [alumno], [{"ID_Alumno": alumno, "ID_Escuela": "esc-sint",
            "Nombre_Completo": "Estudiante ficticio", "Nombre_Escuela": "Escuela ficticia", "Grado": "3", "Grupo": "A",
            "Tipo_Atencion": "Grupal" if modalidad == "grupal" else "Individual"}],
            autor="Maestra ficticia", funcion="Aprendizaje", ciclo_inicio=2026)
        doc.update(id=f"plan-historico-{modalidad}", cuenta="maestra.historia", estado="BORRADOR")
        doc["metadatos"].update(modalidad_planeacion=modalidad)
        for revision, anterior, titulo in (("v1", "", "Plan inicial"), ("v2", "v1", "Plan histórico")):
            doc["metadatos"]["titulo"] = f"{titulo} {modalidad}"
            contenido = json.dumps(doc, ensure_ascii=False)
            suma = hashlib.sha256(contenido.encode()).hexdigest()
            hojas["Planeaciones_Versiones"].append([doc["id"], revision, anterior, fecha, doc["cuenta"],
                "Maestra ficticia", "esc-sint", json.dumps([alumno]), "XXIII", "BORRADOR", "0", "1", suma, contenido])
    copia = {"marca": MARCA, "origen": "documental-ficticio", "pestanas": hojas}
    if url_preparacion := os.getenv("USAER_COPIA_TEST_URL"):
        from copy import deepcopy
        from sqlalchemy import create_engine, text
        from tools.bloques_escuelas import catalogo, preparar_bloque
        from tools.copia_controlada import empaquetar, preparar_bd

        motor = create_engine(url_preparacion, hide_parameters=True)
        try:
            inicial = empaquetar(copia, "esc-sint", fecha, clase="ensayo")
            vista = preparar_bd(motor, inicial)
            assert vista["estados"]["nuevo"] > 10, vista
            with motor.connect() as db:
                assert db.scalar(text("SELECT to_regclass('copia_controlada.lote')")) is None
            assert preparar_bd(motor, inicial, aplicar=True)["estados"] == vista["estados"]
            assert preparar_bd(motor, inicial, aplicar=True)["repetido"]
            siguiente = deepcopy(copia)
            siguiente["pestanas"]["Informes"][1][-1] = "Revisión ficticia de la fuente"
            siguiente["pestanas"]["NEE"].append(siguiente["pestanas"]["NEE"][1][:])
            incremental = empaquetar(siguiente, "esc-sint", "2026-08-21T12:00:00+00:00", clase="ensayo")
            dif = preparar_bd(motor, incremental, aplicar=True)
            assert dif["estados"]["modificado"] == 1 and dif["estados"]["cuarentena"] == 2, dif
            assert dif["ultima_copia_anterior"] == fecha
            with motor.connect() as db:
                assert db.scalar(text("SELECT count(*) FROM copia_controlada.registro WHERE estado='cuarentena'")) == 2
                assert db.scalar(text("SELECT to_regclass('public.alumnos')")) is None
            paquetes = []
            for plantel in catalogo()["USAER-B01"]:
                eid = plantel["id"]
                alumno_bloque = "fic-" + eid
                copia_bloque = {"marca": MARCA, "origen": "bloque-ficticio", "pestanas": {
                    "Escuelas": [["ID_Escuela", "Nombre_Escuela"], [eid, plantel["nombre"]]],
                    "Alumnos": [["ID_Alumno", "ID_Escuela", "Nombre_Completo"],
                                [alumno_bloque, eid, "Estudiante ficticio"]],
                    "Expedientes": [["ID_Expediente", "ID_Alumno"], ["exp-" + eid, alumno_bloque]],
                    "Anexo5_Eventos": [["ID_Evento", "ID_Alumno", "Evento"],
                                      ["ev-" + eid, alumno_bloque, "Evento ficticio"]],
                }}
                paquetes.append(empaquetar(copia_bloque, eid, fecha, clase="ensayo"))
            vista = preparar_bloque(motor, "USAER-B01", paquetes, clase="ensayo")
            bloque = preparar_bloque(motor, "USAER-B01", paquetes, clase="ensayo", aplicar=True)
            assert bloque["estados"] == vista["estados"] == {"nuevo": 16}
            assert bloque["alumnos"] == 4 and not bloque["faltantes"]
            assert sum(e["expedientes_explicitos"] for e in bloque["escuelas"].values()) == 4
            assert preparar_bloque(motor, "USAER-B01", paquetes, clase="ensayo", aplicar=True)["estados"] == {"nuevo": 16}
            for paquete in paquetes:
                operativo = proyectar(engine, paquete["copia"], aplicar=True)
                assert operativo["tablas"]["Alumnos"]["nuevas"] == 1
                assert operativo["tablas"]["Anexo5_Eventos"]["nuevas"] == 1
                assert "Expedientes" in operativo["solo_archivo"]
            az = empaquetar({"marca": MARCA, "origen": "ensayo-quintana-roo", "pestanas": {
                "Escuelas": [["ID_Escuela", "Nombre_Escuela"], ["ESC-008", "Quintana Roo"]],
                "Alumnos": [["ID_Alumno", "ID_Escuela"]],
            }}, "ESC-008", fecha, clase="ensayo")
            assert preparar_bloque(motor, "USAER-B02", [az], clase="ensayo")["estados"] == {"nuevo": 1}
            print("Bloque 1 sintético:", json.dumps({
                "alumnos": bloque["alumnos"], "estados": bloque["estados"], "recursos": bloque["recursos"],
                "ultima_conciliacion": bloque["ultima_conciliacion"],
            }))
        finally:
            motor.dispose()
        print("Copia de una escuela: manifiesto, segunda captura, cuarentena e idempotencia verificados.")
    altas = proyectar(engine, copia, aplicar=True)["tablas"]
    assert {n: altas[n]["nuevas"] for n in ("Actas", "Informes", "EPP_Versiones", "Planeaciones_Versiones")} == {
        "Actas": 1, "Informes": 1, "EPP_Versiones": 1, "Planeaciones_Versiones": 2}, altas
    repetida = proyectar(engine, copia, aplicar=True)["tablas"]
    assert repetida["EPP_Versiones"]["iguales"] == 1 and repetida["Planeaciones_Versiones"]["iguales"] == 2, repetida
    with TestClient(app, base_url="https://127.0.0.1") as cliente:
        headers = {"X-USAER-Client": "browser"}

        def ingresar(usuario):
            cliente.cookies.clear()
            respuesta = cliente.post("/api/auth/login", json={"usuario": usuario, "password": password}, headers=headers)
            assert respuesta.status_code == 200, respuesta.text

        ingresar("maestra.historia")
        informe = cliente.get("/api/informes/informe-historico").json()
        assert informe["avances"] == "Avance ficticio", informe
        cambio = cliente.put("/api/informes/informe-historico", headers=headers,
                             json={**informe, "avances": "Edición docente posterior"})
        assert cambio.status_code == 200, cambio.text
        assert cliente.put("/api/informes/informe-historico", headers=headers, json=informe).status_code == 409
        epp = cliente.get(f"/api/epp/{aid}/anexo").json()
        assert epp["partes"]["Aprendizaje"]["contenido"]["sintesis"] == "Hallazgo ficticio", epp
        assert epp["nee_vigentes"][0]["id"] == "nee-sint", epp
        evaluacion = epp["partes"]["Aprendizaje"]["contenido"]["evaluaciones"][0]
        adjunto = f"/api/expedientes/{aid}/adjuntos/{evaluacion['adjunto_id']}"
        assert cliente.get(adjunto).content == binario
        for modalidad in ("individual", "grupal"):
            ruta = f"/api/planeaciones/plan-historico-{modalidad}"
            assert cliente.get(ruta).json()["metadatos"]["titulo"] == f"Plan histórico {modalidad}"
            assert len(cliente.get(ruta + "/historial").json()) == 2
            assert cliente.get(ruta + "/pdf").content.startswith(b"%PDF")
        for ruta in (f"/api/epp/{aid}/pdf", "/api/informes/informe-historico/pdf"):
            assert cliente.get(ruta).content.startswith(b"%PDF")
        ingresar("otra.historia")
        assert cliente.get("/api/informes/informe-historico").status_code == 404
        assert cliente.get("/api/planeaciones/plan-historico-grupal").status_code == 404
        assert cliente.get(f"/api/epp/{aid}/anexo").status_code == 404
        assert cliente.get(adjunto).status_code == 404
        assert cliente.get("/api/visitas/acta-historica").status_code == 403
        ingresar("direccion.historia")
        assert cliente.get("/api/visitas/acta-historica").json()["acuerdos"] == "Acuerdo ficticio"
        assert cliente.get("/api/visitas/acta-historica/pdf").content.startswith(b"%PDF")
        expediente = cliente.get(f"/api/expedientes/{aid}").json()
        assert {"acta-historica", "informe-historico"} <= {r["id"] for r in expediente["seguimiento"]}
        if url_preparacion:
            for eid in ("ESC-001", "ESC-002", "ESC-003", "ESC-004"):
                assert cliente.get(f"/api/expedientes/fic-{eid}").status_code == 200
        assert proyectar(engine, copia, aplicar=True)["tablas"]["Informes"]["conflictos_preservados"] == 1
        assert cliente.get("/api/informes/informe-historico").json()["avances"] == "Edición docente posterior"
    print("Documentos históricos abiertos, exportados y aislados en PostgreSQL.")
