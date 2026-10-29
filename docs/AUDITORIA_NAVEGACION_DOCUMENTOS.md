# USAER 2E — Navegación orientada a documentos

Fecha: 28 de octubre de 2026. Rama local: `feat/navegacion-documentos`.

## Estado de la entrega

Implementación local para revisión. No se publicó, no se reinició Streamlit y no se modificaron datos de producción. No se añadieron tablas, migraciones ni dependencias de base de datos.

La nueva experiencia es de activación gradual: `USAER_NAVEGACION_DOCUMENTOS=1`. Por defecto se conserva la navegación anterior. Para revertir: establecer `USAER_NAVEGACION_DOCUMENTOS=0`, o usar «Ayuda, recuperación y navegación anterior → Usar navegación anterior» en la nueva entrada. Revertir no elimina documentos ni limpia el estado de edición.

## Auditoría previa: puntos de entrada y estado

| Área | Archivos y funciones revisados | Hallazgo y tratamiento |
|---|---|---|
| Inicio y navegación general | `app.py`, `ui/contenido_modulo.mostrar`, `ui/hub.pagina_central_hub`, `ui/sidebar.render_sidebar_navigation` | Inicio mostraba módulos antes que trabajo guardado. Con la función habilitada muestra primero Mis planeaciones; los módulos siguen disponibles en el menú lateral y en Todos los módulos. |
| Planeación propia | `ui/planeacion_viva.pagina`, `_entrada`, `_abrir`, `ui/planeacion_repositorio.listado` | Repositorio propio separado del compartido. Se reúne la consulta autorizada sin crear copias. Se conserva el editor existente. |
| Planeación compartida | `ui/planeacion_colaboracion.panel`, `ui/planeacion_anexo_compartido.panel` | El documento identificado volvía a pasar por escuela, formato, grado/grupo y selector de documentos. Ahora se abre directamente por ID. El PI usa su tabla de aportaciones y la guía grupal su hoja completa. |
| Persistencia y pendientes | `services/planeacion.listar`, `compartidos`, `autorizar`; `ui/planeacion_simple._abrir`; `ui/planeacion_pendientes.conservar` | Los servicios canónicos ya protegen permisos y versiones. Se reutilizan. No se cambió guardar, guardar_aportacion ni la conciliación de versiones. |
| Expedientes | `ui/pages.expedientes_page`, `_seleccionar_alumno`; `ui/archivo_expediente.panel`, `_conectados`, `pagina_grupal` | Se omiten selectores con un único alumno, documento vinculado, escuela, grupo o módulo de origen. Las opciones múltiples conservan su elección. |
| Informes | `ui/pages.documentos_page`, `ui/epp_acceso`, `ui/relatorias` | Se evita volver a escoger alumno/escuela únicos en el expediente documental. EPP y relatorías mantienen sus editores y generación. No se mezclan sus identificadores con los de planeación. |
| Hojas de eventos | `ui/pages.eventos_page`, `seguimiento_page`, `ui/eventos_continuidad.recuperar` | El selector común de alumno y la recuperación de una única hoja se resuelven sin selector. Se conserva la continuidad y el respaldo actuales. El expansor de recuperación continúa siendo una acción explícita. |
| Perfil grupal | Contexto de grupo en `ui/pages.bap_page`, `documentos_page` y `ui/archivo_expediente.pagina_grupal` | No existe una entrada independiente con ese nombre en el menú inspeccionado. Se conserva el contexto escolar/grupal y se simplifican opciones únicas del expediente. No se sustituyen los instrumentos de BAP. |
| Padrón | `ui/pages.alta_page`, `ui/estadisticas.estadisticas_page`, `ui/padron_importacion`, `ui/padron_movimientos` | Se conservan alta manual, Excel, edición en tabla y movimientos. No se modifican matrículas, categorías o asignaciones. |
| Escuelas | `services/escuelas`, selección de escuela en alta, documentos, archivo y estadísticas; `ui/docentes_regulares_form` | El catálogo y la autorización siguen siendo canónicos. Se omiten escuelas únicas en los contextos de consulta modificados. No se crean asignaciones ni una tabla nueva. |
| Actas | `ui/pages.visitas_page`, historial de constancias/reuniones, `ui/relatorias` | Ya recuperan registros por identificador y conservan el folio. Se mantienen esos flujos; no se cambia la lógica documental ni se atribuye un ahorro de clics no medido. |
| Estadísticas | `ui/estadisticas.estadisticas_page` | La maestra con una sola escuela asignada ve directamente esa escuela. Dirección conserva el ámbito Toda la USAER. Ordenamiento y edición del padrón permanecen disponibles. |

