# Planeación simplificada · entrega de desarrollo

Estado: implementada, verificada y autorizada para publicación el 10 de octubre.
Referencia de partida: `D:/simplificacion_planeacion.md`.
Base: `1226a3f7e4e717d0c0378cb62e3ca1f60a0c49c2`.
Se leyó AGENTS.md y se buscaron los consumidores de las funciones afectadas.

## Lo que verá el equipo

Un recorrido principal de tres pasos: **¿A quién planeo? → Preparar con IA → Revisar y enviar**.

- Borradores en tarjetas, con Continuar y estado Por ajustar si Dirección devolvió observaciones. Todos los documentos propios siguen consultables mediante páginas; no se borran los antiguos ni se migran.
- Un selector de alumnos; la modalidad viene del padrón. Escuela y formato se omiten cuando ya se conocen. Reunir alumnos individuales requiere una elección explícita de sesión grupal.
- Ciclo y trimestre propuestos por fecha local, con ajuste avanzado. Los periodos de documentos existentes no se sustituyen.
- Un editor principal, Mi formato; desaparece la elección entre dos editores de la ruta habitual. La implementación anterior se conserva internamente para compatibilidad y pruebas, no como otra pantalla pública.
- Sesiones y referente resumidos; configuración ampliada únicamente cuando se activa Cambiar. El botón Preparar mi planeación usa el generador completo existente, sin llamadas automáticas de IA.
- Una casilla principal de privacidad y el resumen revisable en Ver qué se envía. La ayuda de ideas puntuales continúa como herramienta opcional, con su propio consentimiento cuando se utiliza.
- Subgrupo 1 inicial para nuevos documentos de especialistas. Psicología dispone de prioridades por competencias; Trabajo Social, barrera y contextos. Son orientaciones, no necesidades ni resultados inventados.
- NEE y BAP del PI precargadas solo desde una EPP vigente vinculada, conservando la confirmación profesional.
- Una tabla grupal principal por alumno. Los complementos XIX/XX y las herramientas horizontales permanecen disponibles bajo elección explícita.
- Guardar, Ver PDF y Enviar a Dirección juntos; PDF solo bajo demanda. El calendario del equipo también es opcional. No se modifica el cronograma.
- Más herramientas reúne materiales, referentes, evidencias, conexiones, aportaciones, seguimiento, sesiones, ideas adicionales, respaldos, versiones y ayuda.
- Guardar cambios y cerrar sesión confirma el guardado antes de salir. Si falla, conserva la sesión. Una aportación usa su guardado acotado: no se escribe como documento completo del coordinador.

## Conservación y arquitectura

No hubo escrituras, eliminaciones, migraciones ni modificaciones de permisos en Google Sheets o Drive. No se enviaron datos a Gemini ni se utilizaron expedientes reales para probar.

Sin cambios en `services/`, `data/`, `ai/`, `documents/`, dependencias, formatos oficiales ni esquema de Planeaciones_Versiones. Se reutilizan autorización, ensamblado, vínculos, huellas, versiones, conciliación y presupuesto de solicitudes existentes.

Las prioridades opcionales se conservan dentro del contenedor ya existente de configuración; para el generador se presentan como orientación educativa mediante su campo de enfoque. No se reemplaza el enfoque escrito ni se alteran los contratos de servicios.

La navegación impide reemplazar una edición pendiente, incluso al cambiar de modalidad. Conserva el resguardo JSON y las versiones históricas. Cerrar la vista PDF no cierra ni elimina el borrador.

## Verificación realizada

Comando: `python tools/probar_estabilizacion_sin_red.py`.
Resultado final: **327 pruebas correctas, 81.436 segundos**.

La suite bloquea solicitudes HTTP y conexiones externas; solo admite loopback para el funcionamiento interno de AppTest en Windows. Usa repositorios y respuestas de IA ficticios.

Incluye 15 pruebas nuevas para la interfaz de producción y sus protecciones: cuatro perfiles, Dirección, individual/PI, inferencia de modalidad, periodo, guardado/recuperación, herramientas opcionales, historia, privacidad, PDF bajo demanda, caché de IA con prioridades, cierre seguro y guardado colaborativo acotado. La batería heredada continúa comprobando las funciones y vistas anteriores, además de planeación, EPP, horarios, permisos, actas, cronogramas, trámites y novedades.

Persistencia sintética: 15, 20, 25 y 30 documentos. En 25 y 30 hubo 5 y 15 escrituras diferidas, respectivamente; se recuperaron sin duplicar versiones. La simulación del presupuesto mantiene un máximo de 45 reservas por ventana y difiere el excedente.

Se revisó la ausencia de cambios en capas de datos/servicios y se ejecutó `git diff --check` sin errores. Las dos guías de usuario ya describen la ruta nueva.

## Precisiones antes de publicar

- Tras recuperar el navegador integrado, computer-use comprobó la entrada y generación simulada de apoyo, las prioridades de Psicología y Comunicación y el formato XXV de Trabajo Social. Se verificó Trabajo Social a 390 × 844 píxeles. Se guardaron capturas locales de datos ficticios; no se publican esas capturas como expedientes reales. Esta revisión no sustituye pruebas de carga del servidor.
- Las simulaciones no equivalen a 25 sesiones reales simultáneas. Se mantiene la limitación anterior de un proceso escritor; no se ha introducido coordinación distribuida.
- La prueba heredada `test_student_school_scope.py`, fuera de la suite de estabilización desde la entrega anterior, requiere una función que no existe en la base. No se cambió ese contrato como parte de esta simplificación; la batería seleccionada sí cubre autorización y escuelas compartidas.
- No existe respaldo PDF falso en el generador de producción actual: se conserva ReportLab y el aviso visible ante un fallo. No se aplicó a ciegas esa afirmación de la propuesta.
- Abrir sesión seleccionada no está duplicado por una carga automática en esta base: es necesario para editar la sesión y se conserva. El calendario dejó de calcularse si no se solicita en la vista nueva.
- Dirección autorizó específicamente la publicación de la interfaz para apoyo, Psicología, Comunicación y Trabajo Social. La integración distribuida se prepara como una fase separada: necesita un servicio atómico compartido y no se declara activa sin configurarlo y verificarlo.

## Archivos de entrada

- Interfaz nueva: `ui/planeacion_simple.py`.
- Entrada pública existente: `ui/planeacion.py::planeacion_page`.
- Generador reutilizado con presentación compacta: `ui/planeacion_generacion.py`.
- Organización opcional: `ui/planeacion_equipo.py`.
- Cierre con guardado confirmado: `ui/auth.py`.
- Guías: `docs/guia_planeacion_apoyo.md` y `docs/guia_planeacion_paradocente.md`.
- Pruebas nuevas: `tests/test_planeacion_simple.py` y su fixture con datos ficticios.
