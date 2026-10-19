# Anexo XIX: colaboración sin mover la edición de otra sesión

El documento compartido se abre por ID y permanece fijado en `session_state`
hasta que la persona usa Regresar. La fecha de guardado se muestra aparte del
selector: las etiquetas variables de Streamlit podían restablecer la selección
cuando guardaba otra área. Para cambiar grupo primero se envían las celdas
visibles; un error conserva la hoja abierta.

Comunicación, Psicología y Trabajo Social escriben únicamente su columna y sus
observaciones en el formato vivo. El mismo botón Guardar recoge ambos. La
maestra autora conserva el control del formato; los permisos se comprueban en
servidor, no mediante campos enviados por el navegador.

La vista consulta el mismo ID cada 10 segundos y actualiza otras áreas sin
recrear los nodos editables. La huella de especialista incluye el área, la cuenta,
la matrícula y sus celdas editables; no incluye el texto de solo lectura de apoyo.
La actualización conserva el aporte base propio para que el servicio siga
detectando otra sesión que haya editado la misma área. El autor recibe solo los
aportes, sin reemplazar su texto ni adelantar su revisión base.

Guardar/autoguardar no bloquean la escritura. El acuse corresponde al nonce
persistido: recibir texto o aplazar por cuota no significa haber guardado. Si se
redacta durante un envío se conserva ese texto y se envía después del acuse.
El respaldo inmediato utiliza sessionStorage separado por pestaña, cuenta, área
y documento. No sustituye el guardado en servidor; no cerrar una pestaña con
confirmación pendiente sin descargar su respaldo.

El autoguardado del XIX agrupa escrituras (15 segundos en aportes y 15–29 en
apoyo), conservando presupuesto, reintento y versiones existentes. Guardar un
aporte idéntico confirmado no crea otra versión. No hay migración, borrado,
ampliación de permisos ni cambio de Gemini.

## Alcance de sincronización

Se reutiliza la lectura autorizada y su caché de hasta 60 segundos; las escrituras
confirmadas del proceso se observan antes. No es transmisión de cada pulsación
ni garantía de latencia instantánea. El candado existente es por proceso, no un
nuevo coordinador distribuido. No se modifica esa arquitectura en este parche.

## Verificación sin registros reales

- `tests.test_planeacion_sincronizacion`: etiquetas estables, actualización de
  apoyo para las tres áreas, conflictos propios, matrícula y guardados idénticos.
- `tests.test_planeacion_acceso_equipo`: dos sesiones fijadas en grados distintos,
  cambio de orden y contenido de apoyo, fallo y recuperación del guardado.
- `tests.test_planeacion_compartida`: conservación de aportes entre las tres áreas
  y autor, permisos y conflictos de versión.
- `node tests/planeacion_editor_cliente.cjs`: escritura durante el envío, acuses
  por nonce, actualización de solo lectura sin sustituir el nodo activo,
  respaldo por pestaña y salida protegida.

La publicación debe conservar los archivos ajenos al parche y las versiones
históricas. Las comprobaciones de producción son de lectura, sin ensayos sobre
planeaciones del personal.
