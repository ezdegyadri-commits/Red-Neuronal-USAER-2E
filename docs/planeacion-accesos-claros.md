# Accesos claros y selector sin duplicados

Sustituye la navegación por pestañas/radio del módulo por accesos grandes por rol.
Cada clic abre un solo submódulo; no se montan dos editores ocultos. Los botones
usan foco visible y animación discreta, desactivada con movimiento reducido.
El formato individual conserva su formulario único y el XIX su editor por área.

Las etiquetas de consulta muestran escuela, grado/grupo, ciclo, trimestre y fecha
cuando corresponde; no muestran UUID ni cadenas técnicas. Los IDs siguen siendo
las claves internas, nunca se sustituye identidad por coincidencia de nombres.

El catálogo compartido vuelve a conciliar las guías autorizadas antes de construir
el selector y comprueba de nuevo la autorización de la hoja resultante. Una raíz
ya consolidada tiene prioridad sobre las copias incluidas en sus fuentes incluso
cuando se reciben solo versiones recientes. Esto evita que su fecha de guardado
más nueva reactive otra copia como documento independiente. Las fuentes no se
borran ni se modifican. La regla se aplica a todos los equipos, por escuela,
grado/grupo, ciclo y trimestre; no mezcla grupos A/B ni trimestres distintos.

Si una sesión abierta apunta a una copia ya reunida, se dirige a su raíz solo
cuando no tiene aporte pendiente. De lo contrario conserva la edición y ofrece
respaldo para conciliación, sin sobreescribirla. No se efectúan migraciones ni
escrituras de planeaciones al cambiar la navegación.

Pruebas: accesos por rol y montaje de un solo submódulo; etiquetas sin IDs;
persistencia de raíz consolidada; selector de tercero con apoyo y comunicación
en una sola hoja; regresiones de concurrencia y captura agrupada.
