# Informe de preparación — USAER 2E

Fecha: 21 de octubre de 2026. Estado: cambios locales preparados y probados; **no publicados**.

Rama de trabajo: `codex/expedientes-continuidad-usaer`.
No se ejecutó push, despliegue, reinicio de Streamlit ni migración de registros reales.
No se modificaron permisos, contraseñas ni configuración de los motores de IA.

## 1. Revisión del manual

Fuente local: `D:/Google Drive/SEGEY/USAER 2E/2026-2027/220121_Manual_USAER (1).pdf`.
Se consultaron los apartados pertinentes, no se trató el documento como instrucciones de ejecución.

| Expediente o proceso | Referencia | Organización que guía la implementación |
| --- | --- | --- |
| Grupal | Anexo VI, páginas impresas 120–121; PDF 131–132 | Documentos generales del grupo; documentación de NI en agote de recursos; RI en espera de EPP; seguimiento de alumnos atendidos grupalmente; documentación AS cuando corresponda. |
| Individual | Anexo IX, páginas impresas 125–126; PDF 136–137 | Documentos generales y apartados de Aprendizaje, Psicología, Comunicación, Trabajo Social y área médica. |
| Programación EPP | Páginas impresas 72–76; PDF 83–87 | Acuerdo del equipo sobre aspectos, instrumentos, responsables, espacio y fechas; validación del cronograma por Dirección. |

En el individual se contemplan identificación, derivación, consentimiento, acta, CURP, solicitudes y canalizaciones, informes, entrevistas, eventos, EPP y plan de intervención. Por área se organizan instrumentos/evaluaciones, sugerencias e informes iniciales/finales; en Trabajo Social, estudio social y BAP familiar; documentación médica según el caso. No todos los documentos son obligatorios para todos los alumnos.

Regla importante del manual: al iniciar EPP, la documentación específica del alumno se incorpora al individual. Un documento colectivo no se mueve entero al expediente de un solo alumno.

## 2. Cambios preparados

| Solicitud | Resultado local |
| --- | --- |
| Expediente automático | Índice conectado por ID para BAP, sugerencias, eventos, derivaciones, planeaciones e informes EPP persistidos. Referencias a los documentos originales, sin duplicar su captura ni generar documentos vacíos al consultar. |
| Organización | Orden cronológico, sección documental y estado visible. Referencias individuales específicas se reorganizan al iniciar EPP; el original y los documentos colectivos se conservan. |
| Escaneos | Tras seleccionar el archivo, confirmar su tipo y destinatario/contexto, se integra automáticamente al expediente correspondiente. Se mantiene el botón manual para reintentar si falla. La misma copia verificada no se duplica. |
| Editar alumnos | Selectores para sexo, NI/RI, nivel, grado, grupo, condición, atención, estatus y categorías demográficas. Condiciones adicionales con selección múltiple. Los valores históricos no reconocidos se conservan como opciones, sin reinterpretarlos. Nombres y CURP siguen siendo campos de texto. |
| Listado nominal | Orden por grado, apellido o edad, ascendente/descendente. La edad se ordena numéricamente; se conserva el orden elegido al generar el listado. Se usa el nombre capturado en orden de apellidos: no se inventa un apellido separado a partir de un nombre ambiguo. |
| Fecha de derivación | Campo central con calendario, normalizado a ISO. Se precarga en la guía grupal solamente si la celda está vacía. La guía ofrece calendario; una fecha narrativa histórica se conserva sin vaciarla. |
| Control EPP | Cuadro compartido iniciado por Apoyo y continuado por el equipo autorizado. Incluye alumno, ciclo, área/reunión, fecha, hora opcional, aspectos, instrumentos, lugar y estado. |
| Calendario | La programación EPP se refleja automáticamente en el calendario de las cuentas autorizadas. Una modificación cambia la fecha vigente; no crea un segundo aviso. El calendario no muestra nombres de alumnos ni hallazgos de evaluación. |
| Recuperación de sesión | Recuperación durante 12 horas en la misma pestaña mediante token cifrado y registro privado revocable. Comprueba nuevamente la cuenta y permisos; no guarda contraseñas en el navegador. |
| Eventos significativos | Selector para continuar hojas vinculadas por ID. Borradores separados por alumno/grupo; recuperación cifrada con la misma cuenta y filtrado por la asignación actual. Se reconocen variantes antiguas del grado sin reescribir los eventos históricos. |
| Temática docente | Campo opcional en «Qué vamos a trabajar». Se incorpora como propuesta de la docente, no como diagnóstico ni evidencia de logro. |
| Generación IA | Indicador visible con tiempo transcurrido en los dos recorridos de generación completa. Prompt reforzado por función, evidencia, apoyos, nivel documentado e historial. Rechazo de copias y reformulaciones casi idénticas. |
| Continuar planeaciones | Etiquetas con fecha completa, hora con segundos, escuela, grado/grupo, ciclo, trimestre, función, modalidad, alumnado, estado y cantidad de actividades redactadas; sin mostrar hashes como nombre principal. |

El control EPP es una sola fuente de programación. El calendario es una proyección de esa fuente, no una copia editable que pueda desincronizarse.

