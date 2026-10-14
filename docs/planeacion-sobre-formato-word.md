# Planeación sobre el formato Word

El prototipo anterior de matriz Streamlit no fue publicado. Dirección solicitó trabajar directamente sobre el formato de referencia, por lo que se añadió un editor de documento con tablas, bordes negros, Times New Roman y organización horizontal según los ejemplos compartidos, no una cuadrícula de aplicación. Se revisaron los tres ejemplos trimestrales individuales y los cinco grupales; sus nombres, condiciones y actividades no se incorporan al código.

La fidelidad gráfica está pendiente de revisión de Dirección: el entorno no dispone de LibreOffice empaquetado para renderizar los Word originales. Se verificaron estructura OOXML, fuente Times New Roman y orientación Letter horizontal. No se afirma identidad píxel a píxel ni se copian logos, firmas o datos de las plantillas de otras personas.

## Elegir el trabajo

Se puede elegir Individual, Grupal o Por grado. Por grado requiere escoger un grado y reúne a sus destinatarios individuales y grupales autorizados; esta selección es una sesión por grado y no modifica la modalidad del padrón. En la opción Grupal, incluir alumnos individuales conserva la confirmación excepcional existente. La maestra puede escoger la guía grupal horizontal o el formato trimestral de los ejemplos para un subgrupo. Psicología, Comunicación y Trabajo Social conservan sus documentos específicos y acuerdos.

## Escribir en la hoja

Las celdas se escriben directamente y se expanden con el texto. Se puede vaciar su contenido, agregar filas o retirar filas manuales con confirmación. Las identidades procedentes del padrón, sesiones vinculadas y aportaciones de otras personas están protegidas; no se extienden permisos. Añadir/retirar destinatarios se hace mediante copia adaptada, conservando el documento previo.

Los PDA oficiales se presentan en la columna correspondiente, separados de la adaptación u objetivo editable. Retirar un referente se hace en su selector oficial, no falsificando su cita. El DUA se registra en los apoyos de configuración ya existentes, que alimentan la solicitud de propuestas. La IA se solicita explícitamente para conectar el resumen minimizado, referentes y ajustes y proponer actividades, nunca durante la escritura.

El editor transmite una pausa de edición de cuatro segundos, agrupada por el guardado canónico con sus intervalos, reintentos, versiones y control de concurrencia. Guardar cambios de la hoja transmite inmediatamente y pide guardado. Si no se confirma, el contenido sigue en sesión; también hay respaldo descargable del texto aún no transmitido. No es un sistema de trabajo totalmente desconectado.

## Arquitectura y seguridad

`ui/planeacion_papel_component` es un componente local, sin CDN, llamadas externas ni acceso a la base. Usa el protocolo Streamlit existente y comprueba origen/parent en los mensajes. El contenido se inserta mediante textContent, no como HTML ejecutable; el pegado es texto plano. No almacena datos en localStorage.

`services/planeacion_papel` vuelve a autorizar cada operación, reconstruye las celdas desde el documento de servidor y rechaza documento/huella obsoletos, celdas ajenas, campos inventados, acciones fuera de lista y eliminación de aportes/sesiones protegidos. La fila vacía del ejemplo permite empezar a escribir sin configurar la IA. Todos los cambios siguen usando el documento canónico, no una segunda base.

`documents/planeacion_papel` imprime las mismas celdas y orden del editor y conserva fundamentos, apoyos y complementos de especialistas. La interfaz anterior y la primera vista viva siguen siendo alternativas de desarrollo, no publicaciones separadas. Dirección autorizó la publicación de este rediseño el 14 de octubre de 2026, condicionada a completar la regresión final y verificar el despliegue.

## Comprobaciones del 14 de octubre

Batería final offline de 405 pruebas correcta (125.337 s), incluidos Por grado y la separación de caché de PDF entre formato anterior y papel. El protocolo JavaScript se probó con un DOM simulado: origen de mensajes, texto literal, autoguardado, guardado explícito en cola, conservación de texto ante versión obsoleta y aviso de salida. No hubo conexiones externas en esas pruebas.

En Chrome se abrió un formato individual ficticio, se escribió dentro de la celda de actividades y se comprobó Guardado confirmado. La captura de demostración solo contiene texto ficticio. Se reutiliza la caché por sesión y formato para no regenerar PDF en cada interacción. Guardar, mostrar PDF y enviar desde la hoja transmiten primero las celdas pendientes; enviar sigue sujeto a la revisión canónica. No se publicó ningún cambio ni se escribió en la base real.
