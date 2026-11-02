# Restauración de Streamlit y persistencia exclusiva en Neon

Cotejo aplicado y verificado el 2 de noviembre de 2026.

Se conservaron las 36 pestañas de los tres libros originales: 10,124 filas del libro central, 12 respuestas del personal y 880 registros de cronogramas. Google Sheets se leyó exclusivamente; no se alteraron datos ni permisos.

El padrón conserva 263 filas originales, con 262 alumnos válidos y el registro vacío previamente identificado. Se preservaron las 15 cuentas y todos sus permisos. Planeaciones conserva 3,756 fragmentos originales, con una proyección de consulta de 1,926 revisiones completas en 155 documentos; EPP conserva 202 revisiones de 8 documentos. Las versiones incompletas de origen siguen en el respaldo íntegro, sin inventar contenido.

La interfaz original usa ahora PostgreSQL para todas las pestañas operativas. Se mantienen columnas adicionales, filas e historia. La selección de documentos carga versiones actuales y obtiene la historia completa bajo demanda. Las ediciones usan transacciones, bloqueos por documento, control de cambios por celda y claves de reintento. Una respuesta de éxito requiere confirmación del commit; un error conserva la captura pendiente.

La API de Drive sigue disponible para archivos y el motor de IA para la generación; no se usan Google Sheets como fuente operativa ni SQLite como alternativa silenciosa. Sin DATABASE_URL, el acceso anterior muestra un enlace al servicio canónico de Render y no abre una base vacía.

## Verificación realizada

- 19 pruebas del adaptador documental y 200 regresiones de acceso, guardado, Planeación, EPP y padrón: aprobadas.
- PostgreSQL real con datos ficticios aislados: dos áreas simultáneas, seis documentos simultáneos, reintento idempotente y rollback aprobados. El esquema de prueba se eliminó al terminar.
- Interfaz Streamlit local sobre Neon, mediante el mismo arranque compatible con Render: inicio de sesión de Dirección, 120 planeaciones visibles, EPP, Estadística y Documentos sin excepciones.
- Navegación local con caché caliente: Estadística 0.85 s y Documentos 0.49 s. No son mediciones de redes escolares ni una garantía de respuesta instantánea.

## Despliegue

El arranque directo es Streamlit. main.py conserva compatibilidad con el comando Uvicorn ya configurado en Render: inicia la misma interfaz y transporta HTTP/WebSocket, sin plantillas HTMX. La configuración gratuita no usa discos persistentes. Credenciales, archivos .env y copias privadas quedan excluidos de Git.