## 3. Protección de la información

- Las pruebas usan datos y persistencia sintéticos; no se realizó una reparación ni modificación del padrón real durante esta preparación.
- Las consultas no vacían tablas, no borran fuentes ni migran documentos históricos.
- EPP conserva versiones aditivas, detecta revisión obsoleta, permite reintento idempotente y comprueba la lectura posterior antes de confirmar el guardado.
- La recuperación de acceso vence a las 12 horas; cerrar sesión revoca el token. Cambios en contraseña, identidad, rol o escuelas registradas invalidan su recuperación.
- El borrador cifrado de eventos sólo se recupera con la misma cuenta. Los contextos fuera de la asignación actual se excluyen. Un fallo al verificar permisos conserva el respaldo cifrado sin mostrarlo.
- En computadoras compartidas debe cerrarse sesión explícitamente. Cerrar la pestaña o borrar los datos del navegador no equivale a guardar en la base central.
- El índice no manda escaneos a IA ni deduce al alumno por su nombre o por el nombre del archivo.

## 4. Verificación efectuada

Pruebas específicas aprobadas, ejecutando los módulos por separado para aislar sus simulaciones:

| Módulo de pruebas | Casos aprobados |
| --- | ---: |
| Continuidad e integración nuevas | 24 |
| Interfaz de sesión y control EPP nuevas | 2 |
| Archivo privado, movimientos y UX del padrón | 23 |
| Editor del formato de planeación | 16 |
| Preparación rápida | 11 |
| Servicios EPP | 26 |
| Interfaz EPP | 9 |
| Entrada EPP | 11 |
| Calendario | 17 |
| Ámbito de estadística/padrón | 6 |
| Cola de envíos pendientes | 12 |
| Flujo simplificado de planeación | 15 |
| Generación completa | 13 |
| Interfaz de generación completa | 4 |
| Contexto documental | 6 |
| Matrícula y nomenclaturas | 7 |
| Estabilidad y concurrencia sintéticas | 17 |
| Compatibilidad de sesión con passkeys | 2 |
| Seguridad de passkeys | 11 |
| Capacidad de texto de actas/eventos | 2 |

Además: compilación de Python; comprobación de diferencias con finales de línea Windows; contrato JavaScript del editor; prueba JavaScript de almacenamiento por pestaña y separación entre cuentas.

La ejecución monolítica inicial de 734 casos no pasó: produjo 9 fallos y 87 errores, con sustituciones globales de funciones que escapaban de las simulaciones de interfaz. Durante la revisión también se corrigió una regresión de recuperación de la generación guardada causada por incluir su propia salida en la nueva huella. Los módulos afectados listados arriba se repitieron en procesos aislados y pasaron. **No se declara que toda la batería monolítica esté libre de fallos**; su aislamiento continúa siendo una tarea técnica pendiente.

## 5. Límites y comprobaciones pendientes antes de autorizar publicación

1. No se ha probado todavía la recarga en teléfonos Android ni en los equipos Windows reales de las maestras. La restauración se verificó con simulación de interfaz y almacenamiento; hace falta la prueba de aceptación en esos equipos en un entorno de prueba.
2. El respaldo de eventos contiene el texto recibido por el servidor. No se debe presentar como guardado confirmado un último cambio que el navegador no haya transmitido, una pestaña cerrada o datos locales borrados. Las planeaciones conservan además su respaldo propio del editor.
3. La detección de repetición es textual/casi textual; no garantiza detectar todas las repeticiones semánticas. No se enviaron solicitudes reales de IA durante las pruebas. La pertinencia educativa exige revisión docente.
4. El índice automático cubre las fuentes estructuradas enumeradas. Archivos externos sin un ID de alumno/grupo o sin tipo confirmado requieren esa identificación mínima; no se usa OCR para adivinar destinatarios. El enlace del índice abre el módulo de origen, no sustituye todos sus selectores por enlaces profundos.
5. Los estados y fechas históricos ambiguos no se corrigen por inferencia. Los documentos que no corresponden a una etapa no se generan como relleno.
6. La lectura completa del índice depende de la disponibilidad de sus fuentes. Si una falla se avisa que la lectura está incompleta, sin borrar los originales.

## 6. Datos técnicos para un despliegue futuro, aún no ejecutado

- Columna aditiva `Alumnos.Fecha_Derivacion`, incorporada al guardar ese campo. No se reescriben filas del padrón al consultar.
- Hoja privada `EPP_Programacion`, creada sólo al guardar una programación; versiones aditivas con revisión anterior.
- Hoja privada `Sesiones_Recuperables`, creada al emitir un acceso recuperable; tokens cifrados fuera de la hoja y diario autenticado de emisión/revocación. Mantiene los permisos existentes del archivo central.
- Dependencia explícita `cryptography==50.0.2`; versión disponible en el entorno local de pruebas.
- No hay enlaces públicos, cambios de permisos, migración masiva ni tarea que elimine registros antiguos.
- Se necesita una nueva autorización para publicar. Este informe no es una confirmación de disponibilidad en producción.
