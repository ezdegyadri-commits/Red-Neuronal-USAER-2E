# Operación cero fricción — USAER 2E

Fecha: 28 de octubre de 2026. Rama: `feat/operacion-cero-friccion`.
Base examinada: `6bf34c1` (producción al iniciar la intervención).

Esta entrega corrige causas reproducibles de espera y guardado incierto,
conserva los formatos y las funciones pedagógicas y prepara diagnóstico sin
datos de alumnos. No se publicó, reinició ni modificó la base institucional.
La prueba con maestras en Cloud continúa pendiente: los ensayos descritos son
locales, con datos ficticios y almacenamiento simulado.

## 1. Causas comprobadas y correcciones

| Hallazgo reproducido en código/pruebas | Corrección |
| --- | --- |
| Una escritura con respuesta perdida seguida de nueva captura se rechazaba como conciliación pendiente, aunque procediera del mismo editor. | Primero se verifica/repite la revisión original idempotente; la captura posterior de ese editor se concilia con su instantánea enviada. |
| Un intento incierto de otra clave, ausente en Sheets, devolvía una espera de 60 segundos sin resolverlo. Si su sesión desaparecía podía impedir nuevas aportaciones. | Bajo el candado del documento se verifica y recupera esa misma revisión antes de procesar la siguiente aportación. No se borra el intento ni se descarta su contenido. |
| Todos los informes EPP compartían un candado durante lecturas/escrituras de red. | Candado por alumno/ciclo. El candado global queda para las operaciones breves del caché, sin red dentro de él. |
| El candado de documento esperaba sin límite. | Admisión acotada a dos segundos; si sigue ocupado se difiere el intento con un aviso recuperable. No se fuerza la liberación de otro escritor. |
| El navegador retransmitía cada 15 segundos sin límite, incluso después de ciertos errores del servidor. | Hasta tres transmisiones con pausas crecientes; al fallar se conserva el respaldo y queda disponible el reintento explícito con el mismo nonce. Los errores detienen el watchdog. |
| Los reintentos automáticos de Planeación/EPP podían continuar indefinidamente. | Hasta tres fallos por ciclo automático, con backoff y pausa posterior. El reintento manual habilita otro ciclo. |
| El Anexo V se convertía a PDF al renderizar diversas pantallas. También se reconstruían los archivos de padrón/personal al visitar Dirección. | Generación diferida al descargar, con copias independientes de los datos que el usuario estaba viendo. |
| Para descargar respaldos, un expansor revelaba otro botón que revelaba las descargas. | Abrir el expansor presenta las descargas directamente. Su contenido se calcula solo cuando está abierto. |

Estos mecanismos explican fallos sintéticos reproducidos. No prueban por sí
solos qué ocurrió en el incidente particular de los 30 minutos: faltan sus
registros operativos. No se atribuye ese incidente a cuotas o a otra persona.

La continuación automática exige un identificador de origen del editor.
Dos pestañas de una misma cuenta no se consideran una sola edición. Si el
origen no puede verificarse, se mantiene el tratamiento conservador. Dos
cambios incompatibles en la misma celda siguen rechazándose; no se elige un
ganador ni se sobrescribe texto silenciosamente.

## 2. Mapa de persistencia y recuperación

El inventario estático registra 103 archivos con interacciones o acceso a datos,
842 declaraciones de controles y 98 operaciones de datos. Es una exploración
del código, no 842 recorridos humanos ni una medición de clics en producción.

| Ámbito | Identidad, almacenamiento y concurrencia | Recuperación y límite |
| --- | --- | --- |
| Planeación individual y formatos de especialistas | Documento estable, revisiones aditivas en `Planeaciones_Versiones`, SHA256 y partes completas; comparación de revisión; permisos en servidor. | Historial, respaldo JSON y texto pendiente por pestaña. La continuación de un envío incierto del mismo editor se resuelve en esta entrega. |
| Planeación grupal | Clave canónica por escuela/grado/grupo/ciclo/periodo, coordinación del grupo y aportaciones por área. | Se mantienen conciliación, historial de copias y prohibición de borrar aportes ajenos. |
| Borradores de planeación | Eliminación lógica versionada, solo por el autor de un borrador. | Papelera recuperable; los documentos enviados conservan su revisión. Eliminar ya tenía acceso directo en la versión base. |
| EPP | Clave por alumno/ciclo; versiones por área; fusión de cambios independientes y permisos granulares. | Respaldo del editor y versiones. La red de otro informe ya no comparte el candado de escritura. |
| Expedientes y documentos cargados | Contexto autorizado por ID; metadatos/binarios separados; hash y verificación de partes antes de declarar completo. | Documentos incompletos no se ofrecen como íntegros. Se conserva el archivo y su clasificación existente. |
| Eventos significativos | Anexo V y relaciones con expediente/línea de tiempo; filtro de duplicados en la interfaz; borradores por contexto. | Recuperación de pestaña y borrador cifrado de eventos. El registro y sus relaciones siguen siendo varias operaciones, no una transacción conjunta. |
| Informes y documentos de salida | Generadores oficiales a partir de datos y capturas del módulo correspondiente. | Se difiere el PDF de eventos y las exportaciones de Dirección; no se declara que todos los generadores sean asíncronos. |
| Horarios y cronogramas | Borradores aditivos y publicaciones separadas, con autorización de cuenta/escuela. | Se conservaron sus mecanismos y pruebas. Aún existen rutas síncronas y append con reintentos genéricos: requieren intervención específica antes de prometer idempotencia universal. |
| Padrón y otros formularios | Repositorio y permisos por ámbito; formularios específicos y editor directo existentes. | No se modificó matrícula ni se migraron esquemas. La auditoría detecta que el buscador antiguo de la tabla ya no forma parte del editor directo; no se presenta como restaurado en esta entrega. |

