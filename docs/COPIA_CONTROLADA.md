# Copia controlada de una escuela

Streamlit y Google Sheets siguen como sistema oficial de captura. El exportador
lee una copia filtrada mediante Sheets API. La preparación escribe en PostgreSQL
independiente. La SPA no tiene una ruta de retorno hacia Sheets.

## Fuentes identificadas en código

`config/settings.py` declara `URL_SPREADSHEET_MAESTRO`,
`URL_SPREADSHEET_RESPUESTAS_PERSONAL` y `CRONOGRAMAS_SPREADSHEET_ID`.
`data/google.py` abre el maestro y el libro de respuestas. El primero y
los servicios de Planeación, EPP y archivo describen el padrón, los anexos,
los diarios por revisión y los documentos por fragmentos. `PESTANAS` en
`tools/migracion_paralela.py` define las estructuras admitidas por la copia.
Los libros de respuestas, cronogramas y catálogos de cuentas quedan fuera
del primer ensayo. El proceso no incorpora identificadores de libros ni
credenciales de producción.

## Ensayo manual, recomendado

En una carpeta cifrada **fuera del repositorio**, coloca CSV UTF-8 con los
nombres de pestaña, como `Escuelas.csv` y `Alumnos.csv`, o un JSON con
`marca: "USAER_SPA_COPIA_SINTETICA_V1"`, `origen` y `pestanas`.
Incluye una escuela, entre 1 y 20 alumnos ficticios y solo sus documentos.
Al anonimizar, sustituye identificadores de forma consistente y revisa
texto libre, PDF, metadatos y firmas. Para el primer ensayo es preferible
generar datos ficticios como los de `tests/fixture_proyeccion_documental.py`.

Desde el clon aislado, usando un directorio privado en el entorno de prueba:

```sh
python -m tools.copia_controlada empaquetar /privado/csv-ficticios /privado/lote.json \
  --origen ensayo-escuela-a --escuela esc-ficticia --capturada 2026-11-04T12:00:00-06:00
python -m tools.copia_controlada preparar /privado/lote.json
python -m tools.copia_controlada preparar /privado/lote.json --aplicar
```

Usa la hora real de captura, el mismo alias estable de origen y el ID
sintético correspondiente. La URL se solicita sin eco. La base para este
ensayo debe ser PostgreSQL 17 de loopback, por ejemplo
`usaer_copia_ensayo_escuela_a`, propiedad del rol restringido
`copia_ensayo_escuela_a`, con el comentario `USAER COPIA ENSAYO V1`.
La primera orden de preparación es de solo lectura. La segunda aplica el
lote atómicamente y conserva sus registros crudos en `copia_controlada`.
La aplicación de la SPA no usa ese rol ni esa base.

El manifiesto privado guarda fecha, conteos, huellas por pestaña e identidades
deterministas. La segunda captura distingue altas, cambios y cuarentena.
Una ausencia es informativa. Repetir exactamente un paquete no lo duplica.
Los conflictos y los cambios de origen permanecen en preparación para
revisión. La salida de la terminal contiene huellas y conteos, sin filas ni
datos personales. Quien revise la cuarentena necesita acceso privado
autorizado. La presencia en preparación no equivale a incorporación en la SPA.

Para el ensayo operativo prepara otra base sintética con el esquema SPA y
las cuentas de prueba autorizadas. Usa el paquete ficticio verificado
con `python -m tools.proyectar_copia_sintetica /privado/lote.json`
y revisa el informe antes de agregar `--aplicar`. Solo se agregan altas
compatibles. Un cambio sobre un documento ya importado queda como conflicto
para que no sustituya una edición en React. Conserva el dump previo, restaura
en otra base y verifica documentos, vínculos, permisos y cero sesiones.

## Orden separada para una futura copia real

Estos comandos están reservados a un operador institucional autorizado, en
un entorno privado aprobado. El entorno, la credencial y el identificador de
la copia se suministran fuera de Git. No se cambia la compartición de los libros
oficiales. La opción preferida es que el responsable entregue una copia mínima
por el canal institucional. La alternativa usa una copia filtrada que ya esté
autorizada y compartida como lectora a una cuenta dedicada. El alcance OAuth
es `spreadsheets.readonly`. El exportador usa `values:batchGet` con rangos
explícitos y una sola petición de valores. El descriptor privado incluye
`tipo: "copia_filtrada_autorizada"`, `libro`, `origen` y `rangos`, por
ejemplo rangos `A1:B20` para las pestañas autorizadas.

```sh
export USAER_COPIA_PRIVADA_AUTORIZADA=1
python -m tools.copia_controlada exportar-copia /privado/descriptor.json /privado/lote-real.json \
  --credencial /privado/lector.json --escuela ID_AUTORIZADO \
  --capturada FECHA_ISO_CON_ZONA --referencia ACTA_AUTORIZADA
python -m tools.copia_controlada preparar /privado/lote-real.json --real --referencia ACTA_AUTORIZADA
python -m tools.copia_controlada preparar /privado/lote-real.json --real --referencia ACTA_AUTORIZADA --aplicar
unset USAER_COPIA_PRIVADA_AUTORIZADA
```

Para CSV manual, sustituye la orden `exportar-copia` por `empaquetar` con
`--origen`, `--real` y `--referencia`. En JSON manual el marcador real es
`USAER_COPIA_REAL_CONTROLADA_V1`. El perfil real solo permite preparación
en una base `usaer_copia_privada_*`, con rol `copia_privada_*` y comentario
`USAER COPIA PRIVADA AISLADA V1`. La referencia registra la autorización
externa. El programa no puede certificar su validez institucional.
La proyección operativa actual solo admite el perfil sintético.

## Aprobaciones y controles pendientes

- La institución debe determinar la base jurídica, el alcance por alumno y
  escuela, el responsable, el aviso de privacidad, los plazos de conservación,
  el encargado y las condiciones de transferencia internacional aplicables.
  [Ley mexicana aplicable a sujetos obligados](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPDPPSO.pdf)
- Uppcoder declara infraestructura Hetzner en la UE, cifrado y respaldos
  con retención de hasta doce meses. Sus términos describen acceso de personal
  autorizado y condiciones de tratamiento. Falta confirmar por escrito su
  aplicación al plan y a la pila concretos, auditar acceso administrativo,
  restauración, borrado, incidentes y aprobar el contrato antes de usar
  expedientes identificables. [Privacidad](https://portal.uppcoder.com/privacy)
  [Condiciones de tratamiento](https://portal.uppcoder.com/terms)
- Verifica por separado una restauración de respaldo cifrado con clave
  custodiada por la institución, permisos y descarga de archivos en el
  entorno elegido, y la ausencia de sesiones restauradas. Las pruebas
  locales de restauración no certifican el respaldo del proveedor.
- Aprueba un punto de corte y capturas sucesivas. Los rangos de Sheets no
  ofrecen por sí mismos una instantánea transaccional de varios libros.
  Revisa versiones y relaciones antes de promover cambios. Los adjuntos
  grupales, documentos sin correspondencia de autoría o escuela, formatos
  administrativos y revisiones incompatibles requieren mapeo adicional.
