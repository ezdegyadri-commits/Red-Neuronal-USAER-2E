# Redacción contextual de EPP

La EPP abre el informe completo y reúne los instrumentos en la parte superior.
La carga revisada y las aplicaciones digitales alimentan el mismo documento y
alumno. El conteo distingue las cuatro áreas y cuenta evaluaciones con resultados.

## Flujo

1. Subir un informe de resultados o aplicar un formato digital disponible.
2. Revisar la síntesis, identificar instrumento y fecha, y vincular los resultados.
3. Autorizar el uso de los hallazgos anonimizados en los motores configurados.
4. Usar **Redactar EPP Automáticamente** para los campos vacíos de la función,
   o **Autocompletar** junto a un campo para trabajar únicamente ese apartado.
5. Revisar la redacción incorporada. El diario confirma el guardado por separado;
   el guardado maestro continúa disponible.

No se eligen proveedor ni apartado en un diálogo. Las dos vistas de EPP usan
el mismo servicio, validación y motor. Los formatos y reglas digitales existentes
se conservan; no se implementan baremos nuevos ni calificación psicométrica por IA.

## Protección del documento

- Se mantienen los permisos canónicos, incluidos los campos compartidos.
- La coordinación autorizada puede integrar conclusión, NEE y BAP; cada
  especialista redacta sus campos habilitados con la evidencia de todo el equipo.
- La redacción global conserva los campos escritos y las marcas No se requiere.
- Las propuestas se validan por estructura, destino y referencias de evidencia
  antes de modificar el borrador. No autorizan ni validan el informe final.
- Un cambio de hallazgos durante la generación conserva la propuesta para consulta
  y exige redactar con la evidencia actual. Las ediciones posteriores no se pisan.
- El diario usa la mezcla por campo existente, conserva revisiones e historial y
  distingue el borrador visible de una confirmación remota. Un fallo permite
  reintentar sin borrar el texto ni bloquear nuevas ediciones.

## Procesamiento y datos

Se envía una solicitud JSON conjunta en el caso exitoso. Hay una cola acotada,
sin acceso a session_state desde el trabajador, y un solo trabajo activo por
cuenta/documento. Los fallos transitorios permiten un respaldo acotado mediante
los proveedores ya configurados. No hay un bucle ilimitado de reintentos.

Se retiran identificadores conocidos antes de enviar los hallazgos textuales;
esta reducción automática no sustituye la revisión del profesional. La lectura
visual de un archivo con Gemini requiere autorización específica para ese archivo,
admite hasta 5 MB y produce una síntesis revisable de resultados ya registrados.
La lectura local sigue disponible. No se envían archivos a otros proveedores
para el OCR visual. Los registros de errores no incluyen el contenido ni claves.

Los indicadores muestran etapas; el porcentaje en espera no pretende medir el
avance interno del proveedor. Las credenciales, límites y disponibilidad reales
de los proveedores siguen siendo condiciones externas al módulo.

## Verificación

Pruebas con matrícula ficticia y respuestas de IA simuladas: permisos,
anonimización, campos omitidos, concurrencia, validación JSON, respaldos,
instrumentos, documento completo, incorporación visible y edición durante espera.
La comprobación local del navegador usa tests/fixtures/epp_viva_app.py;
no se crean alumnos ni documentos de producción y no se consumen APIs reales.