Variables relevantes anteriores: `navegacion_principal`, `base+'_activa'`, `base+'_viva_entrada'`, `prefix+'_doc'`, `prefix+'_pending'`, `prefix+'_trabajo_io'`, `prefix+'_abierto'`, `prefix+'_papel_nonce'`.

Nuevo estado: `base+'_documento_contexto'`, `base+'_url_resuelta'`, `base+'_crear_documento'` y preferencias de búsqueda/filtros. El contexto incluye ID de documento, escuela, alumnos, grado/grupo, formato, modalidad, ciclo, cuenta y ruta del editor. Ningún índice de posición actúa como identidad de documento.

## Arquitectura implementada

- `services/navegacion_planeaciones.py`: índice, filtros, contexto, resolución de enlaces y proyección de lectura. No guarda documentos ni genera archivos.
- `ui/mis_planeaciones.py`: lista táctil, consulta opcional y apertura por identificador. Reutiliza los editores, exportadores y servicios versionados existentes.
- `ui/seleccion_contextual.py`: autoselección de una opción reversible; mantiene los selectores cuando hay decisiones reales.
- El parámetro `plan` contiene un identificador opaco de 64 caracteres, sin nombres, CURP, escuela o ID de alumno. No es una credencial: resolverlo vuelve a comprobar la asignación y los permisos en el servidor.
- Un enlace no autorizado no abre automáticamente otro alumno ni el primer resultado.
- Lista paginada inicialmente a 12 documentos. Los controles secundarios y el catálogo de módulos se cargan al expandirse. No se genera el PDF completo durante cada rerun de la lista; se conserva la descarga diferida existente.
- La búsqueda y los filtros no modifican el documento ni su modalidad. La guía nueva exige un grado válido y resuelve automáticamente un grado/alumno único.
- Abrir otro documento reutiliza la protección de pendientes existente, incluyendo el mismo Future de un envío en curso. Si se pulsa volver antes de la pausa de autoguardado, el cliente entrega primero el texto pendiente mediante el evento de navegación. No se declara guardado un documento por el solo hecho de navegar.
- Dirección dispone de lectura sin celdas editables ni botones aparentes de guardado, además del acceso a su revisión existente.

## Acciones contextuales

La fila completa es Abrir. Exportar PDF se muestra junto al documento. Duplicar abre directamente la preparación de la copia adaptada cuando corresponde, con revisión de alumno/periodo. No se crea otra guía del mismo grupo; se conserva la unicidad de la planeación compartida.

Eliminar borrador muestra la confirmación en la misma lista. Solo el autor de un borrador confirmado puede hacerlo; con cambios pendientes primero se pide confirmar su guardado. Se conserva la papelera versionada y la recuperación. No hay eliminación permanente.

## Rutas y número de acciones

Una acción significa una selección o pulsación; no incluye escribir filtros opcionales, desplazarse, autenticarse o abrir el navegador.

