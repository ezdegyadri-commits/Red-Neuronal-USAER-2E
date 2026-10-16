# Anexo XIX compartido y continuidad de planeación

## Alcance

La maestra de apoyo crea la guía de un grado y grupo. Los especialistas abren
Trabajo colaborativo, eligen una escuela de su asignación y el documento por
escuela, grado, grupo, ciclo, trimestre, fecha/hora, alumnos e identificador.
Escriben sobre el mismo formato; cada área solo puede modificar su columna.
El formato propio del especialista sigue disponible, con antecedentes,
referentes, DUA y generación de propuestas revisadas. La modalidad Individual
solo ofrece alumnos registrados como individuales; Mi intervención permite
organizar la atención del especialista sin crear otra guía XIX.

Referente: Manual USAER SEGEY, páginas PDF 88 y 162 (páginas impresas 78 y 152).
https://educacion.yucatan.gob.mx/multimedia/publicaciones/220121_Manual_USAER.pdf

## Sin duplicar captura

- La guía incorpora, al abrirse, las altas grupales autorizadas del mismo grado
  y grupo. No retira alumnos anteriores, no cambia su modalidad ni toca otras escuelas.
- El maestro regular y NI/RI se reutilizan del padrón; las NEE registradas y la
  EPP vinculada sustentan una descripción inicial breve. No se copia BAPSE ni se
  deduce un diagnóstico. Si falta NI/RI o docente, la revisión lleva a la celda.
- La situación final es editable desde junio del año de cierre del ciclo. Los
  resultados ya existentes se conservan visibles; no se inventan promociones.
- El envío de la guía revisa sus propios campos, no obliga a llenar además un
  formato trimestral oculto.

## Evaluación individual

Al final de las tablas se propone una escala complementaria, por alumno e
indicador, vinculada con las actividades de su planeación. La valoración inicial
es Sin valorar: no representa un resultado observado. Opciones: Requiere apoyo
constante, En proceso con apoyos, Logrado con autonomía y No observado.
Se pueden editar los indicadores, actividades y observaciones y añadir o retirar
filas. Los indicadores retirados no reaparecen al abrir el documento.
Esta escala es una herramienta docente editable, no un nuevo formato oficial.

## Persistencia y compatibilidad

- Se utiliza la misma hoja versionada Planeaciones_Versiones; no hay migración
  masiva, eliminación física ni reescritura de versiones previas.
- Los aportes antiguos mantienen su integración y conciliación humana. Las
  celdas vivas nuevas se guardan como aportes explícitos del profesional.
- Cambios de áreas diferentes pueden partir de una misma revisión. Los cambios
  sobre la misma área se rechazan si otra sesión ya la modificó.
- El autoguardado conserva el presupuesto de escrituras y reintentos. Texto
  recibido en sesión NO equivale a guardado recuperable: la interfaz distingue
  ambos estados. Una pestaña guarda temporalmente texto aún no transmitido en
  sessionStorage; no sustituye el respaldo confirmado del servidor.
- Un acuse de persistencia no invalida la huella de las celdas abiertas. La
  conciliación del autor solo incorpora aportaciones ajenas si no hubo cambios
  concurrentes en el trabajo del autor.
- Este candado es por proceso: no prometer coordinación distribuida entre
  varias instancias sin un coordinador externo. La configuración de producción
  debe mantener una instancia escritora hasta verificar esa integración.
- El autoguardado descrito corresponde a planeación y aportaciones; no publica,
  firma ni envía automáticamente productos. No implica que todos los otros
  módulos de la plataforma ya tengan autoguardado de borradores.

## Alta e integridad

La fecha de nacimiento calcula edad al 1 de septiembre del ciclo vigente.
Fecha_Nacimiento es una columna aditiva; los registros previos quedan intactos.
Capturas nuevas y comparaciones de planeación normalizan grado (3°, 3o, 3º →
3°) y grupo. No se realiza una normalización masiva del padrón histórico.
La CURP se contrasta con su fecha de nacimiento. La ayuda propone únicamente
16 posiciones: las dos posiciones finales se verifican en la constancia RENAPO.
No se asigna una CURP oficial ni se consulta un tercero con datos del alumno.

## Caso del video de Marycruz

El problema reportado es recuperar un documento entre copias y volver al editor
correcto. La apertura preserva el autoguardado pendiente, utiliza su revisión
recién confirmada cuando corresponde y limpia el panel auxiliar del documento
anterior. La lista muestra alumnos, modalidad, grado, grupo y fecha/hora.
La eliminación de borradores sigue siendo recuperable desde la papelera.

## Recuperación del editor y confirmación de guardado

- El formato se monta directamente con componentes v2 de Streamlit 1.65,
  mecanismo ya usado por el corrector de escritura. No carga un iframe ni
  depende de la ruta externa del componente, su caché o un saludo postMessage.
  Se reutilizan el mismo HTML, estilos y renderizador de tablas; no se sustituye
  la hoja tradicional ni se modifican los documentos para mostrarla.
- Un adaptador acotado entrega los datos del componente y sus eventos al mismo
  contrato existente. No escucha mensajes externos ni hace solicitudes de red.
  El estado de edición se conserva entre renderizados y se liberan los relojes,
  observadores y avisos al desmontar la vista.
- Cada envío tiene un identificador. Solo el acuse de ese envío libera sus
  cambios; un acuse anterior no puede borrar texto más reciente.
- Si la respuesta tarda 15 segundos, se reintenta el mismo envío. Durante una
  espera de guardado se permite continuar escribiendo; la respuesta anterior
  no reemplaza lo escrito después. Las acciones estructurales siguen protegidas.
- El respaldo de la pestaña se conserva mientras falta confirmar la escritura
  recuperable. Recibir texto en la sesión no autoriza borrar ese respaldo.
- Un rechazo deja el texto disponible y detiene los reintentos automáticos de
  esa edición inválida. Un respaldo de otra revisión no se aplica ni elimina
  automáticamente: se ofrece su descarga para revisión.
- La confirmación se muestra con el documento actual tras el autoguardado,
  no con una copia anterior al intento de persistencia.

La espera y pérdida de conexión se verifican con un servidor ficticio aislado
(`tests/servidor_editor_guardado.cjs`); jamás se simulan fallos en la base real.

## Verificación

Ejecutar módulos de pruebas en procesos separados: algunos fixtures de
Streamlit reemplazan adaptadores globales, y el descubrimiento global sin
aislamiento puede contaminar las siguientes pruebas. Nunca usar la base real
para simular aportaciones ni para probar eliminación.
