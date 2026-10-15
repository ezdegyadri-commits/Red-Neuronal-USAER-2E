# Planeación clara y borradores recuperables

La NEE usa la redacción del Manual USAER: verbo y qué necesita el alumno, por ejemplo «Necesita fortalecer la atención sostenida». La captura de la maestra y la conclusión revisada de EPP tienen prioridad. Cuando faltan, se muestra una propuesta educativa para revisión. BAPSE se consulta como antecedente contextual.

La limpieza de copias antiguas se limita a fragmentos mecánicos reconocibles de instrumentos en el campo NEE. Conserva el texto anterior en la versión/documento, propone una NEE legible y completa objetivo/descriptor vacíos; no sustituye objetivos o descriptores ya escritos. No se modifica el padrón ni el expediente. Vaciar después una propuesta no provoca que se regenere al abrirla. El ensamble de actividades usa la misma prioridad docente de NEE.

En la hoja, todo el cuerpo de las celdas de redacción es editable. Las citas oficiales y la procedencia permanecen en conexiones/metadatos y en el apartado documental de la descarga; no se anteponen a un fragmento editable. Las actividades conservan la secuencia propuesta sin mensajes técnicos ni bloques de fundamento dentro de la redacción.

Las filas automáticas de contexto sin actividades, tiempos o recursos se conservan en los datos, pero no ocupan espacio en la hoja ni en el PDF. Añadir una fila abre un espacio de edición explícito. Los índices originales se conservan para que editar o retirar una fila visible no afecte a otra oculta. Los pendientes ignoran metadatos de procedencia y ofrecen enlaces al campo, tabla o sección pertinente. En la hoja, los enlaces abren el apartado plegado y enfocan su celda.

Los borradores ofrecen edición y descargas PDF/JSON. La descarga PDF es diferida: se autoriza y captura la instantánea en el hilo de la pantalla; ReportLab se ejecuta al descargar sin leer la sesión desde otro hilo. Eliminar exige confirmación y autoría, registra otra versión y oculta el documento de la lista vigente. «Mostrar borradores eliminados» permite restaurarlo. Los documentos enviados o revisados no se eliminan como borradores; una sesión antigua no puede revivir un borrador eliminado ni reemplazar una versión reciente.

Pruebas: `test_planeacion_clara` cubre NEE heredadas, prioridad docente en generación, conservación de redacción, índices, destinos, descarga diferida, eliminación, restauración y conflictos. Los recorridos de apoyo y especialistas, PDF y estabilidad usan únicamente datos ficticios.
