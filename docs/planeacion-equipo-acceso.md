# Continuar la planeación grupal del equipo

La maestra de apoyo inicia el Anexo XIX y confirma su guardado. No necesita
enviarlo a Dirección para que los especialistas asignados puedan colaborar.

1. Abre **Planeación e intervención**.
2. Elige **Planeaciones del equipo**. Es la entrada inicial de Comunicación,
   Psicología y Trabajo Social; las maestras de apoyo también pueden consultarla.
3. Selecciona tu **Escuela del trabajo compartido**.
4. Mantén **Planeación grupal · Anexo XIX**, filtra por grado y grupo y elige
   el documento. La lista incluye fecha/hora y los borradores guardados.
5. Escribe directamente en la columna de tu área. El resto del formato queda
   protegido y visible. Se conserva un único documento, sin copiarlo.
6. Usa **Guardar mi aportación** y comprueba la confirmación. También puedes
   descargar el respaldo de tu aportación.
7. **Actualizar aportaciones del equipo** recupera los cambios ya guardados
   por las otras áreas; primero intenta guardar tu trabajo pendiente.

Si no aparece un documento recién creado, pulsa **Actualizar planeaciones
del equipo**. Si sigue ausente, comprueba su guardado, la escuela seleccionada
y las asignaciones oficiales. No crees una copia para resolver la visibilidad.

**Mi formato de especialista** conserva la planeación propia de cada área.
Los PI se consultan mediante **Plan de intervención · Anexo XXI**.

## Protección y límites

- No cambia la matrícula, los permisos, la configuración de IA ni el historial.
- La consulta sigue comprobando todos los alumnos y la escuela asignada.
- Una letra de grupo pendiente no oculta una guía existente, pero tampoco
  permite enlazar automáticamente otro grupo o incorporar alumnos sin identificarlo.
- Recibir un cambio del editor no equivale a guardarlo: el respaldo del editor
  se conserva hasta confirmar la persistencia, también durante reintentos.
- Esta mejora no convierte Windows 7/8.1 ni Chrome antiguo en plataformas
  compatibles. El error `Object.keys(...).toSorted is not a function` procede
  del cliente Streamlit. No se parchean sus paquetes ni se reduce la seguridad.
- No se añade autenticación persistente ni se garantiza recuperar una sesión
  tras reiniciar el servidor. Antes de publicar, cerrar o recargar, confirma el
  guardado y descarga un respaldo si hay cambios pendientes.

## Verificación

Pruebas con datos ficticios: acceso de las tres áreas, exclusión de alumnos
ajenos, modalidad individual/grupal, documentos eliminados, grupo pendiente,
edición de la columna propia, fallo de persistencia y recuperación en el mismo
documento. Las pruebas de interfaz seleccionan explícitamente el formato propio
cuando no están comprobando la nueva entrada compartida.