### Sesiones, recargas y desconexiones

- El token de continuidad existente es cifrado, dura 12 horas y vuelve a validar
  cuenta y permisos. Cerrar sesión revoca ese acceso. No es un bloqueo de edición.
- Las claves de Planeación/EPP y del respaldo del documento se derivan de cuenta,
  área y documento. El origen de un envío se mantiene al trasladarlo a la cola
  de pendientes; es distinto en otra pestaña.
- Un rerun consulta el Future existente; no vuelve a lanzar la escritura por el
  hecho de dibujar la pantalla. Un acuse solo confirma el texto efectivamente
  enviado, conservando lo escrito después.
- El editor usa debounce de cuatro segundos al escribir y un segundo en
  selectores, además del agrupamiento del servidor ya existente.
- El evento offline del navegador pausa transmisiones y muestra «Sin conexión».
  Al volver online se verifica el mismo envío. La falta de respuesta del servidor
  se muestra como falta de confirmación, sin deducir que Internet esté caído.
- `sessionStorage` permite recuperar en la misma pestaña tras una recarga. No
  constituye un respaldo central, no se comparte entre dispositivos y puede
  perderse al cerrar la pestaña o borrar el almacenamiento del navegador.
- Los Futures, intentos y colas en memoria no sobreviven a un reinicio del
  servidor. Esta limitación se conserva visible; no se promete cero pérdidas.

## 3. Comparación de clics

Conteos del recorrido desde el punto indicado, excluyendo escribir y escoger
datos. Derivados del código y contratos de interfaz locales; no son un estudio
con tiempos de maestras en producción.

| Módulo y acción | Base actual | Después | Reducción | Pasos conservados |
| --- | ---: | ---: | ---: | --- |
| Planeación: tarjeta → continuar documento | 1 | 1 | 0% | Apertura explícita del documento identificado. |
| Planeación: lista → eliminar borrador → confirmar | 2 | 2 | 0% | Confirmación y papelera. El recorrido antiguo de cuatro clics ya había sido corregido. |
| Planeación: tarjeta → respaldos → descargar | 3 | 2 | 33% | Abrir las descargas y elegir el archivo; eliminado el único clic intermedio redundante. |
| Editor vivo: guardar manualmente | 1 | 1 | 0% | Acuse real; autoguardado no requiere ese clic. |
| EPP: autocompletar un apartado desde el documento vivo | 1 | 1 | 0% | Se conserva revisión profesional y consentimiento contextual ya existente. |
| Eventos: descargar PDF desde su vista | 1 | 1 | 0% | La generación costosa pasa al clic de descarga. |
| Dirección: descargar padrón/personal | 1 | 1 | 0% | La exportación se prepara al descargar. |

Se eliminó el 100% del paso redundante identificado en la cadena de respaldo.
No se afirma una reducción general del 50% de todos los flujos: varios accesos
ya eran directos y no corresponde quitar confirmaciones necesarias para forzar
ese indicador. La exploración con usuarios de todos los módulos sigue pendiente.

## 4. Rendimiento medido

Ensayo reproducible con cuatro workers, 15/20/25 escritores ficticios, 30 ms de
latencia simulada por append y verificación de las revisiones recuperadas.
Compara el código EPP de `6bf34c1` con el candado por documento. No representa
los tiempos de Google Sheets ni de Streamlit Community Cloud.

| Escritores ficticios | Tiempo total antes | Después | Reducción | Versiones verificadas |
| --- | ---: | ---: | ---: | ---: |
| 15 | 786.11 ms | 400.51 ms | 49.1% | 30 |
| 20 | 1059.41 ms | 551.81 ms | 47.9% | 40 |
| 25 | 1294.70 ms | 737.99 ms | 43.0% | 50 |

Con 25 escritores, el p95 de la operación de guardado fue 217.39 → 141.98 ms.
La prueba controla una red artificial; no permite prometer esos porcentajes
en las escuelas. Debe repetirse en un entorno de prueba alojado antes de medir
la capacidad real de 15–25 sesiones de navegador.

