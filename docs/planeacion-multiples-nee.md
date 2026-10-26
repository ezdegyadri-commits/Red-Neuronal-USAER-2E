# Intervenciones independientes por NEE

En planeación individual, seleccionar varias NEE validadas de la EPP y agregar
sus apartados conserva un solo documento. Cada necesidad tiene objetivo,
descriptor de logro, apoyos, ajustes razonables, contextos, actividades,
temporalidad, recursos y evaluación propios. Aplica a Apoyo, Psicología,
Comunicación y Trabajo Social, en los formatos XXI, XXIII y XXV.

## Datos y continuidad

- `metadatos.intervenciones_nee` contiene bloques identificados de manera estable
  por documento, alumno y NEE. Repetir la selección no duplica los bloques.
- El catálogo validado vigente controla las opciones. Una NEE detectada,
  descartada, de otro alumno o de una fuente sin vínculo verificado no se agrega.
- Cada bloque conserva una instantánea de su fuente y revisión; actualizar la
  EPP no sobrescribe la redacción de una intervención ya guardada.
- El guardado usa las versiones, controles de autoría y recuperación existentes.
  No crea otra planeación ni escribe en la matrícula o en el expediente de origen.
- Las tablas históricas permanecen intactas. Las propuestas para alumnos sin EPP
  siguen su recorrido anterior. Las BAP de Trabajo Social permanecen separadas.

## Vistas y validación

La hoja viva ofrece selección múltiple y presenta tres secciones por necesidad:
NEE/objetivo/logro, apoyos/ajustes/contextos y actividades/tiempos/recursos/evaluación.
Las vistas alternativas comparten el mismo servicio y persistencia. El PDF usa
las mismas secciones y el resumen de antecedentes incorpora las intervenciones.

La revisión señala cada bloque incompleto y su celda. No exige duplicar
aprendizajes, necesidades o dosificación en las tablas anteriores al utilizar
estos bloques. Continúan las comprobaciones independientes del formato,
incluidas BAP, participantes, currículo y condiciones del plan anual cuando
correspondan. Las exigencias de sesiones en subgrupo no se aplican al nuevo
recorrido individual de especialistas.

La incorporación no inventa objetivos ni actividades: los apartados son
editables. No cambia el motor de generación con IA ni aplica una propuesta
automática sobre las intervenciones redactadas.

## Verificación

Pruebas con datos ficticios: selección múltiple en Streamlit, edición aislada,
reintento idempotente, dos alumnos con la misma necesidad, exclusión de NEE
descartadas, procedencia/revisión, continuidad JSON, eventos de la hoja viva,
validación sin doble captura y PDF para las cuatro funciones. Se ejecutan
también las suites existentes de planeación, EPP/NEE y formularios.

No se realizan escrituras de prueba en datos reales ni reinicios manuales de la
aplicación. La prueba local no sustituye una comprobación posterior en una sesión
real del personal.
