# Continuidad y colaboración de planeación

UI → servicios → repositorio existente. Los enlaces, aportes, seguimiento y contexto se almacenan en el payload versionado de Planeaciones; no se crean hojas duplicadas ni se cambia el padrón.

- Las fuentes se vinculan por alumno, documento y revisión, no por semejanza de nombres. La EPP solo aporta apartados revisados. El PI conserva vigencia de uno a tres cursos. Fuentes ambiguas se señalan, no se eligen automáticamente.
- El coordinador conserva el editor general. Cada participante autorizado escribe únicamente su aportación de área; Dirección revisa. Una aportación invalida la aprobación anterior y requiere nueva integración/revisión. Hay control de versión y respaldo ante conflictos.
- Una guía anual por escuela/ciclo/grado/grupo es la fuente compartida. Otras planeaciones muestran una referencia filtrada a sus alumnos, actualizable desde el expediente. Grupos mezclados no se presentan como una guía única.
- Modalidad de padrón y organización de sesión son distintas. Se permite inclusión explícita de atención individual en una sesión grupal. Modalidades desconocidas requieren aclaración, no se convierten en grupales.
- El contexto escolar/comunitario se mantiene para las solicitudes educativas, minimizado antes de la IA. Regenerar una planeación existente exige revisar y aplicar la propuesta; conserva sesiones editadas y eliminadas. No se envían archivos originales ni se aprueba con IA.
- El seguimiento registra resultados observados sustentados en evidencias, no actividades previstas ni fechas futuras. Se incorpora a siguientes planeaciones y al PDF. No sustituye la revisión profesional ni emite diagnósticos clínicos.

Verificación: pruebas unitarias de continuidad/permisos/modalidad/IA simulada, pruebas AppTest de interfaz y recuperación, y render PDF con datos ficticios. No requieren Google Sheets ni Gemini reales. En Windows AppTest requiere permitir conexiones internas locales del entorno de pruebas. No modificar firewall ni configuración de producción para ejecutar pruebas.

Reversión: revertir el commit de publicación; no borrar versiones ni metadatos ya guardados. Los campos añadidos son opcionales y compatibles con documentos existentes.