Instrumentación añadida: tiempo de cola, duración y resultado del trabajo;
espera/admisión del candado; duración, intento, clase de error y estado HTTP de
operaciones Google. No registra payloads, nombres, CURP, cuentas, documentos,
hallazgos ni mensajes crudos del proveedor. Para conocer latencias reales es
necesario publicar con aprobación y analizar estos indicadores operativos.

Reproducción local:

```powershell
python tools/auditar_cero_friccion.py --baseline 6bf34c1 --salida antes.json
python tools/auditar_cero_friccion.py --salida despues.json
python -m unittest tests.test_operacion_cero_friccion -q
node tests/planeacion_editor_cliente.cjs
```

## 5. Verificación

Matriz ampliada: 77 módulos y 843 ejecuciones de pruebas, con datos ficticios.
Incluye casos compartidos/heredados; no equivale a 843 casos únicos. La matriz
final actualizada debe acompañar el informe.

Se comprobaron: reintento idempotente tras respuesta perdida, captura posterior,
dos pestañas de la misma cuenta, conflicto real de celda, espera acotada,
independencia de dos EPP, permisos, historial/papelera, recuperación,
sincronización, matrícula, separación de áreas, JSON/PDF y navegación AppTest.
El contrato JavaScript cubre debounce, nonces, retransmisión limitada, offline,
online y preservación de captura posterior al envío.

Se actualizaron dos pruebas anteriores: la de cuota esperaba dormir y repetir
dentro de la petición (ya fallaba contra la versión base), y la de gestión
esperaba la tabla paginada sustituida previamente por el editor directo. Se
mantuvieron las comprobaciones de pausa por cuota, baja y reactivación; no se
reintrodujo el bloqueo ni se anunció un buscador inexistente.

Pendientes externos: navegador Android/Windows real, recarga con sesión real,
15–25 navegadores simultáneos, red de las escuelas y tiempos de API en Cloud.
Las pruebas sintéticas no sustituyen esas comprobaciones.

## 6. Archivos y alcance

- `services/planeacion.py`: resolución de intentos inciertos y continuidad por origen.
- `services/planeacion_estabilidad.py`: espera acotada de candado y diagnóstico.
- `services/epp.py`: candado por informe y coherencia/aislamiento del caché.
- `services/trabajos_documento.py`, `data/google.py`: mediciones sin datos personales.
- `services/reintentos_edicion.py`: política acotada de reintentos de interfaz.
- `ui/guardado_asincrono.py`, `ui/epp_guardado_asincrono.py`,
  `ui/planeacion_pendientes.py`: acuses, origen y cola pendiente.
- `ui/planeacion_papel_component/index.html`: retransmisión, offline/online y respaldo.
- `ui/planeacion_repositorio.py`: respaldos directos y carga diferida del expansor.
- `documents/descarga_diferida.py`, `ui/pages.py`: snapshots para seis exportaciones.
- `tests/test_operacion_cero_friccion.py`, `tests/planeacion_editor_cliente.cjs`:
  regresiones; contratos antiguos ajustados en dos módulos de pruebas.
- `tools/auditar_cero_friccion.py`: inventario y medición reproducibles.

## 7. Límites y evolución propuesta, sin implementar ni migrar

Sheets no ofrece una transacción de comparación de revisión y append frente a
escritores externos. Los candados son por proceso. La idempotencia lógica de
versiones no elimina necesariamente filas físicas idénticas tras un timeout.
El registro de un evento y sus relaciones tampoco es una sola transacción.
No sería correcto anunciar guardado universal transaccional sobre esta base.

La ruta gradual propuesta es un almacén transaccional para revisiones, cambios
pendientes e idempotencia; conservar Sheets como fuente/exportación compatible
mientras se migra cada flujo aprobado. Requeriría autorización independiente.

1. Acordar backend, cuentas técnicas, acceso privado, respaldo y restauración.
2. Implementar la misma interfaz de repositorio y probar con datos ficticios.
3. Migrar un flujo piloto, con cotejo de cantidades, hashes, permisos y versiones.
4. Usar una única fuente escritora por flujo; evitar doble escritura no atómica.
5. Exportar a Sheets y conservar una ruta de reversión verificada antes de ampliar.

El costo incluye implementación, pruebas de conciliación/permisos, alojamiento,
copias, monitoreo y operación. No se cotizó un proveedor ni se comprometió una
tarifa. No se instalaron servicios ni se cambiaron credenciales o esquemas.

## 8. Estado de entrega

Correcciones críticas implementadas y verificadas localmente; inventario y
mediciones disponibles. No se declara concluido un recorrido humano exhaustivo
de toda la plataforma ni una migración de la persistencia de todos sus módulos.
El despliegue y la comprobación alojada quedan sujetos a aprobación, conforme
al documento de intervención. No se modificaron registros de producción.
