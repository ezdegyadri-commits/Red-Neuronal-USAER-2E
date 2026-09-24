# USAER 02E — Gestión Integral

## Objetivo
Transformar la aplicación de formularios independientes en una plataforma centrada en el **Expediente Único** y la doctrina **capturar una vez, reutilizar siempre**.

Flujo principal:

**Alumno → Expediente → BAP → IA → revisión humana → Anexo 4 oficial → seguimiento → Anexo 5 → resultado → línea de tiempo.**

## Arquitectura

- `app.py`: punto de entrada y navegación.
- `config/`: configuración institucional.
- `data/`: conexión, caché y repositorio de Google Sheets.
- `services/`: reglas de negocio y expediente.
- `ai/`: IA estructurada; la IA propone, el sistema construye el formato.
- `documents/`: renderizado de Anexos IV/V.
- `ui/`: identidad visual y pantallas.
- `utils/`: normalización e identificadores.
- `app_legacy.py`: respaldo de la versión monolítica actual.

## Seguridad de despliegue

1. Conserva en Streamlit Secrets `GEMINI_API_KEY`, `credenciales_json` y `token_json`.
2. No subas `secrets.toml` al repositorio.
3. La hoja `Usuarios` actual se mantiene compatible; en una segunda fase se debe migrar de contraseñas en texto plano a autenticación segura.

## Google Sheets

La aplicación conserva las hojas actuales y agrega únicamente estas hojas nuevas:

- `Expedientes`
- `Relaciones_Expediente`
- `Linea_Tiempo`

La vinculación se hace por `ID_Alumno`, `ID_Expediente` y los IDs existentes de Anexo 3/4/5. Esto evita destruir o reordenar las hojas oficiales existentes.

## Despliegue en Streamlit Cloud

1. Sustituye el `app.py` de producción por este `app.py`.
2. Sube las carpetas `config`, `data`, `services`, `ai`, `documents`, `ui`, `utils` y `requirements.txt`.
3. Mantén `app_legacy.py` como respaldo temporal.
4. En Streamlit Cloud, verifica que el archivo principal sea `app.py`.
5. Reinicia/redeploya la aplicación.
6. Inicia sesión con un usuario existente.
7. Comprueba en este orden: Inicio → Expedientes → Evaluación BAP → Seguimiento → Documentos.

## Cronograma mensual del equipo especialista

- El apartado solo aparece a las cinco cuentas especialistas del directorio; el perfil de Dirección no puede abrirlo.
- Lee y escribe en el libro `Cronogramas`, pestaña `Registros`, conservando las filas anteriores. Una agenda corregida agrega una versión y marca la anterior como `SUSTITUIDO`.
- El libro y la carpeta histórica de PDFs deben seguir accesibles desde las credenciales `token_json` de Drive o desde la cuenta de servicio `credenciales_json`.
- El generador incluye descarga PDF y copia a la carpeta histórica. Para insertar las firmas del especialista, agrega `CRONOGRAMAS_FIRMAS` en Streamlit Secrets como JSON cuyos valores sean IDs de imagen en Drive y cuyas claves sean el nombre canónico o su versión en mayúsculas con espacios sustituidos por guiones bajos. Las imágenes de firma de Dirección y sello usan `CRONOGRAMAS_FIRMA_DIRECCION_ID` y `CRONOGRAMAS_SELLO_ID`; si no se definen, la plataforma usa los recursos locales existentes cuando están disponibles.
- El formulario conserva días hábiles, selección de escuela, actividades, agenda guardada y calendario global. No incorpora generación con IA.

## Prueba de aceptación

- Un alumno visible abre un expediente único.
- Una evaluación BAP puede analizarse con IA.
- El profesional puede editar la propuesta antes de aprobarla.
- Al aprobar, se generan Anexo 3 y Anexo 4.
- Ambos quedan relacionados con el expediente.
- Un evento posterior genera Anexo 5 y una entrada en la línea de tiempo.
- Los documentos se generan desde los datos almacenados, no desde texto aislado.
- Los errores de cuota de Google Sheets se reducen mediante caché e invalidación selectiva.

## Nota sobre formato oficial

El motor de documentos mantiene los campos del Anexo IV/V existentes. Antes de declarar el PDF/HTML como reproducción gráfica final del formato oficial de CGE/SEGEY, debe compararse con la plantilla oficial vigente (encabezado, distribución, campos y firmas). La IA nunca decide la estructura del documento: solamente propone contenido.
