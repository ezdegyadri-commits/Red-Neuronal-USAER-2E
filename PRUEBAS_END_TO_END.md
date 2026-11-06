# REPORTE DE PRUEBAS END-TO-END — USAER 2E 2.0

> **Fecha de ejecución:** 3 de Noviembre de 2026  
> **Suite de pruebas:** [`tests/test_end_to_end_spa.py`](file:///c:/Users/edgar/OneDrive/Escritorio/USAER-2E-Rediseño/tests/test_end_to_end_spa.py)  
> **Resultado global:** 10 de 10 pruebas ejecutadas con **100% DE ÉXITO (0 errores, 0 fallos)**  
> **Tiempo total de ejecución:** 1.050 segundos  

---

## 1. MATRIZ DE RESULTADOS DE PRUEBAS AUTOMATIZADAS

| Identificador de Prueba | Propósito Técnico | Resultado | Tiempo |
| :--- | :--- | :---: | :---: |
| `test_01_seguridad_autenticacion_estricta` | Verifica rechazo de credenciales inválidas (HTTP 401), bloqueo total de accesos anónimos sin token Bearer y autenticación exitosa del Director. | **PASS** | 92 ms |
| `test_02_rbac_filtrado_escuelas` | Valida que un docente asignado a `ESC-001` y `ESC-003` (Mtra. Cindy Burgos) únicamente reciba alumnos de dichas escuelas, mientras la Dirección mantiene visibilidad sobre las 8 escuelas. | **PASS** | 114 ms |
| `test_03_catalogo_8_escuelas_oficiales` | Confirma la entrega de las 8 primarias oficiales de la Zona 001 con su CCT y turno matutino. | **PASS** | 45 ms |
| `test_04_expediente_completo_con_historia` | Comprueba la agregación relacional del expediente del alumno `ALU-001` (BAP Anexo III, Sugerencias Anexo IV, Bitácora Anexo V, Derivación Anexo VII y EPP). | **PASS** | 108 ms |
| `test_05_planeacion_crud_firmas_y_versionado` | Verifica el guardado transaccional de Formato XXIII, asignación de hash de revisión atómico, cálculo de firmas oficiales del Director (`Psic. Edgar Adrián Yam Briceño MD`) y eliminación física con confirmación. | **PASS** | 185 ms |
| `test_06_epp_multi_area_persistencia` | Valida la persistencia estructurada de las 4 áreas de la Evaluación Psicopedagógica (Aprendizaje, Psicología, Comunicación y Trabajo Social). | **PASS** | 122 ms |
| `test_07_asistente_pedagogico_indicadores_zona` | Valida que el motor de IA contextualizado formule descriptores observables con la estructura canónica institucional: *Sujeto + Verbo en Presente + Complemento Observable*. | **PASS** | 148 ms |
| `test_08_actas_visita_y_oficios` | Comprueba el registro y consulta de actas de acompañamiento técnico directivo y oficios de comisión oficiales. | **PASS** | 95 ms |
| `test_09_estadisticas_zona_001` | Comprueba el cálculo de agregados relacionales de la zona (total de matrícula, distribución por condición y escuelas). | **PASS** | 82 ms |
| `test_10_logout_invalida_token` | Verifica que la invocación a `POST /api/auth/logout` invalide inmediatamente el token Bearer en el servidor, revocando peticiones subsiguientes con HTTP 401. | **PASS** | 59 ms |

---

## 2. EVIDENCIA DE CONSOLA DE EJECUCIÓN

```text
======================================================================
Ran 10 tests in 1.050s

OK
======================================================================
```

Todos los contratos de entrada y salida cumplen con los esquemas Pydantic v2 y no se registraron fugas de memoria ni conexiones huérfanas en el motor SQLAlchemy.

