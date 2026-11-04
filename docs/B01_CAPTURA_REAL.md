# B01. Descriptor y captura controlada

Destino exclusivo de preparación PostgreSQL 17 privado, con respaldo cifrado
restaurado y acceso institucional aprobado. Streamlit y Sheets siguen siendo
el sistema oficial. La orden real no promueve registros a la SPA.

| Escuela | ID | CCT para cotejar con el padrón firmado |
| --- | --- | --- |
| Damián Carmona | ESC-001 | 31DPR0414P |
| Ichcaanziho | ESC-002 | 31DPR0232G |
| Gregorio Torres Quintero | ESC-003 | 31DPR0466V |
| Remigio Aguilar Sosa | ESC-004 | 31EPR0232F o 31EPR0771P. El operador elige únicamente con el padrón autorizado y el turno. |

El libro maestro se identifica en `config/settings.py` y `data/google.py`.
Usa sus pestañas `Escuelas`, `Alumnos`, `Expedientes`, `Movimientos_Alumnos`
y los anexos correspondientes. Los servicios de EPP y Planeación declaran
`EPP_Versiones` y `Planeaciones_Versiones`. El archivo de expediente usa
`Documentos_Expediente` y `Archivos_Expediente`. Incorpora las pestañas de
NEE, informes, relaciones y actas solo cuando figuren en la exportación
autorizada con los encabezados que valida la herramienta. Los libros de
respuestas del personal y cronogramas quedan fuera. No exportes cuentas,
contraseñas ni secretos.

## Archivos privados del operador

1. Para la opción manual, guarda un directorio CSV UTF-8 por escuela, con
   el nombre de cada pestaña como nombre de archivo, o un JSON por escuela.
   Usa almacenamiento cifrado fuera de Git. El marcador JSON real es
   `USAER_COPIA_REAL_CONTROLADA_V1`. Conserva todos los alumnos del ámbito
   autorizado. Un exceso de tamaño detiene la captura completa.
2. Guarda `padron-autorizado.json` en la misma zona privada. Usa este esquema
   con un objeto por ID de escuela. El CCT y turno deben provenir de la
   aprobación institucional y coincidir con la fila de `Escuelas`.

   ```json
   {
     "ESC-001": {"nombre": "Damián Carmona", "cct": "CCT_VALIDADO", "turno": "TURNO_VALIDADO"},
     "ESC-002": {"nombre": "Ichcaanziho", "cct": "CCT_VALIDADO", "turno": "TURNO_VALIDADO"},
     "ESC-003": {"nombre": "Gregorio Torres Quintero", "cct": "CCT_VALIDADO", "turno": "TURNO_VALIDADO"},
     "ESC-004": {"nombre": "Remigio Aguilar Sosa", "cct": "CCT_VALIDADO", "turno": "TURNO_VALIDADO"}
   }
   ```

3. Si se usa Sheets en vez del archivo manual, el descriptor de **cada
   copia filtrada** indica `tipo: "copia_filtrada_autorizada"`, `libro`,
   `origen`, `filas_por_pagina` y `pestanas`. Cada pestaña declara
   `ultima_fila` y `ultima_columna`, verificadas por el operador. Por ejemplo:

   ```json
   {
     "tipo": "copia_filtrada_autorizada",
     "libro": "ID_PRIVADO_DE_LA_COPIA",
     "origen": "b01-esc-002",
     "filas_por_pagina": 250,
     "pestanas": {
       "Escuelas": {"ultima_fila": 2, "ultima_columna": "E"},
       "Alumnos": {"ultima_fila": 120, "ultima_columna": "Y"}
     }
   }
   ```

   Sustituye los límites del ejemplo por las extensiones completas
   verificadas. El exportador usa GET con el alcance `spreadsheets.readonly`
   y páginas de hasta 500 filas. La captura conserva las filas en blanco
   entre páginas. El manifiesto registra conteos y huellas del resultado.
   Para exportar, usa `python -m tools.copia_controlada exportar-copia`
   con el descriptor, el archivo de salida, `--credencial`, `--escuela`,
   `--capturada` y `--referencia`. La cuenta lectora debe estar previamente
   autorizada sobre la copia. No cambies permisos de las hojas oficiales.

## Conciliación especial de Ichcaanziho

Cruza `Alumnos.Maestra de Apoyo` y los movimientos internos confirmados
de `Movimientos_Alumnos`. Conserva el ID del alumno y la autoría original
de cada documento por separado. El operador agrega a la copia
`Asignaciones_Apoyo` con las columnas `ID_Asignacion`, `ID_Alumno`,
`ID_Escuela`, `ID_Cuenta`, `Responsable`, `Desde`, `Hasta` y
`Compartida`. Usa `CECI` o `MARYCRUZ` y el ID estable de la cuenta
validada en el destino. Usa `SI` en ambas filas cuando el acceso
simultáneo esté aprobado. Las fechas se expresan como AAAA-MM-DD y
la vigencia es inclusiva. Deja vacíos los límites desconocidos; un
solapamiento sin marca explícita queda pendiente. Conserva también las
vigencias cerradas de una nueva captura. El nombre del padrón da evidencia
de conciliación, pero jamás concede acceso ni crea una cuenta.

El reporte separa Ceci, Marycruz, compartidos y pendientes sin mostrar
identificadores de alumnos. La incorporación operativa de ESC-002 requiere
la conciliación de su padrón y las pruebas con ambas cuentas en el entorno
aprobado. Los vínculos documentales de la ficha histórica se muestran a
Dirección. Las maestras siguen las reglas de cada módulo y su asignación
vigente. Las guías que mezclan alumnos fuera del alcance se bloquean.

## Órdenes finales, reservadas al operador autorizado

```bash
export USAER_COPIA_PRIVADA_AUTORIZADA=1
# Repetir con ESC-001 a ESC-004, sus alias y sus directorios reales.
python -m tools.copia_controlada empaquetar /privado/csv-esc-001 /privado/esc-001.json \
  --origen b01-esc-001 --escuela ESC-001 --capturada FECHA_ISO_CON_ZONA \
  --real --referencia ACTA_AUTORIZADA

python -m tools.bloques_escuelas preparar USAER-B01 \
  /privado/esc-001.json /privado/esc-002.json /privado/esc-003.json /privado/esc-004.json \
  --real --referencia ACTA_AUTORIZADA --padron-autorizado /privado/padron-autorizado.json
```

La URL de la base privada se pide sin eco. Repite la última orden con
`--aplicar` después de revisar duplicados, faltantes, CCT, turnos,
asignaciones y respaldo. La escritura es una transacción de preparación.
Las filas incompatibles permanecen en el lote privado. Las relaciones
operativas requieren que el documento de destino exista y corresponda al
mismo alumno. Los traslados entre escuelas sin evidencia suficiente
requieren conciliación. No uses la rama para actualizar Uppcoder activo.
