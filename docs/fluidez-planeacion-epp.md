# Planeación y EPP: menos configuración y actividades distintas

## Causa de actividades repetidas

El dosificador recorría todas las fechas y elegía la unidad con módulo
(`i % len(unidades)`). Dos actividades podían repetirse seis veces al solicitar
doce sesiones. Ahora cada unidad genera una sola actividad calendarizada. Si
la respuesta contiene menos unidades, no se rellenan las fechas copiándolas.
No se eliminan actividades históricas para corregir esta proyección futura.

El generador IA muestra cantidad (1–8), contextos y duración. La temática es
opcional. Las prioridades, apoyos, metodología y acuerdos quedan dentro de
personalización opcional con los valores sugeridos existentes. Se conserva la
revisión del resumen anonimizado y autorización antes de transmitir a IA, y la
revisión antes de incorporar al formato.

La solicitud y esquema exigen la cantidad elegida y los contextos permitidos.
El reintento conserva esos parámetros. Se validan copias y reformulaciones muy
similares dentro de la respuesta y frente a actividades recientes, incluidas
propuestas previas sin editar, sesiones del equipo y bloques por NEE. No se
afirma detección semántica perfecta: no hay otro motor ni embeddings añadidos.
Las NEE seleccionadas se incluyen con alias y evidencia por destinatario; se
mantienen las comprobaciones de fuentes, PDA y alumnos autorizados.

## EPP

Tres accesos segmentados separan Mi área, Conclusión y NEE e Informe completo.
Se evita mostrar siempre la conclusión a la coordinadora mientras trabaja su
área. Se retiran los botones de vaciado por campo y el guardado superior
duplicado. Los textos siguen editables y se pueden vaciar desde el propio campo.
El avance muestra las revisiones confirmadas y oculta el detalle secundario.
La consulta filtra alumnos autorizados antes de deserializar versiones de EPP,
en lugar de procesar primero todo el historial de la USAER.

Los botones principales de la aplicación y del formato vivo tienen mayor tamaño.
La barra existente de IA continúa avanzando por hitos reales.

## Verificación y límites

Datos ficticios y motor sustituido: dos unidades no producen doce copias,
reintentos sin duplicación, cantidad/contextos, NEE por destinatario, configuración
visible y ausencia de guardado al preparar. Regresión de planeación, continuidad,
EPP y edición de conclusión. La latencia de proveedor y los tiempos de una sesión
real no se deducen de estas pruebas locales. No se alteran datos reales ni se
reinicia manualmente el servicio.
