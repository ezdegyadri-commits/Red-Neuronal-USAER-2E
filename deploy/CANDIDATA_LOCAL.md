# Candidata local RC1

Contextos escolar/sociofamiliar reutilizan el Anexo XVII y su historial por ciclo. Aprendizaje y Trabajo Social editan su área; Dirección puede editar ambas; la consulta conserva el alcance interdisciplinario existente del expediente. La planeación toma las narrativas con referencia de revisión, sin copiar la tabla de familiares. No realiza llamadas a IA externa en el modo privado.

Los cuatro protocolos digitales verificados XI, XIII, XIV y XVI conservan sus reactivos originales; permiten vigencia profesional opcional y respaldo/recuperación de respuestas. Otros instrumentos se incorporan mediante resultados profesionales cotejados con el PDF original; no existen baremos automáticos para protocolos no verificados. No se interpreta una vigencia vacía como confirmación profesional ni se suprimen resultados históricos vencidos.

Trámites: solicitud interna por alumnos autorizados, solicitud externa por Dirección, seguimiento versionado, folio central idempotente, respuesta institucional PDF para firma manual y comprobantes privados JPG/PNG/WEBP de hasta 5 MB. La respuesta emitida no se sustituye. La delegación de gestión administrativa a personal distinto de Dirección sigue pendiente de evidencia de autorización individual; no se deduce de un nombre.

## Actualización reversible de un clon de prueba

El ZIP contiene únicamente los cambios de código desde d0f4067, React compilado y manifiesto de huellas. Requiere las dependencias ya instaladas. No contiene datos, secretos, bases, respaldos ni plantillas privadas. No ejecuta SQL, extracciones ni despliegues.

1. Conservar los respaldos cifrados existentes. Elegir un clon de prueba en rama distinta de main, sin cambios locales en los archivos incluidos. No ejecutar en Uppcoder ni en Streamlit. Montar V: antes de iniciar la SPA privada; no recrear el clúster.
2. Extraer solamente `codigo/deploy/actualizar_candidata.py` del paquete a una carpeta temporal de código y ejecutar: `python actualizar_candidata.py --destino RUTA_CLON_PRUEBA --paquete USAER_2E_RC1_ACTUALIZACION.zip`. Agregar `--aplicar` tras revisar la previsualización. Se crea automáticamente un ZIP de reversión de código fuera del clon; nunca se copian archivos de PostgreSQL.
3. Reiniciar únicamente FastAPI de la instancia local de prueba mediante su iniciador privado existente. No se requiere migración del esquema. Las aplicaciones conservan sus tres claves originales; la vigencia se almacena como metadato adicional y en el resultado, permitiendo que el código anterior siga abriendo sus respuestas al revertir. Conservar los secretos DPAPI existentes y la conexión exclusiva a la base consolidada cifrada. URL prevista: http://127.0.0.1:18083/.
4. Para revertir, detener solo esa instancia de prueba y ejecutar `python actualizar_candidata.py --destino RUTA_CLON_PRUEBA --paquete RUTA_ZIP_REVERSION --revertir --aplicar`; iniciar con el mismo iniciador. El reversor rechaza cambios posteriores de código y nunca borra registros capturados.

## Límites de esta candidata

Pruebas nuevas específicas en base ficticia aislada; ningún expediente real se editó para validarlas. El cierre de este paquete no certifica equivalencia total de Streamlit. Permanecen sin automatización los baremos de instrumentos sin reglas verificadas y la delegación administrativa individual no documentada. La activación sobre la base consolidada requiere V: montada: no se habilita un destino sin cifrado como sustituto.

Pruebas específicas aprobadas: API de contextos e instrumentos (incluida reutilización en propuestas), API de trámites y comprobantes, navegador React con contextos/instrumentos/trámites y reversión de código con rechazo de conflictos. Se usaron exclusivamente SQLite y datos ficticios aislados; no se certifica una ejecución nueva en PostgreSQL real mientras V: esté desmontada. React compiló sin errores.
