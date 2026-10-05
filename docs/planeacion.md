# Planeación e intervención · 2026-10-04

Panel integrado en la navegación de apoyo, Psicología, Comunicación, Trabajo Social y Dirección. Dirección también accede desde su panel a las entregas del equipo.

- XXI: plan individual basado en IEPP; no convierte automáticamente una condición en NEE.
- XXIII: planeación trimestral de apoyo, Psicología y Comunicación.
- XXV: formato específico de Trabajo Social.
- Datos de identidad precargados desde el padrón autorizado; no se mezclan escuelas ni asignaciones de Marycruz/Cecilia.
- Evidencias: BAP, sugerencias, eventos con ID explícito y actas como contexto escolar. No atribuye una visita escolar a intervención individual.
- El borrador recupera automáticamente el contexto al crearse: evidencia individual y grupal, eventos históricos resueltos por el expediente, seguimientos y versiones más recientes de planes/planeaciones enviados o validados, únicamente de alumnos seleccionados. Fuentes grupales duplicadas se reúnen sin convertirlas en logros individuales. La desconexión de una fuente conserva el contexto previo y avisa de lo pendiente. Actualizar el expediente no solicita IA automáticamente.
- Guía visible en tres pasos, indicadores breves y evidencias desplegables. El resumen se prepara localmente y requiere revisión antes de enviarse; cambiarlo invalida el consentimiento y la propuesta anterior.
- Autoguardado de cambios confirmados cada 15 segundos mientras la sesión permanece activa. Guardar borrador confirma de inmediato. El texto aún no confirmado por el navegador y cambios pendientes pueden perderse si se cierra abruptamente; no se promete trabajo sin conexión.
- Respaldo JSON editable, recuperación por cuenta y consulta de versiones. Guardado aditivo en `Planeaciones_Versiones` del libro central, sin depender de Drive OAuth.
- Envío y revisión por Dirección; devolver observaciones o validar sin reescribir el trabajo del autor. La validación no estampa una firma manuscrita automática.
- PDF con todos los apartados y paginación legible. No se elimina contenido para forzar una página.
- IA opcional, bajo demanda, con resumen minimizado y revisado antes de enviar a Gemini. Modelo independiente configurable por `PLANEACION_GEMINI_MODEL`; predeterminado `gemini-2.5-flash`. Tiempo límite 45 s, una tentativa, fallo breve sin borrar el borrador.
- Programas: Plan de Estudio 2022, edición 2025. Los PDA deben cotejarse con el programa sintético; no se inventa un catálogo oficial.
- Catálogo extraído sin IA de las tablas SEP 2025, fases 3, 4 y 5: 563 extractos por campo y grado, con URL, página PDF, edición y huella del documento fuente. Son extractos de celdas, no un catálogo transcrito y validado editorialmente de todos los PDA; las continuaciones se verifican con la página original. Se conserva el texto y se separa de la adaptación propuesta. Cuatro campos y siete ejes seleccionables, más contextualización del programa analítico escolar. El Manual USAER SEGEY 2021 es el referente local, no un sustituto del currículo nacional. No se presume que el programa analítico de cada escuela esté cargado.
- La IA recibe referentes verificados y devuelve fundamento e IDs de fuentes permitidas. El servidor vuelve a resolver los IDs desde el catálogo; no acepta texto curricular alterado en un respaldo. La vista previa se genera del mismo PDF descargable, con membrete y pie institucionales en cada página. Cambiar el contenido invalida la vista previa. Edición en el panel y salida PDF: no se implementa creación nativa en Google Docs ni se depende de Drive OAuth.

Verificación local: 25 pruebas de modelo, servicio y pantalla; 24 pruebas de regresión de sugerencias, actas y filtros; PDFs ficticios renderizados y revisados. No se usaron alumnos reales ni llamadas reales a Gemini en estas pruebas.

Límites operativos: Google Sheets requiere acceso de edición del servicio al libro central; cuotas o desconexiones pueden impedir un guardado. Las versiones anteriores no se eliminan. El bloqueo de edición concurrente es por proceso; múltiples instancias conservan todas las versiones pero no ofrecen transacciones distribuidas. Actualizar entregas vuelve a consultar el libro. El libro sigue siendo la fuente persistente después de reiniciar.
