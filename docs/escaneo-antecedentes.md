# Escaneo conectado con antecedentes

Ampliación verificada localmente, con publicación autorizada por Dirección.

## Flujo

1. Seleccionar al alumno/contexto y cargar el documento.
2. Pedir lectura local y revisar una síntesis breve, no la transcripción completa.
3. Confirmar correspondencia y guardar. En evaluación externa EPP, la misma
   acción conserva resultados, archiva el original admitido y guarda la síntesis.
4. Recuperar la síntesis desde Documentos del expediente sin repetir OCR.
5. Actualizar antecedentes en Planeación o preparar el contexto de EPP:
   recupera las síntesis educativas revisadas por ID, con revisión y procedencia.

No se calcula una puntuación psicométrica ni se valida una EPP por cargar un
archivo. Las NEE siguen procediendo exclusivamente de la conclusión revisada o
de enunciados de EPP escaneada confirmados por el profesional.

## Persistencia y límites

- Se reutilizan Documentos_Expediente, Archivos_Expediente y Sintesis_Documentos;
  no se cambian permisos ni se reescriben originales o historial.
- El archivo admite PDF, JPG y PNG hasta 5 MB. Otros formatos admitidos para
  lectura externa conservan sus resultados revisados en EPP, pero se informa
  que el original requiere una copia en formato/tamaño admitido para archivarse.
- Un fallo al archivar o guardar síntesis no deshace la evaluación confirmada.
  La pantalla distingue la confirmación parcial y permite repetir la misma acción.
- El archivo es idempotente por hash y contexto; las síntesis conservan revisiones.
- Cargar otra evaluación en EPP viva cambia la clave del borrador de lectura y
  de revisión: no se reutiliza el texto o la confirmación del archivo anterior.
- No se realiza OCR al reconstruir antecedentes. No se llama a IA sin el
  consentimiento separado del flujo existente.
- Se excluyen documentos de identidad/contacto de las fuentes educativas.
  Una fuente colectiva solo se reutiliza si todos sus destinatarios pertenecen
  al contexto consultado, y se identifica como colectiva.
- La fecha expuesta es de archivo y nunca se presenta como fecha de aplicación.

## Verificación

Pruebas con datos ficticios: recuperación de síntesis sin lectura en memoria,
tipos y destinatarios autorizados, ciclos, alcance colectivo, archivo y resumen,
fallos parciales, reintento sin duplicar evaluación y ausencia de llamadas a IA.
Regresiones: instrumentos EPP, EPP viva y planeación local. No se subieron
documentos ni se modificaron expedientes reales para estas pruebas.
