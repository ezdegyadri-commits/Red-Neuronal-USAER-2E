# Visibilidad de planeaciones anteriores

Los documentos anteriores al campo `modalidad_planeacion` se clasificaban como otros formatos. Una planeación individual con trabajo redactado podía quedar fuera de la pestaña Individuales aunque su historial siguiera completo.

Después de comprobar los permisos, el listado proyecta la modalidad individual cuando todos los IDs del documento corresponden de forma exacta a alumnos con atención individual de la misma escuela en el padrón autorizado. Conserva ID, revisión, tablas, filas vacías, texto y demás metadatos. No infiere por nombre ni convierte documentos ambiguos en guías grupales. Las modalidades declaradas se respetan.

Consultar no escribe en Sheets, no crea documentos ni reescribe versiones históricas. Si el usuario edita y guarda después, el protocolo normal añade una versión al mismo documento. Las tarjetas antiguas sin clasificación y con un solo alumno muestran su nombre; un grupo declarado continúa identificándose por grado y grupo. Al cambiar el conjunto de documentos del repositorio, los filtros previos vuelven a Todos para que una recuperación no quede oculta.

Pruebas con datos ficticios: dos tarjetas individuales visibles, clasificación con ID y escuela exactos, borradores históricos intactos, preservación de una fila extensa y otras vacías, modalidades explícitas respetadas, ausencia de alumnos no autorizados y filtros anteriores restablecidos. No se incluyen datos de alumnos reales en código ni pruebas.

El repositorio se consulta al entrar y se actualiza en un fragmento cada diez segundos mientras está abierto. La actualización manual no es requisito ni aparece como paso del flujo principal. Se reutiliza la caché compartida, sin invalidarla por cada docente; la clasificación de documentos anteriores se aplica en cada consulta. Al abrir el editor, el fragmento del listado deja de montarse: no sustituye ni recarga la edición activa. Las consultas fallidas se reintentan en el siguiente ciclo, sin crear borradores ni escribir datos.
