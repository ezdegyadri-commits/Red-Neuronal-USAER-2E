# Gestión conectada del padrón y expedientes

## Alcance de esta rama

No publica cambios ni opera sobre registros reales durante la verificación.
Mantiene Streamlit, la identidad institucional, los permisos y los formatos
oficiales. No cambia Gemini ni envía expedientes a IA.

- Padrón: tabla con búsqueda, paginación y exportación; acciones de traslado,
  baja recuperable y reactivación separadas de la corrección ordinaria.
- Horarios: entrada directa a Mi semana. Las referencias y los avisos tienen
  recorridos separados; la jornada, los módulos y el descanso se configuran
  en un apartado desplegable. Se conservan choques, acuerdos, versiones y PDF.
- Expedientes: consulta individual y grupal; archivo explícito de documentos
  generados o escaneados; acceso a planeaciones y EPP existentes sin migrarlas.
- UI: fondo claro con gradientes discretos, superficies de 16 px, botones con
  estados, acción de baja diferenciada en rojo, foco visible y movimiento reducido.
  Las tablas HTML paginadas escapan el texto y resaltan las filas al pasar el cursor.
  La exportación CSV neutraliza prefijos de fórmulas sin modificar la fuente.

## Referencia institucional consultada

Manual USAER, enero de 2021, Anexo VI, páginas impresas 120–121 (PDF 131–132):
lista del grupo, BAP áulicas, evaluación diagnóstica y planeación; derivación y
agote de recursos según nuevo ingreso; eventos y sugerencias por grupo y, cuando
el caso lo requiere, por alumno. AS incorpora actividades exploratorias y
productos/evidencias. Al iniciar EPP los documentos específicos pasan al individual.

Anexo IX, páginas impresas 125–126 (PDF 136–137):

- Generales: identidad, derivación, consentimiento, nacimiento, CURP, solicitudes,
  canalizaciones, informes a instituciones, baja/alta, entrevistas, eventos, EPP y PI.
- Aprendizaje: sugerencias, estilo y motivación, competencia curricular e
  instrumentos, informe inicial y final.
- Psicología: sugerencias, estudio/instrumentos, informes inicial/final, entrevistas
  y visitas cuando corresponden.
- Comunicación: sugerencias, evaluación e instrumentos, informes inicial/final.
- Trabajo social: estudio social, BAP familiares y visitas según el caso.
- Médica: informes de estudios y reportes de atención.

Para reingreso, el informe final anterior puede servir de inicial. El listado de
referencias de la interfaz NO es una exigencia de generar todos los documentos
para todos los alumnos. La clasificación no es un diagnóstico ni una decisión
de que el alumno deba ser evaluado.

## Regla de archivo

El destino combina tipo documental, IDs de destinatarios, modalidad vigente y
etapa confirmada. No infiere alumnos a partir de nombres de archivos ni OCR.
El título puede sugerir el tipo del escaneo; se muestra como sugerencia editable,
nunca como lectura de su contenido. Un archivo sin clasificación no se asigna.
Si desde un grupo se añade un documento individual, se elige explícitamente a
qué alumno corresponde; no se asigna automáticamente a todos los integrantes.
Identidad, consentimiento, informes médicos y EPP son individuales; documentos
áulicos y planeación grupal pertenecen al grupo. Las categorías contextuales
dependen de la modalidad y de si se ha iniciado EPP. Si el contexto es ambiguo,
no archiva silenciosamente: pide confirmar tipo/destinatario.

El botón aparece en la descarga de planeaciones, EPP, BAP guardadas, sugerencias
individuales/grupales, hojas físicas de sugerencias y eventos guardados, y en el
módulo Documentos para anexos III, IV y V. Un borrador pendiente no se anuncia
como una versión guardada. Una plantilla vacía sin destinatario no se asigna.
En EPP también permite archivar la evaluación original PDF/JPG/PNG de hasta
5 MB, tras confirmar que pertenece exclusivamente al alumno. Esto no reduce
el límite previo de lectura/transcripción de evaluaciones ni sus tipos admitidos.

Las copias ya archivadas no se migran automáticamente de ámbito al iniciar EPP:
se conserva su contexto original. Los documentos específicos se pueden añadir
al individual confirmando la etapa. Un colectivo con varios alumnos requiere
un extracto individual revisado, no copiar el expediente completo a cada alumno.

