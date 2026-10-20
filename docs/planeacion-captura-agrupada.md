# Captura agrupada sobre los formatos tradicionales

El módulo publicado no cambia hasta desplegar este código. No requiere migraciones
ni modificaciones a los documentos ya guardados.

## Alcance

La pantalla propia del rol se muestra mediante `st.tabs`. Apoyo ve su planeación;
Psicología, Comunicación y Trabajo Social ven la de paradocentes, con su formato.
Dirección conserva revisión y consulta del trabajo compartido. No se asignan nuevos
permisos. El segundo tab da acceso a los documentos compartidos ya autorizados.

XXIII conserva NEE, aprendizaje/PDA, descriptor, contextos, actividades,
temporalidad, recursos, evaluación y observaciones. XXV conserva alumnos, BAP,
apoyos/ajustes, contextos, actividades, fechas, recursos y resultados. El documento
XXI heredado sigue editable con sus tablas propias. Se reutiliza el contrato del
formato vivo, incluyendo competencias, sesiones vinculadas y escala individual.

## Un solo guardado

La captura propia utiliza un `st.form(clear_on_submit=False)` con un único
`form_submit_button`: Guardar Planeación. Celdas, nuevas filas, retiros,
referentes y apoyos DUA se aplican juntos. Los retiros producen otra versión del
documento y no borran versiones ni registros del padrón. Las celdas de otras áreas
siguen protegidas. Las filas nuevas vacías no se incorporan.

El formulario NO se monta dentro de un fragmento periódico. La hoja colaborativa
Anexo XIX conserva su editor concurrente, autoguardado y sincronización por área.
La navegación por tabs no solicita rerun al cambiar de pestaña.

Este modo de captura explícita **no autoguarda teclas todavía no enviadas**:
Streamlit solo entrega esos valores al pulsar Guardar. Se comunica en pantalla
que es necesario guardar antes de navegar o cerrar. Si falla la persistencia de
un envío, se conserva el documento capturado en `session_state`, se muestra el
error y no se confirma éxito. Esto no equivale a respaldo del navegador tras
cerrar sesión; no se promete recuperar texto que nunca fue enviado.

## Conectividad sin botones intermedios

Expediente, PDA y DUA están en secciones secundarias cerradas. Las fuentes del
alumno se consultan sin copiarlas como NEE. Los PDA se vinculan por ID exacto y sus
campos se incluyen automáticamente. La escuela se recuerda por ID, no por índice
ni por coincidencia parcial del nombre.

El mismo botón permite guardar, completar vacíos con datos documentados, preparar
propuestas locales, solicitar IA o enviar a Dirección. Para propuestas locales o
IA se exige revisar primero la propuesta/resumen y confirmar con otro envío del
mismo formulario. No se transmite a IA un resumen distinto del consentido. El
ensamble reutiliza los validadores y protección de ediciones existentes. Un fallo
de la ayuda opcional no impide guardar la captura manual.

Descargas, archivo en expediente y regreso están agrupados al final. Se indica
que corresponden al último envío, no al texto sin enviar que aún está en el form.
La vista anterior sigue disponible como herramienta complementaria.

## Verificación

`tests/test_planeacion_cero_friccion.py` prueba los cuatro roles, envío único,
preservación de metadatos y fuentes, filtros por ID, protección de celdas ajenas,
fallos de guardado y consentimiento. Las regresiones del Anexo XIX deben seguir
verificando documento único, concurrencia y conservación de aportes.
