# Formatos conectados del equipo paradocente

Se mantiene el contrato de `Planeaciones_Versiones`, identidad por alumno, permisos y guardado existentes. No hay migración ni escritura en el padrón.

- `planeacion_papel.hoja` presenta XXIII para Psicología/Comunicación y XXV para TS. Psicología proyecta `equipo.competencias` y `sugerencia_familia` sobre celdas editables; los objetivos anteriores siguen accesibles. TS conserva su encabezado y lista de alumnos del Anexo XXV. La descarga usa la misma proyección.
- Una celda de sesión apunta a su ID estable, no a su índice. Contexto, fecha y recursos actualizan la sesión. `texto_formato` conserva la redacción final de la celda Actividades sin analizar ni desarmar texto libre. `sincronizar` usa esa redacción incluso si está vacía. El editor detallado, la revisión de actividades y las copias adaptadas consumen esa misma versión. Cambiar la configuración no descarta una edición; el ensamble de IA ya protege sesiones modificadas frente a su instantánea generada.
- Retirar una fila de sesión llama a `quitar_sesion` y mantiene las filas manuales; aportaciones ajenas y sesiones sin origen recuperable permanecen protegidas. Fechas/contextos de sesiones siguen pasando la validación del equipo. La huella del documento rechaza eventos obsoletos.
- `planeacion_social` obtiene BAP explícitas de fuentes vinculadas y permitidas. Extrae `BAP/Tipo de barrera/Acciones generales` de la conclusión EPP revisada o un apartado literal BAP de un registro. BAPSE continúa como antecedente; no se vuelcan preguntas/JSON a la tabla. Las filas llevan destinatarios y procedencia. No se infieren barreras de una condición, se completan resultados ni se actualizan fuentes originales.
- La continuidad local admite orientación ya escrita en el formato y un contexto elegido. Solo usa filas propias de cada alumno para orientar su actividad; las filas generales no se convierten en una evaluación individual. Las propuestas permanecen revisables y con aplicación explícita.

Referencias: Manual USAER SEGEY, anexos XXIII/XXIV y XXV/XXVI; ejemplo de Psicología y formatos de zona compartidos por Dirección. Los documentos privados y sus ejemplos nominales no se incluyen en el repositorio.

Verificación: `tests.test_planeacion_paradocente_viva` cubre edición/retirada/sincronización/PDF en las tres áreas, competencias y familia, fuentes BAP, datos ajenos y continuidad sin IA. Las suites existentes cubren creación y recuperación con matrícula ficticia, generación, autoría y guardado. La comprobación visual usa únicamente documentos ficticios.