| Escenario | Antes | Después | Evidencia |
|---|---|---|---|
| Abrir planeación compartida existente | Continuar → Compartidas → Escuela → Formato → Grado/grupo → Documento → Abrir: aproximadamente 7 | Mis planeaciones → tocar documento: 1 | Ruta anterior documentada por el usuario y cotejada en código; ruta nueva probada con AppTest y con navegador móvil. |
| Abrir planeación propia desde Inicio | Inicio → Planeación → Continuar → documento: aproximadamente 3, según estado | Inicio ya muestra Mis planeaciones → documento: 1 | Apertura desde Inicio comprobada con AppTest. Conteo anterior por inspección, no por cronómetro. |
| Documento compartido con una sola opción | Selector de documento + Abrir: 2 adicionales | No existe ese selector en la ruta directa: 0 adicionales | Guía y PI compartidos probados. |
| Eliminar borrador desde lista | Eliminar + confirmar: 2 cuando se usaba el control directo existente | Eliminar + confirmar: 2, visibles en la fila | AppTest verifica que la primera acción no elimina y que las otras filas permanecen. No se atribuye una reducción inexistente. |
| Escuela única en estadísticas | Selector obligatorio con una opción | Escuela resuelta y visible; 0 selecciones | Regresiones de estadísticas con la nueva función habilitada. |
| Volver del editor a la lista | Dependía de la vista/recorrido | Mis planeaciones: 1 | Prueba de cambio entre documentos con captura pendiente conservada. |

## Verificación realizada

Datos ficticios, sin enviar información de alumnos a APIs ni escribir en Sheets/Drive:

1. Pruebas específicas de índice y UI: propios/compartidos sin duplicar, filtros, identificadores opacos, permisos revocados, enlace denegado, acceso directo desde Inicio, guía compartida y PI con tabla real, eliminación en dos acciones, recuperación por enlace y conservación de texto pendiente.
2. Contrato JavaScript con DOM y reloj ficticios: regreso antes del debounce entrega el texto y conserva el respaldo, tanto en transporte nativo como en el compatible.
3. Creación desde la nueva entrada hasta el editor real y regreso a la lista sin crear otra copia.
4. Compatibilidad del recorrido anterior: suites de planeación, papel, repositorio, pendientes, copias, permisos, menú y padrón ejecutadas con la función deshabilitada.
5. Estadísticas de Remigio, ámbito compartido, edición del padrón y archivo ejecutados también con la función habilitada.
6. Navegador local a 390 × 844 px: sin desbordamiento horizontal en la lista, filas visibles de más de 44 px y apertura con un toque. Se comprobó el ID en el editor y el regreso. Se restauró el tamaño normal del navegador.

Resultado final: 23 pruebas específicas de navegación aprobadas; 11 del contrato del formato aprobadas con la nueva navegación; 177 regresiones del recorrido anterior aprobadas; 36 verificaciones transversales aprobadas y 16 verificaciones finales de guardado/acceso compartido aprobadas. Estos grupos se superponen y no constituyen un total de pruebas únicas. El contrato JavaScript también terminó correctamente.

La evidencia y resultados locales se encuentran en `output/navegacion-documentos/`. Los contadores finales figuran en `verificacion-final.json`.

Limitación de la suite heredada: `tests/test_student_school_scope.py` no puede importarse porque solicita `validar_identidad_padron`, ausente también en `services/padron_oficial.py` de la revisión base. No se modificó ese servicio ni se presenta esa suite como aprobada. Las pruebas de permisos de la nueva navegación y de ámbitos compartidos se ejecutaron por separado.

No se probaron un despliegue, sesiones reales, concurrencia de toda la USAER ni latencia de Google en producción. Las pruebas antiguas de UI requieren la navegación anterior; ejecutarlas con la nueva activa falla al buscar los selectores retirados. La nueva interfaz tiene sus propias pruebas de interacción.

## Reconexión y límites de recuperación

El enlace permite recuperar el documento y su contexto después de autenticarse otra vez, siempre que siga autorizado. Se conserva el respaldo y control de cambios pendientes ya existente en el editor. Esto no convierte en guardado central el texto que aún no ha sido confirmado ni garantiza recuperar una pestaña cerrada antes de enviar o respaldar su contenido.

## Revisión antes de una publicación futura

La etapa local queda disponible para revisión. Antes de activar globalmente: comprobar cuentas reales de apoyo, especialistas y Dirección en un entorno autorizado, verificar una reconexión de cada perfil y medir el tiempo de apertura con el volumen real. No se autoriza una publicación mediante este informe.
