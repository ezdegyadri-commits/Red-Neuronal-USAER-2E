# Motor pedagógico contextual y chat de planeación individual

Entrega preparada el 28 de octubre de 2026 en `feat/motor-pedagogico-contextual`. Sin publicación, migraciones ni cambios de datos de producción.

## Resultado para el docente

La hoja individual incorpora el acceso «Indica qué necesitas ajustar…». El asistente se muestra junto al documento y, en móvil, antes de la hoja. Conserva una conversación por identificador estable de documento y alumno. El docente solicita un ajuste, revisa los apartados afectados y acepta, edita o descarta la propuesta. No cambia NEE ni PDA confirmados. Una observación solo se incorpora permanentemente al expediente mediante confirmación explícita; una indicación de generación nunca se convierte por sí sola en evidencia.

## Auditoría y decisiones

El chat anterior usaba un diálogo genérico y podía tratar la conversación como evidencia. La construcción antigua del prompt daba prioridad absoluta a campos manuales e incluía un respaldo de fuentes sin vínculo verificado. Se sustituyó el flujo activo del chat, se retiró ese respaldo y se separaron instrucciones, hallazgos documentados y propuestas.

Se reutilizan `services.planeacion.evidencias`, `preparar_contexto`, autorización, versiones, envío pendiente y respaldo del editor. `services.memoria_pedagogica` prepara una proyección acotada; `services.planeacion_chat_contextual` controla conversación, generación, destinos permitidos y aceptación. La interfaz usa `ui.planeacion_memoria` y `ui.planeacion_chat`; el acceso está en el componente existente del documento. `services.planeacion_generacion` y `ai.planeacion_completa` consumen la misma memoria. El transporte sigue siendo `ai.documento_json`, con los proveedores institucionales configurados, sus reintentos y límites existentes. No se agregan servicios pagados, base vectorial ni dependencias.

## Contexto y fundamento

Se incluyen únicamente fuentes vinculadas con IDs exactos a los alumnos autorizados: EPP validada o escaneada y revisada, entrevistas, visitas, eventos, seguimientos y planeaciones previas autorizadas. Se distinguen registros documentados y propuestas anteriores, datos recientes (ventana orientativa de 120 días), históricos y sin fecha. El plan anterior no demuestra un logro. Las fuentes no consultadas se señalan; se conserva la última copia.

La jerarquía es evidencia individual, referentes oficiales y currículo, indicaciones docentes y complemento provisional de IA. Se mantienen los referentes oficiales y los 14 indicadores de la Zona 001 sin aplicar requisitos CAM como exigencias USAER. El contenido confirmado no se sobrescribe. La aceptación aplica solamente destinos autorizados y compara tanto la versión de las celdas como la de los antecedentes; un cambio concurrente exige solicitar una propuesta nueva.

Las contradicciones explícitas detectadas se muestran al docente. La confirmación se vincula con la versión exacta de los fragmentos. La detección es conservadora y basada en patrones de desempeño, no una revisión semántica exhaustiva ni una decisión diagnóstica. El equipo conserva la valoración profesional. La comprobación de los 14 indicadores es orientativa, señala pendientes y no certifica ni califica automáticamente.

## Privacidad y rendimiento

Las solicitudes llevan alias y fragmentos pertinentes, no archivos completos ni identificadores locales de expedientes. Se filtran campos de contactos y composición familiar; la anonimización existente se conserva. Límite de 32 fragmentos y 14 000 caracteres de memoria, 80 registros para comparación, contexto curricular acotado y últimos ocho mensajes para la solicitud. Una corrección del resumen por privacidad también retira el texto de la vía contextual paralela.

La consulta del expediente y la IA utilizan los ejecutores existentes en segundo plano, con autorización de cuenta y escuela. La consulta se reutiliza durante 120 segundos; los fragmentos de estado no regeneran continuamente toda la hoja. El editor y la conversación permanecen disponibles ante un fallo. El botón de envío se desactiva mientras existe una solicitud. Las propuestas se conservan como pendientes antes de aceptarlas. No se midió latencia de producción ni se promete respuesta instantánea de un proveedor externo.

## Verificación realizada

Matriz aislada: 162 pruebas aprobadas en 13 módulos. Tras estabilizar la identidad de conflictos frente a cambios de relevancia y probar el evento completo del botón con cambios pendientes, el módulo nuevo se repitió con 30 pruebas aprobadas; total equivalente: 164 casos. El contrato JavaScript del editor también pasó. Se comprobó sintaxis y diferencias sin errores de espacios.

| Escenario | Comprobación real |
|---|---|
| A | EPP, visita y eventos ficticios llegan al contexto con referencias y sin expediente íntegro. |
| B | Avances recientes se priorizan y antecedentes históricos se distinguen. |
| C | La propuesta cambia solo destinos autorizados; conserva otros campos y decisiones manuales. |
| D | Contradicciones explícitas bloquean generación hasta confirmación; nuevas versiones invalidan decisiones anteriores. |
| E | Revisión con 14 indicadores, pendientes y valoración profesional sin certificación automática. |
| F | Serialización y reapertura conservan conversación y propuesta; AppTest verifica navegación entre documentos. |
| G | Se rechazan alumno ajeno, permisos revocados, referencias inventadas, rutas alteradas y propuestas desactualizadas. |
| H | Navegador real a 390 × 844: enviar indicación, revisar y aceptar, cambiar de alumno y comprobar aislamiento. La recuperación de la conversación se probó mediante AppTest. Sin desbordamiento horizontal en el chat. |
| I | Información insuficiente o falta de PDA se identifica como provisional y solicita los datos esenciales. |

También se verificaron el guardado, continuidad, NEE múltiples, edición manual, variedad de actividades, guía oficial, integridad, documento en papel y flujo simplificado. La primera ejecución conjunta del bloque de interfaz sin el indicador de compatibilidad produjo errores de configuración de navegación; la matriz aislada con `USAER_NAVEGACION_DOCUMENTOS=0`, correspondiente a esos casos heredados, pasó completa. El chat nuevo se verificó también en navegador local.

## Límites y revisión antes de publicación

La IA se simuló y la persistencia de las pruebas usa datos ficticios. No se hicieron llamadas pagadas, escrituras en Sheets, pruebas con expedientes reales ni una comprobación del despliegue. La recuperación probada incluye serialización, reapertura y navegación; no se provocó una caída del servicio de producción ni se probó una pérdida de conexión móvil real. La vista móvil comprobada corresponde al chat y su integración local de prueba, no a todos los formatos en dispositivos físicos.

La conversación comparte el JSON versionado existente y sus límites de tamaño. Los mensajes y las propuestas no se validan como hallazgos por existir en el chat. Los módulos antiguos de IA conservan sus funciones por compatibilidad, pero la interfaz activa ya utiliza el servicio contextual nuevo.

Para revertir, retirar el commit de esta rama devuelve el acceso y los prompts anteriores; no se requiere revertir datos ni esquema. La publicación debe revisar la recarga de módulos de las sesiones Streamlit existentes y comprobar una apertura autorizada, una propuesta revisable y su guardado confirmado.
