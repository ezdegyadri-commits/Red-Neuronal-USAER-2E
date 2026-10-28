# Intervención integrada de planeación — 28 de octubre de 2026

Rama: `feat/intervencion-planeacion-integrada`. Preparada localmente, sin despliegue,
reinicio ni escrituras de prueba en la base real. Esta verificación automatizada
no equivale a una validación con personas en producción.

## A. Diagnóstico técnico

Se consultaron **Guía Planeación. 2025-2026.docx.pdf** (4 páginas) e
**Instrumento planeacion USAER.docx.pdf** (2 páginas, Zona 001, ciclo 2026–2027).
La guía admite actividades ordenadas, secuencias y proyectos. El instrumento
contiene 14 indicadores y una valoración adicional de coherencia, escala 0–3.

Problemas comprobados:

- Materiales reutilizaba claves desde distintas ubicaciones.
- Deseleccionar modalidad podía devolver `None` y activar Individual.
- El importador omitía las CURP existentes, sin actualización revisable.
- El generador contenía instrucciones contradictorias y cantidades que podían
  exceder las sesiones disponibles de Psicología.
- Sus propias actividades automáticas podían invalidar la caché de generación.
- El payload XML no recorría íntegramente el anonimizado del resumen.
- Una lectura colaborativa de una versión anterior podía llegar tarde y volver
  a mostrar datos viejos. El acuse asíncrono no propagaba siempre la señal de
  compatibilidad de las pestañas antiguas.

## B. Cambios y dependencias

| Área | Componentes principales | Resultado |
| --- | --- | --- |
| Estabilidad | `ui/planeacion.py`, `planeacion_viva.py`, `planeacion_papel.py` | Claves por documento/instancia, recuperación de archivos seleccionados y modalidad estable. |
| EPP → NEE | `services/nee_documentales.py`, `documentos_sintesis.py`, `planeacion_necesidades.py`; `ui/documento_sintesis.py` | Origen, revisión, prioridad y fusión conservando fundamentos. Sólo lo validado alimenta el catálogo del alumno. |
| Cadena pedagógica | `services/planeacion_generacion.py`, `planeacion_calidad.py`; `ui/planeacion_calidad.py` | PDA confirmado, descriptor con nombre y actividades por NEE mediante referencias explícitas. |
| IA | `ai/documento_json.py`, `planeacion.py`, `planeacion_completa.py`; `ui/planeacion_tareas.py`, `planeacion_edicion.py` | Trabajos acotados en segundo plano, validación JSON, control de doble envío y propuestas protegidas contra cambios concurrentes. |
| Hoja anual | `services/planeacion_periodo.py`, `planeacion_grupo_unico.py`, `planeacion.py` | Nueva guía anual compartida, periodos internos y versiones; trimestrales anteriores separados. |
| Borradores | `ui/planeacion_repositorio.py`, `planeacion_borradores.py` | Continuar, copia adaptada y eliminación reversible. La guía única permite añadir alumnos en vez de duplicarla. |
| Padrón | `services/padron_importacion.py`, `padron_integridad.py`; `ui/padron_importacion.py`, `padron_integridad.py`, `estadisticas.py`, `pages.py`; `utils/escolar.py` | Excel revisable por CURP, escritura por ID, historial en una petición, grupo desplegable y diagnóstico privado de Dirección. |
| Colaboración | `ui/lecturas_documento.py`, `planeacion_anexo_compartido.py`, `guardado_asincrono.py` | Descartar lecturas de otra versión y proteger el guardado frente a listados anteriores. |

Se reutilizan autorización, expediente, currículo, versionado, papel, OCR y
estadística. No se crea otra base ni se renombran columnas centrales. El alta
manual se conserva. Las consultas remotas y sus permisos no se sustituyen por
un catálogo paralelo.

## C. Mejoras pedagógicas

**Alumno → NEE confirmadas → PDA → descriptor observable → actividades → apoyos → evaluación.**

