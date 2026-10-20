# Editor estable durante el autoguardado

El transporte nativo del formato usa un callback de Streamlit para aplicar las
acciones guardar/autoguardar antes de renderizar su fragmento. Antes se recibía
el evento en el cuerpo y se solicitaba otra ejecución para enviar el acuse: dos
renders por edición y consultas de catálogo repetidas mientras el contenido
quedaba marcado como desactualizado. Las acciones de navegación y cambio de
estructura mantienen su ruta protegida anterior.

Los callbacks reutilizan los validadores, nonce idempotente y persistencia
existentes. Recibir texto no confirma un guardado: el acuse solo se emite tras
persistencia. Fallos y límites de escritura mantienen pendientes y respaldo.
La lectura del equipo se limita a una consulta por diez segundos durante los
ticks/eventos de fragmento; navegar o actualizar explícitamente conserva su
lectura inmediata. No se cambia la política de conflictos ni de permisos.

El adaptador nativo entrega un cleanup por generación. Un efecto asíncrono
antiguo que termina tarde no puede destruir el editor que ya está actualizado.
El cleanup vigente sigue liberando timers y listeners al desmontar de verdad.

Las actividades de otros formatos se consultan al solicitarlas, no en cada
tick dentro de un expander cerrado. Antes de reutilizarlas se vuelve a comprobar
su autorización. No hay migración ni escritura sobre documentos históricos.

Pruebas: protocolo real del componente con AppTest (callback y acuse en una
ejecución), escritura autor/especialista, fallos de persistencia, nonce repetido,
consulta acotada, eventos inválidos y cleanup fuera de orden con DOM/reloj
ficticios. Se mantienen regresiones de concurrencia y preservación de aportes.
