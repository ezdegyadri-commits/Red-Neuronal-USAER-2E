# Menos carga por interacción

El corrector global serializaba y enviaba 86 165 palabras (1 111 918 bytes de
JSON sin compresión en el entorno de prueba) en cada ejecución de la página.
Ahora el navegador confirma su recepción y conserva el diccionario público;
los clics posteriores envían un objeto vacío. Si la página pierde su memoria,
solicita el diccionario nuevamente. No se cachean textos privados del usuario.
El registro del componente se reutiliza por runtime y tiene exclusión mutua.
Las mutaciones de la pantalla se agrupan por cuadro de animación, manteniendo
la revisión de escritura y sus sugerencias.

La lectura periódica de una planeación grupal abierta consulta solo las
versiones de su escuela, ciclo, trimestre y grado antes de conciliar las copias.
Reutiliza una matrícula autorizada por consulta, en lugar de prepararla por
cada documento. La consulta general y los selectores conservan su comportamiento.
Se mantienen la conciliación, las autorizaciones y los protocolos de guardado.

Las pruebas verifican que 30 interacciones no retransmiten el diccionario,
que 200 mutaciones se agrupan en una revisión, la recuperación tras recarga,
la conservación de aportes y el rechazo de documentos sin permiso.

Esta reducción de carga no elimina la latencia de una operación real de Google
Sheets ni confirma por sí sola los tiempos de producción con todo el equipo.
No se cambia la confirmación de escrituras ni se reinicia manualmente el servicio.
