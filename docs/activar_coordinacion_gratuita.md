# Activar la coordinación gratuita, sin trasladar los expedientes

La interfaz de planeación ya está publicada. La coordinación distribuida es una integración separada, preparada y desactivada hasta probar su conexión.

## Qué hace falta hacer una vez

1. Entra a [Supabase](https://supabase.com/dashboard) y crea un proyecto dedicado a la coordinación. Selecciona exclusivamente **Free**; no Pro ni complementos. Si aparece una solicitud de pago, detente. La aceptación de los términos y la creación de tu cuenta las haces tú.
2. En el proyecto, abre **SQL Editor**. Ejecuta íntegro [el archivo de instalación](../deployment/coordinacion_postgres.sql). Solo crea controles de coordinación privados en ese proyecto; no se ejecuta sobre Google Sheets ni sobre una base con alumnos.
3. Localiza la URL del proyecto y una **clave secreta de servidor** —secret key o service_role heredada—, nunca la clave pública/publishable/anon. No envíes esa clave por WhatsApp ni por este chat; no la guardes en GitHub. Las [claves de servidor](https://supabase.com/docs/guides/getting-started/api-keys) deben permanecer en la configuración segura del backend.
4. Cuando esté publicada la integración, añade el bloque siguiente a **Secrets** de Streamlit, conservando todas las credenciales actuales. Al principio deja `habilitada = false`.

```toml
[coordinacion_planeacion]
habilitada = false
url = "https://ID_DEL_PROYECTO.supabase.co"
token = "TU_CLAVE_SECRETA_DE_SERVIDOR"
namespace = "usaer2e-produccion"
```

5. Avísame cuando exista el proyecto. Primero probaremos con un namespace de pruebas y documentos ficticios; después, en una ventana sin guardados pendientes, activaremos `habilitada = true` y reiniciaremos todas las instancias. Todas deben usar la misma versión, proyecto y namespace. No habilites varias instancias mezclando escritores antiguos sin coordinación.

La activación no requiere capturar nuevamente alumnos, escuelas, personal ni expedientes. En PostgreSQL solo se almacenan huellas, referencias de operación, fechas operativas y cupos. No se copian evaluaciones, diagnósticos, nombres ni archivos.

## Qué esperar del plan gratuito

Actualmente, Free cuesta $0/mes, incluye PostgreSQL, 500 MB y solicitudes API ilimitadas; puede pausar el proyecto tras una semana sin actividad. Consulta las [condiciones oficiales vigentes](https://supabase.com/pricing). No equivale a un servicio con disponibilidad garantizada ni a una certificación de carga de 20 navegadores. Si se pausa durante vacaciones, habrá que reactivarlo antes de usar el coordinador. No se ha contratado ni activado ningún servicio de pago.

La IA mantiene su configuración y facturación por separado; este servicio no sustituye Gemini ni incorpora créditos de IA.

## Si hay una incidencia

- Si no se confirma un guardado, conservar el borrador y descargar el respaldo; no repetir envíos ciegamente.
- Un guardado incierto se comprueba por revisión y SHA en la base original. Si no se puede demostrar que terminó, se protege el documento hasta revisar el incidente; no se libera solamente por haber pasado tiempo.
- No borrar las tablas de coordinación ni cambiar proyecto/namespace para resolver una falla mientras haya operaciones pendientes. No vaciar ni limpiar Planeaciones_Versiones.
- Desactivar el coordinador no es una solución automática a una caída: primero detener escrituras, confirmar operaciones en vuelo y volver a una única instancia escritora. Los demás módulos conservan sus reglas de edición y acceso.
