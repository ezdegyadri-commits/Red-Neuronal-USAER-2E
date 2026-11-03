# MATRIZ DE MIGRACIÓN DE MÓDULOS — USAER 2E 2.0
## Inventario Funcional, Endpoints y Estado de Equivalencia

> **Fecha de Actualización:** 3 de noviembre de 2026  
> **Rama:** `piloto-spa`  
> **Objetivo:** Garantizar que el 100% de la funcionalidad pedagógica e institucional de Streamlit sea portada a React SPA + FastAPI + PostgreSQL sin pérdida de información ni de reglas educativas.

---

## 1. MATRIZ DE EQUIVALENCIA INTEGRAL (20 MÓDULOS)

| # | Módulo Funcional | Archivo Original (Streamlit) | Nuevo Componente / Servicio | Endpoint FastAPI Correspondiente | Tablas Utilizadas | Estado de Migración | Prueba de Equivalencia | Riesgos Pendientes |
|:-:|:---|:---|:---|:---|:---|:---:|:---|:---|
| **1** | **Autenticación y Sesiones** | `ui/auth.py`, `data/acceso_usuarios.py` | `services/auth_jwt.py`, `LoginModal.tsx` | `POST /api/auth/login`, `GET /api/me`, `POST /api/auth/logout` | `usuarios`, `sesiones` | **Migrado** | `test_auth_real()` | Ninguno; tokens con expiración y hash seguro. |
| **2** | **Padrón de Escuelas** | `data/repository.py` (`escuelas()`) | `services/escuelas_service.py` | `GET /api/escuelas` | `escuelas` | **Migrado** | `test_escuelas_catalogo()` | Mantener 8 primarias canónicas de Zona 001. |
| **3** | **Padrón de Alumnos** | `services/expedientes.py`, `services/alumnos.py` | `services/alumnos_service.py`, `AlumnosList.tsx` | `GET /api/alumnos`, `GET /api/alumnos/{id}` | `alumnos` | **Migrado** | `test_alumnos_filtrado_escuela()` | Preservar estatus ACTIVO/BAJA y filtros por maestra. |
| **4** | **Expedientes Individuales** | `ui/pages.py` (`expedientes_page`) | `ExpedienteView.tsx`, `services/expedientes_service.py` | `GET /api/expedientes/{alumno_id}` | `alumnos`, `anexo3`, `anexo4`, `anexo5` | **Migrado** | `test_expediente_completo()` | Evitar cruce de expedientes entre escuelas no autorizadas. |
| **5** | **Evaluación Psicopedagógica (EPP)** | `ui/epp.py`, `services/epp.py` | `EPPEditor.tsx`, `services/epp_service.py` | `GET /api/epp/{alumno_id}`, `POST /api/epp` | `epp_documentos` | **Migrado** | `test_epp_guardado_concurrente()` | Coordinación de 4 áreas (Apoyo, Psic, Com, TS). |
| **6** | **Necesidades Educativas Específicas (NEE)** | `services/planeacion_nee.py` | `NEEPicker.tsx`, `services/nee_service.py` | `GET /api/nee/catalogo`, `GET /api/alumnos/{id}/nee` | `alumnos`, `epp_documentos` | **Migrado** | `test_nee_extraccion()` | Formulación obligatoria con sujeto + verbo + complemento. |
| **7** | **Barreras para el Aprendizaje (BAP)** | `ui/pages.py` (`bap_page`), `services/planeacion_social.py` | `BAPEditor.tsx` | `GET /api/bap/{alumno_id}`, `POST /api/bap` | `anexo3_deteccion` | **Migrado** | `test_bap_dimensiones()` | 4 contextos: Áulico, Escolar, Sociofamiliar, Metodológico. |
| **8** | **Planeación Individual (Anexo XXIII)** | `ui/planeacion.py`, `services/planeacion.py` | `PlaneacionEditor.tsx` | `GET /api/planeaciones/{id}`, `POST /api/planeaciones` | `planeaciones_doc`, `plan_versiones` | **Migrado** | `test_planeacion_guardado_con_revision()` | Cumplir 14 indicadores oficiales de supervisión. |
| **9** | **Planeación Grupal (Anexos XIX, XX y XXV)** | `services/planeacion_modalidad.py`, `services/planeacion_social.py` | `PlaneacionGrupal.tsx` | `GET /api/planeaciones/grupales`, `POST /api/planeaciones/xxv` | `planeaciones_doc` | **Migrado** | `test_planeacion_formatos_alternos()` | Soporte de formato XXV específico para Trabajo Social. |
| **10** | **Eventos Significativos (Anexo V)** | `ui/pages.py` (`eventos_page`) | `EventosTimeline.tsx` | `GET /api/eventos`, `POST /api/eventos` | `anexo5_eventos` | **Migrado** | `test_eventos_bitacora()` | Registro cronológico inmutable. |
| **11** | **Informes de Atención** | `documents/reportes.py`, `services/curriculo.py` | `InformesView.tsx` | `GET /api/informes/{alumno_id}` | `alumnos`, `epp_documentos` | **Migrado** | `test_informes_descriptivos()` | Trazabilidad trimestral. |
| **12** | **Actas y Constancias de Visita** | `ui/pages.py` (`visitas_page`), `documents/visitas.py` | `VisitasModule.tsx` | `GET /api/visitas`, `POST /api/visitas` | `registro_visitas` | **Migrado** | `test_visitas_registro()` | Firma digital y motivo de visita. |
| **13** | **Sugerencias y Recomendaciones (Anexo IV)** | `ui/sugerencias.py` | `SugerenciasDocente.tsx` | `GET /api/sugerencias`, `POST /api/sugerencias` | `anexo4_sugerencias` | **Migrado** | `test_sugerencias_creacion()` | Vinculación a docente de grupo regular. |
| **14** | **Perfil Grupal y Matrícula** | `services/planeacion_grupo_unico.py` | `PerfilGrupalView.tsx` | `GET /api/escuelas/{id}/grupos` | `alumnos`, `escuelas` | **Migrado** | `test_perfil_grupal()` | Mapeo de condiciones por grado y grupo. |
| **15** | **Análisis de Contexto y PDA Curricular** | `services/curriculo.py` | `CurriculoPDASelector.tsx` | `GET /api/curriculo/pda`, `GET /api/curriculo/ejes` | Catálogo SEP Fase 3, 4 y 5 | **Migrado** | `test_pda_fases_primaria()` | No inventar PDA; usar extracto oficial SEP 2026. |
| **16** | **Estadísticas Institucionales** | `ui/estadisticas.py` | `EstadisticasDashboard.tsx` | `GET /api/estadisticas/zona` | `alumnos`, `escuelas` | **Migrado** | `test_metricas_zona()` | Desglose por condición, sexo y escuela. |
| **17** | **Derivación de Alumnos (Anexo VII)** | `ui/pages.py` (`derivacion_page`) | `DerivacionForm.tsx` | `GET /api/derivaciones`, `POST /api/derivaciones` | `anexo7_derivacion` | **Migrado** | `test_derivacion_formulario()` | Historial médico y aspecto relevante. |
| **18** | **Generación y Exportación de PDF** | `documents/planeacion.py`, `documents/epp.py` | `services/pdf_export_service.py` | `GET /api/planeaciones/{id}/pdf`, `GET /api/epp/{id}/pdf` | ReportLab Document Engine | **Migrado** | `test_pdf_generacion_bytes()` | Inclusión obligatoria de Vo. Bo. Edgar Yam. |
| **19** | **Asistente Pedagógico Conversacional IA** | `ai/engine.py`, `ai/planeacion_prompt.py` | `PedagogicalChatDrawer.tsx` | `POST /api/ai/chat`, `POST /api/ai/sugerencias` | Gemini 3.5 / Fallback motor | **Migrado** | `test_ai_chat_contextual()` | Jamás enviar identificadores privados a APIs externas. |
| **20** | **Configuración, Permisos y Dirección** | `ui/direccion_rapida.py`, `ui/oficios.py` | `DirectorPanel.tsx` | `GET /api/director/resumen`, `POST /api/oficios` | `usuarios`, `oficios_comision` | **Migrado** | `test_panel_director_permisos()` | Visto bueno masivo y observaciones de dirección. |

---

## 2. REGLA DE NO REGRESIÓN

Cada módulo cuenta con su contrato REST validado en el servidor con modelos Pydantic y autorización RBAC. No se permite la simplificación arbitraria de campos institucionales ni la omisión de las firmas oficiales reglamentarias de la Zona 001.

