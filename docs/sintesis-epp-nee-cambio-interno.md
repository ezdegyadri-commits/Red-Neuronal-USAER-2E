# Síntesis documental, NEE vinculadas y cambio interno de responsable

Preparado y probado localmente el 23 de octubre de 2026, con publicación
autorizada después de verificar. No se modificó la matrícula real ni se
trasladó al alumno del ejemplo.

## Comportamiento

- Los escaneos y documentos archivados ofrecen una vista textual breve,
  extractiva y corregible; no se muestra el original completo ni su OCR íntegro.
  El original se conserva en el expediente. La síntesis inicial tiene hasta
  800 caracteres y admite corrección profesional hasta 1200.
- Las NEE explícitas de una EPP escaneada se seleccionan y revisan contra el
  original. Solo se vinculan a una EPP individual de un único ID de alumno.
  No se infieren necesidades de un diagnóstico o una categoría de discapacidad.
- La conclusión vigente y revisada de la EPP digital también alimenta el
  desplegable de NEE de la planeación. El selector añade el enunciado sin borrar
  la redacción previa; elegirlo otra vez no lo duplica. Conserva procedencia y
  revisión de las fuentes en el contexto del documento.
- Después de guardar una síntesis de EPP escaneada, utilizar «Actualizar
  antecedentes» de la planeación para incorporar las opciones nuevas.
- El cambio «Cambiar maestra en la misma escuela» se ofrece exclusivamente
  entre las dos responsables de Ichcaanziho. Cambia solo Maestra de Apoyo;
  conserva escuela, grado, grupo, modalidad, ID y expediente. Requiere motivo
  y confirmación explícita de la maestra de origen o Dirección. Los especialistas
  no pueden ejecutar movimientos.
- El diario de movimientos conserva PREPARADO y CONFIRMADO. Una operación no
  confirmada no acredita cambio de coordinación. La nueva responsable puede
  continuar la conclusión de la misma EPP si existe la cadena confirmada; META
  conserva su creadora y las nuevas versiones registran a su autora real.
  Los documentos históricos de planeación mantienen su autoría, sin adjudicarlos
  ni clonarlos automáticamente.
- Se eliminó el respaldo inseguro que mostraba toda la matrícula de la otra
  maestra cuando la comparación por responsable no encontraba coincidencias.
  Los alias admitidos son explícitos; un apellido compartido no acredita identidad.

## Identificación y modalidades

La interfaz distingue el total del grado de los alumnos con atención grupal
e individual. La exclusión de la modalidad individual del Anexo XIX responde
a la instrucción de Dirección y no elimina alumnos del padrón. Las pruebas
de separación por responsable emplean datos ficticios; los resultados de
auditorías de matrícula real no se incluyen en este repositorio.

## Persistencia y privacidad

Se agrega `Sintesis_Documentos` al libro privado existente cuando una persona
confirma guardar la primera síntesis. No cambia permisos ni el esquema de
`Documentos_Expediente` o `Archivos_Expediente`.

Columnas: ID_Documento, SHA256, Revision, Sintesis_JSON, Cuenta, Fecha.
Escritura literal RAW, versiones aditivas y confirmación por lectura posterior.
La revisión incluye el hash de su predecesora: volver a una síntesis anterior
genera una nueva versión; repetir un envío ya confirmado no lo duplica.

La lectura revalida el acceso al documento y su hash. No se realiza OCR al
navegar ni al reconstruir el contexto de planeación: solo al pedir la vista
previa. La extracción local no envía documentos a Gemini ni a otros motores.
El análisis con IA ya existente sigue requiriendo revisar y autorizar su
resumen anonimizado por separado.

## Verificación

Pruebas ejecutadas en procesos separados, exclusivamente con datos ficticios:

| Suite | Resultado |
| --- | --- |
| Síntesis, NEE e intercambio interno | 13 correctas |
| Interfaz de síntesis | 1 correcta |
| Servicio EPP | 26 correctas |
| EPP viva | 55 correctas |
| Planeación viva | 12 correctas |
| Estadística y separación de docentes | 6 correctas |
| Movimientos y archivo privado | 23 correctas |
| Hoja tradicional | 16 correctas |
| Captura sin fricción | 10 correctas |
| Instrumentos EPP | 9 correctas |
| Materiales y lectura local | 11 correctas |

Además, sintaxis JavaScript válida y prueba local en Chrome del selector
nativo: añade la NEE, conserva el texto previo, confirma el estado local y
no duplica el enunciado al seleccionarlo otra vez.

La suite antigua `test_student_school_scope` no puede importarse: ya en HEAD
importa `validar_identidad_padron`, inexistente en `services.padron_oficial`.
Es una incompatibilidad previa, no una prueba pasada; no se modificó ese
contrato ajeno a esta solicitud. Se verificaron los filtros relevantes con
las suites de estadística, movimientos y los nuevos casos sintéticos.

## Límites visibles

La síntesis es extractiva, no una interpretación clínica. El OCR puede omitir
tablas, escritura manuscrita o páginas fuera del límite de lectura; los avisos
se conservan y se exige revisión profesional. Las NEE de escaneos se ofrecen
como enunciados seleccionados del original, no como nuevos diagnósticos.
No se comprobó una captura real ni una reasignación en producción.
