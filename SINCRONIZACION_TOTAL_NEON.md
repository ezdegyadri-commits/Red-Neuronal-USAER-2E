# Sincronización verificada de la base central a Neon

Cotejo del 1 de noviembre de 2026 (hora de México).

Se copiaron las 34 pestañas del libro central: 10,097 filas de datos. Se conservaron encabezados, orden, celdas, columnas adicionales, filas internas vacías y duplicados en una copia íntegra en PostgreSQL. Cada pestaña fue cotejada por SHA-256 después del commit. El origen se leyó de nuevo antes del commit y no cambió durante la copia.

El lector utiliza exclusivamente el alcance `spreadsheets.readonly`. No se ejecutaron escrituras, borrados ni cambios de permisos en Google Sheets.

## Destinos operativos comprobados

| Destino | Registros confirmados |
|---|---:|
| Usuarios | 15 |
| Alumnos válidos | 262 |
| Escuelas del catálogo institucional | 8 |
| Planeaciones | 154 |
| Revisiones de Planeación | 1,917 |
| EPP | 8 |
| Revisiones de EPP | 202 |

Se añadieron las 25 revisiones de Planeación que faltaban en el núcleo. El cotejo previo confirmó cero diferencias entre las revisiones ya existentes y su fuente. Se mantuvieron dos registros de legado: una revisión incompleta y una referencia parental ausente en el origen; no se inventó su contenido ni se eliminó el rastro.

Las 15 cuentas mantienen exactamente su identificador, usuario, clave, rol y escuelas. Se comprobó la comparación de credenciales en memoria sin iniciar sesiones ajenas.

## Cotejo por pestaña

| Pestaña | Filas de origen | Copia íntegra en Neon | Registros operativos únicos |
|---|---:|---:|---:|
| Escuelas | 0 | 0 | 8 |
| Personal | 0 | 0 | 0 |
| Asignaciones | 0 | 0 | 0 |
| Alumnos | 263 | 263 | 262 |
| Anexo3_Deteccion | 102 | 102 | 102 |
| Anexo4_Sugerencias | 68 | 68 | 68 |
| Anexo5_Eventos | 397 | 397 | 396 |
| Usuarios | 15 | 15 | 15 |
| Expedientes | 168 | 168 | — |
| Relaciones_Expediente | 431 | 431 | — |
| Linea_Tiempo | 327 | 327 | — |
| Registro_Visitas | 249 | 249 | 248 |
| Anexo7_Derivacion | 20 | 20 | 20 |
| Oficios_Comision | 26 | 26 | 26 |
| Configuracion_Oficios | 9 | 9 | 9 |
| Padron_Ciclo | 178 | 178 | — |
| Historial_Correcciones_Padron | 341 | 341 | — |
| Alumnos_Historico_Ichcaanziho | 11 | 11 | — |
| Avisos_Cronogramas | 166 | 166 | — |
| Horarios_Restricciones | 473 | 473 | — |
| Horarios_Apoyo | 366 | 366 | — |
| Borradores_Horarios | 1,447 | 1,447 | — |
| Borradores_Cronogramas | 432 | 432 | — |
| Planeaciones_Versiones | 3,730 | 3,730 | — |
| Novedades_Supervision | 109 | 109 | — |
| Novedades_Supervision_Revision | 0 | 0 | — |
| EPP_Versiones | 202 | 202 | — |
| Docentes_Regulares | 71 | 71 | 71 |
| Movimientos_Alumnos | 6 | 6 | — |
| Sesiones_Recuperables | 415 | 415 | — |
| Documentos_Expediente | 3 | 3 | — |
| Archivos_Expediente | 70 | 70 | — |
| EPP_Programacion | 1 | 1 | — |
| Sintesis_Documentos | 1 | 1 | — |

La fila vacía ALU-276 sigue conservada en la copia íntegra; se excluyó del padrón operativo conforme a la autorización anterior. Dos identificadores repetidos de eventos/visitas quedan íntegros en la copia; las tablas operativas conservan una fila por identidad (396 eventos y 248 visitas). Los ocho registros de escuelas proceden del catálogo institucional existente en el código; la pestaña Escuelas del libro está vacía. No se generaron escuelas de ejemplo.

## Estado de la conexión de Streamlit

**No se activó el cambio global a Neon.** Streamlit conserva el origen central operativo vigente. Los servicios heredados de Planeación y EPP aún llaman directamente a `data.google`; activar solamente `USAER_STREAMLIT_DATA_SOURCE=postgresql` dejaría las lecturas/escrituras repartidas entre dos orígenes. Antes del cambio faltan el adaptador de esos diarios y su prueba de lectura/guardado en Streamlit, además de comprobar `DATABASE_URL` en sus Secrets. No basta con que esté configurada en Render.

El acceso al panel de Streamlit no se ejecutó: la revisión automática de la herramienta de navegador no pudo completarse. No se expusieron claves ni se cambió la configuración del servicio.

Esta verificación cubre los datos del libro central, no constituye una copia de todos los archivos externos de Drive enlazados desde sus celdas. Las capturas posteriores a este cotejo requieren otra sincronización antes del corte definitivo.

## Pruebas y recuperación

- Pruebas de copia íntegra, idempotencia, reversión, identidades, permisos y retención de borradores.
- Ensayo sobre PostgreSQL real con datos ficticios dentro de un esquema transaccional, revertido al finalizar.
- Comprobación de contenido leído desde PostgreSQL después del commit.
- Prueba del importador de históricos con 57 revisiones, más de una página, repetido sin duplicarlas.
- Una divergencia de contenido detiene la importación y revierte la transacción; no se utiliza la última escritura como ganadora.

## Herramienta de copia

`python tools/sync_central_pg.py --env-file <archivo-privado> --report <reporte-local>` valida sin escribir. Para aplicar se requieren explícitamente `--apply --init-schema`. El reporte contiene sólo conteos, estado y huellas; los valores originales y las credenciales no se escriben en el repositorio.