Las frases explícitas conservan su fundamento. Reformular “Dificultad para…”
produce una propuesta pendiente de revisión, no una necesidad validada. No se
transforma un diagnóstico aislado en NEE. La fusión conserva sus fuentes y exige
confirmación nueva; las versiones previas permanecen disponibles.

El PDA oficial se toma literalmente del currículo vinculado. Sin fuente
verificable se informa que hace falta selección o confirmación contextualizada.
El descriptor se arma localmente con nombre real, verbo presente y complemento
observable; no es necesario transmitir ese nombre a IA.

La generación parte del desempeño documentado, respeta edad e intereses y no
deduce dominio por grado o diagnóstico. Se validan cantidad, contextos, evidencia
y ausencia de repeticiones. Cada actividad vinculada se integra en su bloque de
NEE, sin otra copia automática en la dosificación. Se conservan PDA, descriptores
y redacción docente ya capturada.

La rúbrica distingue presencia estructural, señales de vocabulario y sugerencias
de IA. Los 14 indicadores y su escala original se conservan. La valoración 0–3
la registra el profesional; no hay calificación definitiva automática ni una
validación obligatoria añadida al guardado.

## D. Simplificación de navegación

Conteos de acciones desde la misma pantalla, sin contar escritura o desplazamiento.
Son conteos de controles del recorrido, no tiempos medidos con docentes.

| Acción | Antes | Ahora |
| --- | --- | --- |
| Abrir guía del grupo elegido | Seleccionar todos + abrir: 2 acciones | Alumnos precargados + abrir: 1 acción. |
| Eliminar borrador desde tarjeta | Respaldo + mostrar opciones + eliminar + confirmar: 4 acciones | Eliminar + confirmar: 2 acciones, sin borrar historial. |
| Llegar a copia adaptada | Continuar + herramientas de alumnos: al menos 2 acciones | Duplicar: 1 acción; destinatarios y periodo se siguen confirmando. |
| Actualizar CURP existente con Excel | No disponible en ese importador | Revisar + confirmar, con aceptación explícita de la vista previa. |

La espera de generación y reformulación no retiene el evento de Streamlit. Los
resultados no sustituyen silenciosamente lo escrito mientras se esperaba. Los
indicadores muestran etapas; no prometen porcentajes o tiempos ficticios.

## E. Integridad de datos

Se realizó una consulta real de sólo lectura de encabezados, nomenclaturas,
estados y referencias. El diagnóstico privado, respaldo acotado de campos y
equivalencias quedaron fuera del repositorio. No se descargaron cuerpos de EPP
ni contenidos de planeaciones. No se aplicaron normalizaciones reales.

Representación: `Grado = 2°`, `Grupo = A`, visualización `2° A`. Se reconocen
`2A`, `2°a`, `2º A`; las contradicciones se detienen. Los grupos se eligen en un
desplegable que conserva también valores históricos para revisión. No se
fusionan personas por nombre.

La propuesta reversible conserva valores anteriores por ID y precondiciones.
Se prueban simulación y reversión sobre copias. Para aplicarla realmente faltan
respaldo completo, validación de equivalencias y referencias escolares, relectura
y comprobación posterior. Los trimestrales no se migran automáticamente.

Excel admite `.xlsx` de hasta 16 MB y 128 MB descomprimidos, con encabezados
simples o institucionales de dos filas. Los no reconocidos se muestran antes de
confirmar. Una ausencia o campo vacío no causa baja ni borrado. Categorías
desconocidas, traslados y duplicidades ambiguas requieren corrección.

Altas, cambios e historial usan una petición `batchUpdate` con texto literal.
La fila destino se identifica por ID, incluso si existe una copia conservada de
la CURP. Se comprueba la base antes de confirmar y se reconocen reintentos ya
aplicados. Se invalidan las cachés para que las estadísticas deriven de la misma
fuente. No se inventan indicadores para campos ausentes.

## F. Pruebas y aceptación

La matriz entregada comprende **57 módulos y 685 ejecuciones aprobadas (589 casos distintos por ID)**. Incluye
servicios, AppTest, contratos del editor y exportación PDF. La matriz usa la última ejecución de cada módulo. Algunas clases importan o
heredan casos compartidos; por eso se informa también el total de IDs distintos.

