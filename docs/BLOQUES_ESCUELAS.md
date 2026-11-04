# Migración por bloques de escuelas

La pertenencia a USAER proviene de `ESCUELAS_USAER` en
`config/settings.py`. Los CCT de respaldo que usa la SPA cuando su base está
vacía no se usan para conciliar. Las siguientes claves son referencias
públicas que Dirección debe cotejar con su padrón autorizado y turno.

| Bloque | ID | Escuela | CCT de referencia pública |
| --- | --- | --- | --- |
| USAER-B01 | ESC-001 | Damián Carmona | [31DPR0414P](https://www.yucatan.gob.mx/docs/archivo/segey/instrumentos_sustantivas_5.pdf) |
| USAER-B01 | ESC-002 | Ichcaanziho | [31DPR0232G](https://educacion.yucatan.gob.mx/infopro/files/FAM_B%C3%A1sica_Regular_2024.pdf) |
| USAER-B01 | ESC-003 | Gregorio Torres Quintero | [31DPR0466V](https://www.hacienda.gob.mx/conac/Entidades%20Federativas%20Implementacin/2014/Segundo%20Trimestre/Yucat%C3%A1n/054_2111_300714t02_31000.pdf) |
| USAER-B01 | ESC-004 | Remigio Aguilar Sosa | [31EPR0232F](https://educacion.yucatan.gob.mx/infopro/files/FAM_B%C3%A1sica_Remanente_2024.pdf) y [31EPR0771P](https://www.yucatan.gob.mx/docs/transparencia/gasto_federalizado/2007_2012/2010_TERCER_TRIMESTRE.pdf). Identidad y turno por confirmar. |
| USAER-B02 | ESC-005 | Elvira Parra Ávila | [31EPR0039A](https://sige.segey.gob.mx/resources/descargables/Resultados_PEAGE%20_Ciclo%202015-2016.pdf) |
| USAER-B02 | ESC-006 | Manuel Sarrado | [31EPR0040Q](https://sige.segey.gob.mx/resources/descargables/Resultados_PEAGE%20_Ciclo%202015-2016.pdf) |
| USAER-B02 | ESC-007 | Domingo Solís Rodríguez | [31EPR0075F](https://educacion.yucatan.gob.mx/infopro/files/FAM_B%C3%A1sica_Remanente_2024.pdf) |
| USAER-B02 | ESC-008 | Quintana Roo | [31EPR0092W](https://educacion.yucatan.gob.mx/infopro/files/FAM_B%C3%A1sica_Regular_2025.pdf) |

Quintana Roo conserva su posición, incluso sin maestro de apoyo. El bloque
acepta su padrón sin campo de docente y admite un catálogo escolar sin
alumnos en la captura. Dirección consulta los registros compatibles mediante
los permisos existentes. La importación no crea cuentas. Cuando un documento
requiere vincular una autoría, conserva el original en preparación hasta
conciliarla con una cuenta autorizada.

## Ensayo y aplicación reversible

1. Obtén paquetes individuales según el [procedimiento de copia controlada](COPIA_CONTROLADA.md).
   Para el ensayo usa datos ficticios. Para una operación posterior autorizada,
   conserva el mismo alias de origen por escuela y registra la fecha real de
   cada captura. El límite inicial sigue siendo 20 alumnos por paquete.
2. Desde el clon de desarrollo, con una base de preparación PostgreSQL 17
   local y su rol exclusivo, ejecuta:

   ```sh
   python -m tools.bloques_escuelas catalogo
   python -m tools.bloques_escuelas preparar USAER-B01 \
     /privado/esc-001.json /privado/esc-002.json /privado/esc-003.json /privado/esc-004.json
   ```

   La previsualización es de solo lectura. Si el informe coincide con la
   captura, respalda la base de preparación y repite la orden con `--aplicar`.
   Los paquetes del bloque se escriben en una transacción. El reporte
   incluye faltantes, CCT de la copia, referencias, alumnos, expedientes,
   filas documentales, fecha de captura, conciliación y cuarentena.
   Un ID de alumno presente en dos escuelas del bloque detiene la operación.
   Coteja el CCT y turno con el padrón autorizado antes de continuar.
3. En una **segunda base sintética**, con respaldo restaurable, previsualiza
   cada paquete con `python -m tools.proyectar_copia_sintetica /privado/esc-001.json`.
   Agrega `--aplicar` únicamente tras la conciliación. Si hay incompatibilidades
   o ediciones locales, conserva el original en preparación. El ensayo se
   revierte restaurando el respaldo en otra base y cambiando el destino del
   entorno aislado. Una ausencia en la captura no da de baja un registro.
4. Verifica API y React con cuentas autorizadas. Antes del siguiente bloque
   revisa conflictos, integridad y capacidad. La herramienta no selecciona,
   aplica ni promueve automáticamente otro bloque. Cada aplicación posterior
   necesita una orden distinta.

En el perfil real la orden de preparación requiere además `--real`,
`--referencia ACTA_AUTORIZADA`, el permiso explícito del entorno y el
PostgreSQL privado marcado. Antes de manejar expedientes identificables
deben estar aprobados el alcance, el alojamiento, los permisos, la custodia
de claves y una restauración desde respaldo cifrado. La proyección a tablas
operativas sigue limitada a ensayos sintéticos.

## Estado y capacidad

El ensayo B01 usa cuatro escuelas, cuatro alumnos ficticios, cuatro filas de
expedientes explícitos y cuatro eventos. Los expedientes explícitos se
conservan en preparación. La SPA puede abrir el expediente derivado del
padrón y su evento. EPP, NEE confirmadas, PDF individuales vinculados,
planeaciones, informes educativos y actas compatibles cuentan con pruebas
locales del ensayo documental. La revisión completa por escuela permanece
pendiente, especialmente para formatos e informes administrativos, oficios
y firmas, análisis de contexto, perfil grupal, instrumentos restantes,
estadísticas históricas y relaciones documentales fuera de los mapeos.

Las métricas del reporte se limitan al CPU del proceso Python, el pico de
asignaciones Python y el crecimiento de tablas e índices de preparación.
El tiempo de reloj incluye la espera de PostgreSQL. No equivalen al consumo
global de CPU y RAM de Spark. Antes de aprobar capacidad, mide el uso del
servicio en el entorno autorizado con una jornada representativa de acceso,
edición y PDF. Cuatro escuelas identifican el alcance documental del bloque.
