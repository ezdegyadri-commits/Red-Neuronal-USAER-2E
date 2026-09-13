# USAE 02-E — Gestión Integral

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