## Baja y traslado

No hay DELETE físico. Una baja cambia solo Estatus y queda consultable para
reactivación. El ID y la CURP no cambian. El traslado interno actualiza en un lote
los campos de escuela, apoyo, grado, grupo y docente regular. No conserva datos
del plantel anterior como si fueran del nuevo. El catálogo debe identificar
unívocamente la escuela y la docente receptora; faltantes impiden la operación.

La autoridad se vuelve a comprobar en servidor: origen dentro del padrón
asignado y solo apoyo o Dirección; especialistas no operan movimientos. La
confirmación se invalida si cambia alumno, acción, destino o motivo. IDs
duplicados o varias identidades activas con la misma CURP exigen revisión.

El movimiento registra PREPARADO antes de escribir y CONFIRMADO al terminar.
Un reintento usa la misma operación; si se perdió la confirmación tras el cambio
de escuela, puede recuperarla sin volver a trasladar al alumno. Hay candado por
ID en el proceso y comparación directa de los campos anteriores; no se afirma
un CAS distribuido entre múltiples instancias de Google Sheets.

Los documentos individuales vinculados por ID permanecen recuperables en
destino. Las planeaciones individuales históricas de otra escuela solo admiten
lectura tras comprobar la cadena de traslados confirmados; no se editan con el
contexto nuevo. Las EPP se consultan por ID. Los documentos colectivos permanecen
en origen para proteger a los demás alumnos. Los legados sin ID no se reasignan
por coincidencia de nombre: requieren revisión, especialmente ante homónimos.

La matrícula activa del Anexo XIX deja de ofrecer al alumno con baja o traslado
confirmado; conserva su fila y los aportes anteriores como historial. No se
retira a un alumno solo por faltar en un filtro. El formato colectivo histórico
solo se consulta por el equipo de origen, nunca se entrega completo al destino.
Los eventos del editor identifican al destinatario además de su posición para
no reasignar texto en vuelo cuando cambia el orden de las filas. Ante un cambio
de estructura se conserva el respaldo y no se anuncia guardado de texto rechazado.

## Persistencia nueva, aditiva y privada

Se crean solo al confirmar las acciones, sin migrar ni vaciar hojas previas:

- Movimientos_Alumnos: auditoría de ubicaciones/estado, motivo, cuenta y operación.
- Documentos_Expediente: índice, contexto, hash y rango del archivo.
- Archivos_Expediente: partes binarias codificadas, separadas del índice.

PDF/JPG/PNG hasta 5 MB, con validación del binario. El contenido se escribe
literalmente (RAW), se verifica por rango acotado y SHA-256 antes de incorporar
la ficha, y se comprueba nuevamente al descargar. El mismo contexto/hash no se
duplica. Los datos parciales nunca se anuncian como un archivo completo ni se
borran para reintentar. No se crean enlaces públicos ni se cambian permisos.
Si ya existe una hoja con otro esquema, la escritura se detiene para revisión.

Se reutiliza la base privada institucional como el almacenamiento de adjuntos
existente. Esto NO es almacenamiento ilimitado: deben vigilarse capacidad del
libro y cuotas, y considerar un almacén de objetos privado para mayor volumen.

## Verificación

Pruebas sintéticas de clasificación, aislamiento por alumno/escuela, integridad,
literalidad, duplicación, límites, baja/reactivación, confirmación perdida,
traslado, comparación obsoleta y lectura histórica. AppTest recorre padrón,
baja/reactivación, búsqueda/paginación, horarios y expediente grupal sin
conexiones a datos reales. La fixture visual bloquea las escrituras de archivo.

Verificación local del 19/10/2026: suite integrada de gestión/planeación/contexto,
93 pruebas aprobadas; regresiones de horarios/referencias/EPP/sugerencias,
96 aprobadas; cierre de movimientos y archivo, 23 aprobadas (incluye las
pruebas repetidas de la suite integrada). Contrato Node del editor aprobado,
incluida la protección contra reasignar texto a otra fila tras una baja/traslado.
La comprobación de contraste cubre la paleta principal, no sustituye una
auditoría completa de accesibilidad ni la revisión visual pendiente.

Revisión visual en navegador pendiente: el acceso al origen local no fue
autorizado. No se intentó otro navegador ni una ruta alternativa.
