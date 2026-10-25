# NEE revisadas de EPP escaneada a Planeación Individual

## Diagnóstico y alcance

La plataforma ya archivaba originales, conservaba síntesis revisadas y ofrecía
enunciados explícitos en el selector. Faltaban edición por propuesta, estados,
fundamento por necesidad, identidad estable y control de revisión simultánea.
Dirección autorizó implementar, verificar y publicar después del diagnóstico.

Se amplía el índice privado existente `Sintesis_Documentos`, sin una hoja nueva,
sin migrar registros reales y sin modificar los encabezados ni permisos.
`Sintesis_JSON.nee_registros` contiene ID, texto, fundamento breve, página o
sección, área, estado, origen, fecha de incorporación, validación y responsable,
ID de alumno, documento y hash original. El servidor fija identidad y autoría.
`necesidades` sigue disponible como proyección compatible de las validadas.

## Recorrido

1. La lectura existente extrae texto u OCR local y conserva sus avisos.
2. La detección local propone enunciados explícitos y verbos educativos de una
   sección NEE. Conserva un fragmento y la página cuando la lectura la identifica.
3. Una tabla permite corregir, añadir o descartar propuestas. Todas las nuevas
   propuestas empiezan Detectadas; solo las Validadas alimentan el selector.
4. Se exige fundamento legible y la confirmación de revisión del original.
5. Se añade una revisión, nunca se sustituye la anterior. Una edición basada
   en una revisión antigua se rechaza conservando la captura y su descarga.
6. Al abrir una planeación se consulta el catálogo estructurado de EPP escaneadas
   del alumno; no se ejecuta OCR ni se cambia el texto de sus celdas. Un fallo
   se explica y permite continuar manualmente. No se fuerza una escritura por
   el solo hecho de consultar el catálogo.

Las fuentes históricas y las necesidades previamente seleccionadas permanecen
en la planeación. Actualizar antecedentes reconstruye sus opciones vigentes.
Las necesidades históricas revisadas siguen siendo compatibles, sin inventar
páginas. La EPP digital conserva su validación colaborativa existente; sus
cambios se incorporan mediante Actualizar antecedentes.

## Límites y decisiones

- No se introduce un proveedor de IA ni se transmiten originales. No se cambia
  el generador de actividades. Una necesidad implícita requiere que la
  profesional la redacte y fundamente; no se inventa especialización a partir
  de frases generales como dificultades en matemáticas o un diagnóstico.
- La deduplicación automática cubre acentos, puntuación y Necesita/Requiere.
  La equivalencia semántica exige revisión humana; no se promete resolverla
  con certeza mediante reglas léxicas.
- La calidad OCR sigue sus límites existentes: hasta diez páginas escaneadas
  por lectura y avisos de ilegibilidad. Una página omitida no acredita lectura.
- La concurrencia usa el candado del proceso y comparación de revisión vigente,
  con lectura invalidada al escribir. No es una transacción distribuida de Sheets;
  un despliegue con múltiples procesos necesitaría un repositorio transaccional.
- Una nueva EPP no retira silenciosamente otras evaluaciones archivadas. Cada
  fuente conserva procedencia; la profesional puede descartar NEE que ya no
  procedan. No se recategorizan alumnos ni se modifican sus diagnósticos.
- El archivo conserva el límite existente PDF/JPG/PNG de hasta 5 MB.

## Verificación

`tests/test_nee_documentales.py` cubre los 15 escenarios del documento maestro,
con pruebas adicionales de legado y filas manuales. No hay datos de alumnos
reales ni escrituras productivas. OCR usa PDF sintético y una salida simulada;
esto verifica la ruta de OCR, no la exactitud de reconocimiento en fotos reales.

Regresiones: síntesis, archivo, hoja tradicional, planeación local, EPP viva,
instrumentos y lectura de materiales. La interfaz se verifica mediante AppTest;
el cambio de estado del editor se simula en el límite de presentación. La
comprobación visual en navegador no se completó por dos tiempos de espera del
control de navegador y no se declara como verificada.