| Escenario | Verificación | Límite |
| --- | --- | --- |
| A — EPP/planeación | PDF sintético con OCR simulado, confirmación/versiones, varias NEE, aislamiento, PDA/descriptor/actividades/evaluación por bloque. | Falta OCR de fotografías representativas y proveedor real. |
| B — Navegación | Modalidad estable, ida/vuelta, claves únicas, adjuntos previos y exportación correcta. | Falta recorrido visual con maestras en navegadores reales. |
| C — Anual | Crear, guardar y reabrir misma hoja; periodos internos; trimestrales intactos. | Sin migración automática de históricos. |
| D — Normalización | Equivalencias, contradicciones, referencias y reversión exacta en copias. | Propuesta real sin aplicar. |
| E — Excel | Altas/cambios, duplicados, escuela, historial, acuse perdido y fila activa por ID. | Sheets simulado; falta piloto autorizado. |
| F — Borradores | Apertura, copia adaptada, eliminación versionada y recuperación. | Se conserva la guía única institucional. |
| G — Concurrencia | 20 escritores ficticios aislados; 15 reintentos producen una sola alta; cola IA acotada; conflicto obsoleto no pisa datos. | No demuestra capacidad de 20 sesiones reales en Cloud. |
| H — Coherencia | Incoherencia lectura/conteo, recomendaciones específicas, JSON validado, 14 indicadores sin notas automáticas. | No demuestra calidad pedagógica de un proveedor real. |

Se compararon fallos iniciales con la versión de partida. Se actualizaron
fixtures con etiquetas antiguas, lecturas externas no simuladas, texto PDF sin
normalizar saltos, acceso indebido a `session_state` desde workers y revisiones
que no cambiaban al simular un guardado. Se conservan las comprobaciones de
contenido, identidad y número de escrituras. Se añadieron regresiones de la
carrera de lecturas y la compatibilidad de acuses.

## G. Riesgos y dependencias

- El bloqueo y la comparación previa son por proceso. Una petición atómica de
  Sheets no ofrece compare-and-swap distribuido frente a otras aplicaciones.
- Las colas son locales y acotadas. Un reinicio pierde trabajos sin persistir;
  una propuesta de IA no constituye un respaldo durable del documento.
- La cola de propuestas admite ocho trabajos, dos en ejecución. En el ensayo
  de 20 solicitudes simultáneas las no admitidas reciben un aviso recuperable.
  No se promete atender 20 llamadas IA simultáneas ni eliminar cuotas.
- OCR local depende de Tesseract y español. Una lectura ilegible requiere otro
  escaneo o captura manual; no se inventa información.
- Claves, modelos, costes y latencia de proveedores requieren prueba externa.
  No se cambiaron credenciales ni se enviaron expedientes reales a IA.
- Un archivo `.xls` requiere guardarse como `.xlsx`.
- No se midió latencia completa de producción ni se validó visualmente esta
  rama en la sesión publicada. No se afirma “cero latencia” o “cero pérdidas”.

## H. Estado final

**Implementado y probado localmente:** claves y modalidad, NEE revisables y
priorizables, relación por NEE, rúbrica, redactor, IA en segundo plano, hoja anual,
borradores, importación, diagnóstico/simulación reversible y protección de
lecturas y acuses.

**Pendiente de prueba externa:** OCR representativo, proveedores reales,
importación piloto y capacidad de Streamlit Cloud.

**Preparado sin aplicar:** equivalencias del padrón real y respaldo acotado de
campos candidatos. Antes de migrar debe conciliarse el catálogo institucional;
no se reasignan alumnos por inferencia.

**No implementado deliberadamente:** fusión automática de expedientes, migración
automática de trimestrales, calificación pedagógica definitiva automática o una
garantía de concurrencia distribuida sobre Sheets.

**Publicación:** no realizada. Se conserva la condición del documento: aprobación
expresa antes de desplegar esta intervención.
