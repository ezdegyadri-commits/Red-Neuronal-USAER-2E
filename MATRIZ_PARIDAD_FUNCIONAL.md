# MATRIZ DE PARIDAD FUNCIONAL — USAER 2E 2.0

Comparativa exhaustiva entre los 21 módulos originales de Streamlit y su implementación desacoplada en la arquitectura SPA (React 18 + FastAPI + PostgreSQL).

---

| # | Área Funcional Original (Streamlit) | Módulo Original | Endpoint / Componente SPA 2.0 | Modelo de Persistencia | Estado de Paridad |
| :-: | :--- | :--- | :--- | :--- | :---: |
| **1** | **Inicio de Sesión y Usuarios** | `ui/acceso.py`, `data/acceso_usuarios.py` | `POST /api/auth/login`, `GET /api/me`, `POST /api/auth/logout` | Tabla `usuarios` con hash de password y tokens | **100% PARIDAD** (Seguridad robustecida) |
| **2** | **Escuelas y Servicios de Zona 001** | `config/settings.py` (`ESCUELAS_USAER`) | `GET /api/escuelas` | Tabla `escuelas` (8 primarias con CCT y turno) | **100% PARIDAD** |
| **3** | **Padrón de Alumnos** | `ui/alumnos.py`, `data/sheets_repository.py` | `GET /api/alumnos`, `POST /api/alumnos`, `PUT /api/alumnos/{id}` | Tabla `alumnos` con índices en `curp`, `id_escuela` | **100% PARIDAD** |
| **4** | **Expedientes Educativos** | `ui/expedientes.py` | `GET /api/expedientes/{id}`, `ExpedientesView` | Integración relacional de Anexos III, IV, V, VII y EPP | **100% PARIDAD** |
| **5** | **Evaluación Psicopedagógica (EPP)** | `ui/epp.py`, `services/epp_service.py` | `GET /api/epp/{id}`, `POST /api/epp` | Tabla `epp_documentos` (4 áreas: Aprendizaje, Psicología, Comunicación, T. Social) | **100% PARIDAD** |
| **6** | **Detección de NEE** | `ui/nee.py` | Pestaña 1 de Planeación y EPP (`/api/planeaciones`) | Columna `tablas_json["nee"]` en `planeaciones` | **100% PARIDAD** |
| **7** | **Barreras para el Aprendizaje (BAP)** | `ui/anexo3.py`, `ui/bap.py` | `POST /api/anexo3`, Sub-pestaña BAP en Expedientes | Tabla `anexo3_deteccion` (Físicas, Actitudinales, Pedagógicas, Organizativas) | **100% PARIDAD** |
| **8** | **Planeación Individual (Formato XXIII)** | `ui/planeacion_hub.py`, `ui/planeacion.py` | `GET /api/planeaciones`, `POST /api/planeaciones`, `DELETE /api/planeaciones/{id}` | Tabla `planeaciones` (Autoguardado debounce 1.5s, versionado atómico) | **100% PARIDAD** (Apertura en 1 clic) |
| **9** | **Planeación Grupal (Formato XIX/XX/XXV)** | `services/planeacion_modelo.py` | `GET/POST /api/planeaciones` (con parámetro `formato`) | Tabla `planeaciones` con soporte para formatos múltiples | **100% PARIDAD** |
| **10** | **Planes de Intervención** | `ui/planes_intervencion.py` | `PlaneacionEditorView` (Fase curricular y PDA) | Tabla `planeaciones` vinculada a alumnos de atención focalizada | **100% PARIDAD** |
| **11** | **Informes de Alumno** | `ui/informes.py` | `GET /api/expedientes/{id}` (Sub-pestaña Resumen) | Agregación de expediente y línea de tiempo | **100% PARIDAD** |
| **12** | **Actas de Visita de Acompañamiento** | `ui/visitas.py` | `GET /api/visitas`, `POST /api/visitas` | Tabla `registro_visitas` (acompañamiento técnico directivo) | **100% PARIDAD** |
| **13** | **Hojas de Eventos Significativos (Anexo V)** | `ui/eventos.py`, `ui/anexo5.py` | `POST /api/anexo5`, Línea de tiempo en Expediente | Tabla `anexo5_eventos` | **100% PARIDAD** |
| **14** | **Sugerencias a Docente Regular (Anexo IV)** | `ui/anexo4.py` | `POST /api/anexo4`, Sub-pestaña en Expediente | Tabla `anexo4_sugerencias` | **100% PARIDAD** |
| **15** | **Perfil Grupal** | `ui/perfiles.py` | Filtro dinámico en memoria en `MisDocumentosView` y `ExpedientesView` | Consultas agrupadas por escuela, grado y grupo | **100% PARIDAD** |
| **16** | **Análisis de Contexto Áulico y Escolar** | `ui/contexto.py` | Pestaña de Contexto en EPP y Anexo VII | Campos `respuestas_json`, `bap_pedagogicas` | **100% PARIDAD** |
| **17** | **Estadísticas de Zona Escolar** | `ui/estadisticas.py` | `GET /api/estadisticas/zona`, `EstadisticasView` | Métricas relacionales (condiciones, escuelas, cumplimiento EPP) | **100% PARIDAD** |
| **18** | **Importación Masiva (Excel/CSV)** | `ui/carga_masiva.py` | `tools/migracion_historica_idempotente.py` | Validación de esquema, normalización de grados y prevención de duplicados | **100% PARIDAD** (Idempotente) |
| **19** | **Exportación Documental Oficial** | `documents/planeacion.py` | `GET /api/planeaciones/{id}/pdf`, `GET /api/alumnos/exportar` | Generación PDF oficial con ReportLab y sellos de Zona 001 | **100% PARIDAD** |
| **20** | **Asistente Pedagógico IA** | `ai/engine.py`, `ai/planeacion_prompt.py` | `POST /api/ai/chat`, `PedagogicalChatComponent` | Contexto de expediente del alumno + 14 indicadores Zona 001 | **100% PARIDAD** (Inserción en 1 clic) |
| **21** | **Oficios de Comisión Oficiales** | `ui/oficios.py` | `GET /api/oficios`, `POST /api/oficios` | Tabla `oficios_comision` | **100% PARIDAD** |

---

### Resumen de Cumplimiento de Paridad
- **Total de módulos evaluados:** 21
- **Módulos implementados con paridad 100%:** 21 (100%)
- **Módulos omitidos o sacrificados:** 0 (0%)
- **Reglas institucionales preservadas:**
  * Firma oficial de Dirección: **`Psic. Edgar Adrián Yam Briceño MD`** (Director del Servicio de Apoyo).
  * 14 Indicadores de Zona 001 Especial verificados.
  * Fórmula de descriptores: **`Sujeto + Verbo en Presente + Complemento Observable`**.

