# Intervención de planeación: avance y pendientes

Rama: feat/intervencion-planeacion-integrada. No desplegada.

## Referencias localizadas y leídas

- Guía Planeación. 2025-2026.docx.pdf: cuatro páginas.
- Instrumento planeacion USAER.docx.pdf: dos páginas, Zona 001, ciclo 2026–2027.

La guía vincula NEE priorizadas, PDA, descriptores observables, actividades,
temporalidad, recursos y evaluación. Permite secuencias, proyectos o actividades
ordenadas; no exige imponer inicio/desarrollo/cierre a toda intervención.
El instrumento contiene catorce indicadores y una valoración separada de coherencia,
con escala 0–3. services/metas_instrumento.py ya conserva estos textos y escala;
su existencia no demuestra que la revisión esté conectada a toda planeación.

## Diagnóstico confirmado y corrección inicial

ui/planeacion_papel.py renderiza materiales desde herramientas y conexiones;
ui/planeacion_viva.py también lo hace desde la ficha del alumno. Todos llamaban
ui/planeacion.py:_materiales con el mismo prefijo de documento. Cuando coinciden
en una ejecución, se duplican el uploader y los demás controles de materiales.

Se separan las claves visuales por documento e instancia estable; la identidad
del borrador, las lecturas procesadas y las operaciones de persistencia siguen
usando el prefijo original. Se cubren todas las claves del panel, no solamente
el uploader. No hay claves aleatorias ni cambios al padrón o documentos reales.

Pruebas iniciales: 33 pasan, incluyendo tres paneles de materiales en la misma
ejecución, estabilidad de claves en rerun, conservación de lecturas en sesión,
extracción documental de NEE y vínculo EPP–planeación con datos ficticios.
No equivalen a una prueba completa de OCR real, carga binaria o concurrencia.

## Mapa de componentes a reutilizar

- Interfaz y navegación: ui/planeacion.py, planeacion_viva.py, planeacion_papel.py.
- Formato y modalidad: services/planeacion_papel.py, planeacion_modalidad.py.
- Necesidades: services/nee_documentales.py, planeacion_nee.py,
  planeacion_intervenciones_nee.py.
- Generación: services/planeacion_generacion.py y ai/planeacion.py.
- Rúbrica institucional: services/metas_instrumento.py.
- Catálogos: services/padron_catalogos.py y utils/escolar.py.
- Importador actual: ui/pages.py:alta_page. Su mensaje indica que conserva las
  CURP existentes sin actualizar: falta implementar conciliación revisable.

## Trabajo pendiente, no declarado terminado

1. Reproducir el cambio involuntario de modalidad; probar ida/vuelta y exportación.
2. Verificar carga de archivos reales sintéticos y recuperación de adjuntos que
   ya estuvieran seleccionados en widgets antiguos antes del despliegue.
3. Auditar la confirmación y comparación de NEE de EPP nueva y su reutilización;
   probar OCR con fuentes sintéticas, sin enviar expedientes reales a IA.
4. Completar el flujo NEE–PDA confirmado–descriptor con nombre real–actividades
   factibles–apoyos–evaluación, sin inventar PDA oficiales ni nivel de desempeño.
5. Conectar la rúbrica y distinguir datos estructurales de juicio pedagógico.
6. Medir clics antes/después y simplificar borradores con eliminación reversible.
7. Incorporar planeación grupal anual sin migrar ni fusionar históricos trimestrales;
   mantener la hoja compartida del equipo, con permisos por aportación.
8. Diagnóstico de integridad de datos de solo lectura y migración reversible
   separada: no modificar datos de producción para probar normalización.
9. Importación idempotente con altas y actualizaciones propuestas, conflictos,
   confirmación, historial y estadísticas desde una fuente canónica.
10. Ejecutar los escenarios A–H, medir concurrencia de 15–25 sesiones y comprobar
    recuperación/guardado antes de solicitar publicación de esta intervención.

No se han medido todavía clics, latencias ni capacidad de usuarios simultáneos.
No se ha modificado infraestructura, producción ni permisos.
