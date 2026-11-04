# Integración histórica en un entorno aislado

Esta rama parte de `piloto-docente-spark`. La operación escolar sigue en
Streamlit y Google Sheets. El piloto que ya está en Uppcoder conserva su
propia configuración. Las pruebas de este trabajo se ejecutan contra
clústeres temporales de PostgreSQL 17 en loopback, con identidades y claves
ficticias independientes. Las respuestas de Sheets se simulan en memoria.

## Operaciones verificables

- El archivo de migración acepta un JSON marcado y reconstruye sus pestañas,
  encabezados, filas y orden por lote. Verifica el SHA del manifiesto y de cada
  pestaña al guardar y recuperar. Un lote revertido no se puede recuperar por
  la herramienta. La copia restaurada se valida de nuevo.
- La proyección aditiva conserva escuelas, padrón, BAP, sugerencias, eventos,
  derivaciones y visitas cuando están conciliados. Una diferencia de escuela
  o de alumno se informa como conflicto y retiene sus registros dependientes.
  Las demás pestañas permanecen en el archivo para su mapeo posterior.
- El comparativo `GET /api/estadisticas/epp-ciclos?ciclos=2025-2026,2026-2027`
  usa el padrón activo actual autorizado como denominador fijo. Mide presencia
  de EPP por ciclo sin leer su contenido y sin atribuir una matrícula histórica.
- La API de actividad curricular externa está apagada por defecto. Requiere
  habilitación institucional y autorización explícita en cada solicitud.
  El adaptador recibe únicamente un PDA público del catálogo oficial que
  corresponda al documento autorizado. La respuesta queda para revisión
  docente y no se aplica automáticamente. React conserva su interfaz.

## Ensayo e integración futura

1. Prepara dos bases locales separadas, una para el archivo y otra para la
   proyección operativa. Usa roles dueños restringidos y marca ambas bases como
   `USAER SPA synthetic only`. Los perfiles requieren respectivamente
   `usaer_spa_test_migracion_*` y `usaer_spa_test_proyeccion_*` con su rol
   `spa_fixture_*` correspondiente.
2. En la primera, configura `USAER_MIGRACION_TEST_URL` mediante un secreto
   local. Previsualiza con `python -m tools.migracion_paralela --json copia.json`.
   Agrega `--aplicar` solo para archivar el ensayo. Recupera un lote aprobado
   con `--recuperar-lote ID` y guarda la salida fuera de Git. Restaura
   el esquema `copia_usaer` en una base sintética vacía y coteja de nuevo.
3. En la segunda, inicializa el esquema SPA de prueba, configura
   `USAER_PROYECCION_TEST_URL` y previsualiza con
   `python -m tools.proyectar_copia_sintetica copia.json`.
   Revisa diferencias antes de agregar `--aplicar`. La reversión del
   archivo no revierte la proyección operativa. Antes de proyectar, conserva
   un respaldo separado de la base operativa de ensayo.
4. Antes de promover la SPA, verifica respaldo y restauración sin sesiones,
   compatibilidad del esquema, pruebas docentes y reversión del código.
   Mantén intactos Streamlit, Sheets y el piloto activo durante el ensayo.

## Brechas y autorización

El archivo conserva las versiones de EPP y planeación y las pestañas de
expedientes, NEE, informes y actas cuando vienen en la copia. Sigue pendiente
proyectarlas a las tablas operativas con sus relaciones y cotejar sus
exportaciones. Quedan pendientes los informes administrativos, las firmas
institucionales, los anexos e instrumentos restantes de EPP, y las
estadísticas con denominadores de matrícula histórica. El comparativo nuevo
está disponible por API.

La migración real requiere autorización institucional independiente, cuenta
de extracción de alcance mínimo, captura de cambios con punto de corte y
conciliación, verificación de identificadores y autoría, tratamiento de
conflictos, acceso restringido, respaldo cifrado restaurado y una decisión
explícita sobre qué sistema será escritor en cada fase. La habilitación de
IA externa requiere además autorización del proveedor, modelo y consumo.
