# Matriz de paridad funcional de USAER 2E 2.0

Estado del piloto sintético en `codex-validacion-spa`. Cada fila separa lo disponible en React y FastAPI de los flujos aún pendientes frente a Streamlit.

| Área | Disponible en la SPA | Pendiente de paridad o validación |
| --- | --- | --- |
| Acceso y usuarios | Contraseña con hash y sal, sesión persistente en SQL, caducidad, revocación, cookie HttpOnly y SameSite Strict. | Ciclo de cuentas, protección contra intentos repetidos, HTTPS de pruebas compartidas, recuperación de acceso y revisión de seguridad. |
| Escuelas y servicios | Alcance escolar y dos servicios de prueba aislados mediante bases y roles PostgreSQL distintos. | Gestión de servicios, asignaciones y privilegios dentro de una instalación multi-servicio. |
| Padrón | Consulta, alta y edición nominal en React, bajas recuperables, reactivación y traslados entre escuelas SQL con historial. CSV y Excel institucional. Importación Excel con vista previa y conciliación por CURP. | Reasignación interna de responsables, conciliación de duplicados históricos y política institucional para consultar planeaciones e informes previos tras un traslado. |
| Planeación individual | Selección de alumno, plantillas XXI, XXIII y XXV, campos de tablas y textos, PDF, autoguardado, historial y recuperación. | Captura equivalente de metadatos, intervenciones por NEE, colaboración, instrumentos, evidencias y revisión institucional completa. |
| Planeación grupal | Guía compartida por escuela, grado, grupo y ciclo. Aportaciones por función, matrícula, autoría, revisiones y PDF XIX/XX probados. | Cotejo visual oficial, conciliación asistida de duplicados previos y confirmación institucional de todas las reglas de matrícula. |
| Planes de intervención | Plantilla y tablas XXI disponibles para un alumno. | Flujo de seguimiento longitudinal, ligas a los planes y criterios completos de Streamlit. |
| Expediente | Consulta integrada, anexos III–V, adjuntos PDF y seguimiento con EPP, NEE, planes individuales, informes y actas vinculadas para Dirección. Comparativo EPP por ciclo. | Trámites, archivo administrativo completo y comparativos institucionales. |
| EPP | Anexo XVII con captura por áreas, protocolos digitales, resultados externos cotejados y vinculados al PDF del expediente, datos generales, historia y composición familiar. Conclusión interdisciplinaria, historial por ciclo y PDF. | Otros formatos de archivo, apartados restantes y firma institucional. |
| NEE | NEE confirmadas con fundamento, responsable, vigencia e historial, visibles desde planeación individual. | Conciliación de NEE históricas y validación de reglas institucionales de reasignación. |
| BAP y sugerencias | Alta, filtros, edición por autor o Dirección, revisiones y exportación III/IV. | Instrumentos y revisión completa de BAP, cotejo visual oficial y firma institucional. |
| Eventos significativos | Alta, consulta, filtros, edición, historial, seguimiento y PDF V. | Cotejo visual y conciliación de documentos históricos. |
| Actas, visitas y oficios | Actas de visita y reunión con acuerdos, historial, PDF y vínculo opcional al expediente. Oficios de comisión con folio SQL, edición, historial y PDF del generador institucional. Reservados a Dirección. | Emisión con firma autorizada y cotejo de los restantes formatos. |
| Informes | Editor educativo por expediente, persistencia, historial API y PDF. | Informes administrativos, formatos institucionales y ciclo de revisión y firma. |
| Estadísticas | Consulta escolar autorizada, filtro de bajas, distribución, sexo, edades y cobertura EPP por ciclo. | Comparativos históricos, reportes de zona adicionales y trazabilidad institucional. |
| Formatos oficiales | Plantillas compartidas con Streamlit y generador PDF de planeación. | Cotejo visual y funcional de todos los anexos, exportación de otros módulos y validación de firmas. |
| Motor pedagógico | Motor local editable: NEE vigente, PDA de catálogo SEP, descriptor nominal, actividad, apoyos, temporalidad, materiales y evaluación. Usa EPP autorizada, BAP, sugerencias y eventos; revisa 14 indicadores estructurales. | Recuperar informes, actas y avances de otros módulos; ya incorpora planes individuales previos e intervenciones XXI; revisión colegiada. El editor histórico conserva el asistente de ejemplo. |
| Persistencia y recuperación | SQLite compatible y PostgreSQL local sintético. Relación entre planes y alumnado, revisiones y autoría para planeación y EPP, prueba de respaldo y restauración. | Historial de todos los anexos, borrador de cliente ante caída, migración integral y políticas de conservación. |

Las métricas del ensayo aislado con 25 cuentas no certifican capacidad de producción ni paridad institucional.

## Guardado por celda

Los anexos XIX y XX pueden confirmar una aportación sin reenviar el documento completo. La revisión general sigue protegiendo la matrícula y los guardados completos. Los conflictos en una misma celda muestran las versiones para que el docente decida. El borrador se conserva mientras el editor permanece abierto, también durante una desconexión.

## Finalización y prueba escolar

- Actas de visita y reunión. Dirección puede crear, consultar, editar y exportar acuerdos y seguimiento, y vincularlos al expediente. Se conserva la revisión y el historial de autoría. Pendientes firmas y cotejo oficial.
- Guía compartida. Bóveda optativa cifrada para cambios por celda. Pendiente extender la recuperación persistente a los demás editores.
- Motor pedagógico. Incorpora informes autorizados y acuerdos de actas vinculadas para Dirección. El adaptador externo solo admite campos del catálogo SEP y no está conectado a la SPA.
- Despliegue. Perfil LAN privado preparado para una prueba autorizada. La medición desde otra computadora en la escuela queda pendiente.
- Traslados. El expediente sigue al alumno. Los informes anteriores conservan autoría y escuela de registro. Las planeaciones individuales conservan su autoría. Una guía o revisión con referencias fuera del ámbito escolar se reserva a Dirección, incluso si parte del grupo sigue asignada. Queda pendiente separar esos antecedentes sin exponer texto histórico.
