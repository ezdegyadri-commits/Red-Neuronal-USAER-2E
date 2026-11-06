"""Script de inicialización y siembra de base de datos aislada para pruebas de USAER 2E 2.0.

Crea registros sintéticos completos en SQLite/PostgreSQL sin tocar ninguna hoja de producción.
Garantiza que todos los modelos de SQLAlchemy tengan datos relacionales consistentes para
probar autenticación, expedientes, EPP, planeaciones, anexos y estadísticas.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timezone
from pathlib import Path

ROOT_DIR = str(Path(__file__).resolve().parents[1])
if ROOT_DIR not in sys.path:
    sys.path.insert(0, ROOT_DIR)

from data.database import (
    Base,
    get_engine,
    get_session,
    Alumno,
    Escuela,
    Personal,
    Asignacion,
    Usuario,
    Anexo3Deteccion,
    Anexo4Sugerencia,
    Anexo5Evento,
    Anexo7Derivacion,
    RegistroVisita,
    OficioComision,
    ConfiguracionOficio,
    DocenteRegular,
    PlaneacionDoc,
    EPPDoc,
)
from piloto_spa.backend.auth_service import hash_password

def sembrar_datos_sinteticos():
    engine = get_engine(initialize_schema=True)
    Base.metadata.create_all(engine)

    with get_session() as session:
        # 1. ESCUELAS (8 Oficiales Zona 001)
        escuelas_datos = [
            ("ESC-001", "31DPR0001A", "Damián Carmona", "Primaria", "Matutino"),
            ("ESC-002", "31DPR0002Z", "Ichcaanziho", "Primaria", "Matutino"),
            ("ESC-003", "31DPR0003Y", "Gregorio Torres Quintero", "Primaria", "Matutino"),
            ("ESC-004", "31DPR0004X", "Remigio Aguilar Sosa", "Primaria", "Matutino"),
            ("ESC-005", "31DPR0005W", "Elvira Parra Ávila", "Primaria", "Matutino"),
            ("ESC-006", "31DPR0006V", "Manuel Sarrado", "Primaria", "Matutino"),
            ("ESC-007", "31DPR0007U", "Domingo Solís Rodríguez", "Primaria", "Matutino"),
            ("ESC-008", "31DPR0008T", "Quintana Roo", "Primaria", "Matutino"),
        ]
        for eid, cct, nom, niv, tur in escuelas_datos:
            if not session.query(Escuela).filter_by(id=eid).first():
                session.add(Escuela(id=eid, cct=cct, nombre_escuela=nom, nivel=niv, turno=tur))

        # 2. USUARIOS Y PERSONAL (RBAC Real con contraseñas seguras y hash PBKDF2)
        usuarios_datos = [
            ("usr-dir-001", "Psic. Edgar Adrián Yam Briceño MD", "edgar", "Usaer2E!Dir#2026", "DIRECTOR", "TODAS"),
            ("usr-doc-001", "Mtra. Cindy Mayanín Burgos González", "cindy.burgos", "Usaer2E!Cindy#2026", "MAESTRA DE APOYO", "ESC-001,ESC-003"),
            ("usr-doc-002", "Mtra. Andrea Gómez Tun", "andrea.gomez", "Usaer2E!Andrea#2026", "MAESTRA DE APOYO", "ESC-002,ESC-004"),
            ("usr-psi-001", "Mtra. Laura Elena Pech Cauich", "laura.pech", "Usaer2E!Laura#2026", "PSICOLOGÍA", "TODAS"),
            ("usr-com-001", "Mtra. Mariana Solís Ceballos", "mariana.solis", "Usaer2E!Mariana#2026", "COMUNICACIÓN", "TODAS"),
            ("usr-ts-001", "Lic. Roberto Méndez Canché", "roberto.mendez", "Usaer2E!Roberto#2026", "TRABAJO SOCIAL", "TODAS"),
        ]
        for uid, nom, usu, pwd, rol, esc in usuarios_datos:
            pwd_hash = hash_password(pwd)
            u = session.query(Usuario).filter_by(usuario=usu).first()
            if not u:
                session.add(Usuario(id=uid, nombre=nom, usuario=usu, password=pwd_hash, rol=rol, escuelas_permitidas=esc))
            else:
                u.password = pwd_hash
                u.rol = rol
                u.escuelas_permitidas = esc

            p = session.query(Personal).filter_by(id=uid).first()
            if not p:
                session.add(Personal(id=uid, nombre_completo=nom, rol=rol, email=f"{usu}@usaer2e.edu.mx", telefono="9991234567"))

        # 3. ALUMNOS SINTÉTICOS ENRIQUECIDOS
        alumnos_datos = [
            ("ALU-001", "Jesús Emmanuel Chan Burgos", "CABJ160512MYNRRN01", "8", "Hombre", "INSCRITO", "Primaria", "2", "A", "ESC-001", "Mtra. Cindy Mayanín Burgos González", "TDAH", "ACTIVO", "Atención Focalizada", "Damián Carmona", "31DPR0001A", "Matutino"),
            ("ALU-002", "Sofía Valentina Morales Pech", "MOPS150824MYNRRN02", "9", "Mujer", "INSCRITO", "Primaria", "3", "B", "ESC-001", "Mtra. Cindy Mayanín Burgos González", "Autismo (TEA)", "ACTIVO", "Acompañamiento Continuo", "Damián Carmona", "31DPR0001A", "Matutino"),
            ("ALU-003", "Rodrigo Alejandro Canul May", "CAMR141103MYNRRN03", "10", "Hombre", "INSCRITO", "Primaria", "4", "A", "ESC-001", "Mtra. Cindy Mayanín Burgos González", "Discapacidad Intelectual", "ACTIVO", "Atención Focalizada", "Damián Carmona", "31DPR0001A", "Matutino"),
            ("ALU-004", "Valentina Guadalupe Ek Ku", "EKKV170215MYNRRN04", "7", "Mujer", "INSCRITO", "Primaria", "1", "A", "ESC-002", "Mtra. Andrea Gómez Tun", "Problemas de Lenguaje y Comunicación", "ACTIVO", "Atención Focalizada", "Ichcaanziho", "31DPR0002Z", "Matutino"),
            ("ALU-005", "Mateo Emiliano Poot Dzib", "PODM160730MYNRRN05", "8", "Hombre", "INSCRITO", "Primaria", "2", "B", "ESC-002", "Mtra. Andrea Gómez Tun", "Dificultades Severas de Aprendizaje", "ACTIVO", "Atención Focalizada", "Ichcaanziho", "31DPR0002Z", "Matutino"),
            ("ALU-006", "Camila Nicole Chim Baas", "CHBC150418MYNRRN06", "9", "Mujer", "INSCRITO", "Primaria", "3", "A", "ESC-003", "Mtra. Cindy Mayanín Burgos González", "Aptitudes Sobresalientes", "ACTIVO", "Enriquecimiento Curricular", "Gregorio Torres Quintero", "31DPR0003Y", "Matutino"),
        ]
        for aid, nom, curp, edad, sex, sit, niv, gra, gru, esc_id, doc, cond, est, tip, esc_nom, cct, tur in alumnos_datos:
            if not session.query(Alumno).filter_by(id=aid).first():
                session.add(Alumno(
                    id=aid,
                    nombre_completo=nom,
                    curp=curp,
                    edad_1_septiembre=edad,
                    sexo=sex,
                    situacion_alumno=sit,
                    nivel_educativo=niv,
                    grado=gra,
                    grupo=gru,
                    id_escuela=esc_id,
                    maestra_apoyo=doc,
                    condicion_discapacidad=cond,
                    estatus=est,
                    tipo_atencion=tip,
                    nombre_escuela=esc_nom,
                    cct_escuela=cct,
                    turno_escuela=tur,
                    fecha_nacimiento="2016-05-12",
                    fecha_derivacion="2024-09-15"
                ))

        # 4. ANEXO 3 — BARRERAS PARA EL APRENDIZAJE Y LA PARTICIPACIÓN (BAP)
        if not session.query(Anexo3Deteccion).filter_by(id_alumno="ALU-001").first():
            session.add(Anexo3Deteccion(
                id="anx3-alu-001",
                fecha="2026-09-20",
                id_alumno="ALU-001",
                id_personal="usr-doc-001",
                bap_fisicas="Disposición de bancos lejana a estímulos visuales distractores.",
                bap_actitudinales="Baja tolerancia del grupo regular ante conductas de inquietud motriz.",
                bap_pedagogicas="Consignas orales largas sin apoyos visuales ni listas de cotejo breves.",
                bap_organizativas="Tiempos rígidos de entrega sin estructuración en pasos secuenciales.",
                estatus_ia="VALIDADO",
                estado="ACTIVO"
            ))

        # 5. ANEXO 4 — SUGERENCIAS PEDAGÓGICAS
        if not session.query(Anexo4Sugerencia).filter_by(id_alumno="ALU-001").first():
            session.add(Anexo4Sugerencia(
                id="anx4-alu-001",
                id_alumno="ALU-001",
                fecha_elaboracion="2026-10-05",
                ciclo_escolar="2026-2027",
                trimestre="1",
                docente_especialista="Mtra. Cindy Mayanín Burgos González",
                area="Aprendizaje",
                sugerencias_area="Estructurar tareas en bloques de 15 minutos con apoyos visuales.",
                motivo="Apoyo en lectoescritura y autorregulación de la atención sostenida.",
                sugerencias="Ubicarlo al frente del aula, otorgar rol de asistente de material y fragmentar lecturas.",
                fecha_seguimiento="2026-11-15",
                nivel_cumplimiento_resultados="Avance notable en inicio de actividades.",
                estado="ACTIVA"
            ))

        # 6. ANEXO 5 — HOJAS DE EVENTOS SIGNIFICATIVOS
        if not session.query(Anexo5Evento).filter_by(id_alumno="ALU-001").first():
            session.add(Anexo5Evento(
                id="anx5-alu-001",
                fecha="2026-10-22",
                nombre_alumno="Jesús Emmanuel Chan Burgos",
                grado_grupo="2° A",
                especialista="Mtra. Cindy Mayanín Burgos González",
                evento="El alumno completó de forma autónoma su ejercicio de grafomotricidad usando un cronómetro visual.",
                estado="ACTIVO",
                id_alumno="ALU-001",
                id_escuela="ESC-001",
                escuela="Damián Carmona"
            ))

        # 7. ANEXO 7 — DERIVACIÓN
        if not session.query(Anexo7Derivacion).filter_by(id_alumno="ALU-001").first():
            session.add(Anexo7Derivacion(
                id="anx7-alu-001",
                fecha="2026-09-12",
                id_alumno="ALU-001",
                escuela="Damián Carmona",
                docente_regular="Mtro. Jorge Cetina Gómez",
                fecha_nacimiento="2016-05-12",
                respuestas_json=json.dumps({"motivo": "Inquietud motriz y dificultad en comprensión lectora"}),
                salud="Buena salud general, sin déficit auditivo o visual diagnosticado.",
                seguimiento_medico="En valoración con neuropediatría.",
                aspecto_relevante="Muestra alto entusiasmo ante dinámicas lúdicas y juegos con reglas claras.",
                elaborado_por="Mtra. Cindy Mayanín Burgos González"
            ))

        # 8. EPP MULTI-ÁREA
        if not session.query(EPPDoc).filter_by(alumno="ALU-001").first():
            partes_epp = {
                "META": {"estado": "COMPLETO", "ultima_modificacion": "2026-10-15"},
                "APRENDIZAJE": {
                    "estilo_aprendizaje": "Visual y kinestésico",
                    "nivel_competencia_curricular": "Fase 3 (Primer ciclo de primaria)",
                    "avances_observables": "Reconoce grafías iniciales y conteo cardinal hasta 30.",
                    "apoyos_requeridos": "Material concreto, instrucciones escalonadas."
                },
                "PSICOLOGIA": {
                    "desarrollo_emocional": "Sensible a la frustración ante tareas extensas.",
                    "atencion_y_memoria": "Periodos de atención sostenida de 12 a 15 minutos.",
                    "recomendaciones": "Refuerzo positivo contingente y pausas activas."
                },
                "COMUNICACION": {
                    "lenguaje_expresivo": "Estructura oraciones simples con vocabulario cotidiano.",
                    "lenguaje_comprensivo": "Comprende consignas directas con apoyo gestual.",
                    "recomendaciones": "Modelamiento articulatorio y tableros de comunicación."
                },
                "TRABAJO_SOCIAL": {
                    "dinamica_familiar": "Apoyo presente de la madre; tiempo limitado por jornada laboral.",
                    "entorno_sociofamiliar": "Acceso a servicios básicos y hábitos de descanso regulares.",
                    "acuerdos_casa": "Establecer horario fijo de tareas de 30 minutos diarios."
                }
            }
            session.add(EPPDoc(
                id="epp_ALU-001_2026-2027",
                alumno="ALU-001",
                ciclo="2026-2027",
                estado="APROBADO",
                revision="rev-epp-alu001-v1",
                fecha="2026-10-15",
                partes_json=json.dumps(partes_epp)
            ))

        # 9. PLANEACIONES (Formatos XXIII y XXV con Firmas)
        if not session.query(PlaneacionDoc).filter_by(id="plan-focalizada-001").first():
            plan_payload = {
                "Escuela": "Damián Carmona",
                "Grado_Grupo": "2° A",
                "Ciclo": "2026-2027",
                "Mes": "Noviembre 2026",
                "Docente_Especialista": "Mtra. Cindy Mayanín Burgos González",
                "Director_USAER": "Psic. Edgar Adrián Yam Briceño MD"
            }
            tablas_plan = {
                "nee": [
                    {
                        "alumno": "Jesús Emmanuel Chan Burgos",
                        "curp": "CABJ160512MYNRRN01",
                        "barreras_o_necesidades": "Requiere autorregulación de la atención y fragmentación de lecturas.",
                        "pda": "Identifica y formula preguntas sobre los textos leídos.",
                        "descriptor": "Jesús Emmanuel identifica palabras clave y formula tres preguntas directas sobre el texto con apoyo visual.",
                        "apoyos": "Tarjetas léxicas, cronómetro de 15 minutos, retroalimentación inmediata."
                    }
                ],
                "dosificacion": [
                    {
                        "semana": "Semana 1 (3-7 Nov)",
                        "actividad": "Lectura compartida y armado de rompecabezas de oraciones cortas.",
                        "recursos": "Láminas ilustradas, tijeras de punta redonda, cuaderno de apoyo.",
                        "modalidad": "Aula de Apoyo (2 sesiones semanales)"
                    }
                ],
                "evaluacion": [
                    {
                        "indicador": "Jesús Emmanuel formula al menos dos preguntas pertinentes sobre la narración leída.",
                        "instrumento": "Rúbrica de 3 niveles de desempeño",
                        "fecha": "2026-11-07"
                    }
                ]
            }
            session.add(PlaneacionDoc(
                id="plan-focalizada-001",
                cuenta="cindy.burgos",
                formato="XXIII",
                estado="APROBADO",
                revision="rev-plan-001-v2",
                guardado_en="2026-11-03 09:30",
                datos_json=json.dumps(plan_payload),
                metadatos_json=json.dumps({"titulo": "Plan de Intervención Focalizada Noviembre"}),
                tablas_json=json.dumps(tablas_plan),
                textos_json=json.dumps({"proposito": "Fortalecer la comprensión lectora y la autonomía de trabajo."}),
                payload_json=json.dumps({}),
                observaciones_director="Cumple con los 14 indicadores de la Zona 001. Aprobada para aplicación."
            ))

        # 10. REGISTRO DE VISITAS Y OFICIOS DE COMISIÓN
        if not session.query(RegistroVisita).filter_by(id="vis-001").first():
            session.add(RegistroVisita(
                id="vis-001",
                fecha="2026-10-28",
                escuela="Damián Carmona",
                personal="Psic. Edgar Adrián Yam Briceño MD",
                motivo="Acompañamiento técnico pedagógico y revisión de expedientes EPP.",
                observaciones="Se constata avance significativo en la vinculación entre maestras de apoyo y docentes regulares.",
                estatus="GUARDADA",
                tipo_acta="Acompañamiento",
                lugar="Mérida, Yucatán"
            ))

        if not session.query(OficioComision).filter_by(id="ofc-001").first():
            session.add(OficioComision(
                id="ofc-001",
                folio="OF-2026-089",
                clave_operacion="COM-USAER-001",
                fecha_emision="2026-11-01",
                fecha_comision="2026-11-05",
                escuela="Damián Carmona",
                id_escuela="ESC-001",
                maestra_apoyo="Mtra. Cindy Mayanín Burgos González",
                director_escuela="Prof. Carlos Canto Rosado",
                asunto="Taller de Ajustes Razonables para Docentes de Aula Regular",
                destino="Instalaciones de la Escuela Primaria Damián Carmona",
                horario="08:00 a 11:30 hrs",
                estado="ACTIVO"
            ))

        session.commit()
    print("Siembra de base de datos aislada USAER 2E completada con éxito.")

if __name__ == "__main__":
    sembrar_datos_sinteticos()
