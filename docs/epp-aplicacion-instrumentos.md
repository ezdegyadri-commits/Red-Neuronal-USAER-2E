# Aplicación digital y evaluaciones externas

## Qué está implementado

- XI: Identificación de BAP en el contexto sociofamiliar (Trabajo Social).
- XIII: Estilo de enseñanza del docente regular (Aprendizaje).
- XIV: Estilo de aprendizaje y motivación para aprender (Aprendizaje).
- XVI: Observación de la autodirección (Psicología).

Fuente: Manual USAER segunda edición 2020, páginas impresas 131, 136–138 y 140. Se contrastaron las opciones y subapartados con el PDF local. Los grupos de frecuencia se capturan por subapartado: los 22 ítems numerados del XIV corresponden a 27 registros de respuesta. No son 27 pruebas ni una nueva escala.

Los anexos se usan para registrar observaciones profesionales. El motor cuenta respuestas por opción y señala pendientes, sin sumar dimensiones distintas ni inventar baremos, puntajes globales, clasificaciones VAK o cortes diagnósticos. «No observado» no equivale a «No»; las observaciones de un ítem pendiente también se incluyen en el resumen. Se necesita fecha y revisión profesional antes de incorporar.

Una aplicación del mismo instrumento/fecha/alumno actualiza su evaluación corriente por identidad y conserva las versiones previas en EPP_Versiones. El resumen se ensambla solamente en su campo de destino si estaba vacío; no reescribe otra área ni la conclusión. Las respuestas en curso viven en el mismo contenido de área, no en otra base o lista privada de alumnos. Se reutilizan la fusión de tres vías, confirmación de lectura y guardas de cierre. El borrador ofrece descarga y recuperación JSON, verificando documento, función, instrumento y versión.

## Lo que no se presenta como disponible

Las otras entradas del catálogo siguen disponibles como registro de resultados profesionales o evaluación externa. En particular, el IHB de Macotela y Romay necesita la edición y protocolo que usa la Unidad antes de implementar sus reglas. No se sustituyen manuales comerciales, tablas normativas ni sistemas de corrección de editoriales por respuestas de IA. Una presencia en el catálogo no significa «corrección digital habilitada».

## Foto / escaneo externo

1. Archivo o cámara, lectura local, advertencias de OCR y revisión contra el original.
2. Confirmar alumno/instrumento/fecha y conservar solo resultados, sin datos de terceros, cuadernillos ni baremos.
3. Guardar como evaluación en la misma EPP y reunir antecedentes autorizados. No se supone que el nombre de un archivo identifica al alumno: se vincula al documento que el profesional abrió y confirmó.
4. Mostrar resumen anonimizado y pedir consentimiento antes de llamar a Gemini. Si cambia la lectura o las evaluaciones, se invalida el resumen anterior.
5. El motor existente redacta propuestas con referencias EV verificadas. Se llenan solo campos vacíos de la propia función, permanecen como borrador y no generan diagnósticos ni validan NEE automáticamente.

El original puede añadirse al expediente con la confirmación de revisión y el límite existente de 5 MB. La transcripción permite hasta 32 MB; una vista inicial limitada a 12000 caracteres se señala explícitamente, no se interpreta como lectura completa. Los reintentos de análisis idéntico reutilizan su propuesta en sesión. Ningún documento real ni evaluación de alumnos se utilizó para las pruebas.

## Verificación y límites

Pruebas automáticas con instrumentos/respuestas ficticias: opciones, fecha, reactivos, pendientes, frecuencias, límites por rol, edición parcial, conservación de textos y observaciones, idempotencia y flujo externo con OCR/IA simulados. Se conservan las pruebas del formato anterior y el formato nativo. La carga del archivo no autoriza por sí sola a enviarlo a IA. El resumen definitivo y sus decisiones requieren revisión profesional.

El borrador en sesión no es una garantía ante cierre forzado o borrado del almacenamiento del navegador. Se ofrece guardado explícito, envío agrupado y descarga recuperable; no se anuncia confirmación sin lectura central. La validación con datos ficticios no equivale a una captura comprobada en la cuenta real de una maestra. No se publica ni reinicia la aplicación como parte de la preparación sin autorización.
