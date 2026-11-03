# Contingencia de producción: Streamlit + Google Sheets

Aplicada el 2 de noviembre de 2026 por instrucción de Dirección.

- Producción vuelve al adaptador original de Google Sheets y al catálogo Usuarios de ese mismo libro.
- La existencia de DATABASE_URL, USAER_AUTH_SOURCE o USAER_STREAMLIT_DATA_SOURCE no activa SQL durante la contingencia.
- Se conservan caché de lecturas, filtros, permisos, captura pendiente, presupuestos de escritura y conciliación de reintentos de los diarios.
- PostgreSQL no se vació, eliminó ni modificó. El avance íntegro previo quedó en staging-sql en ambos repositorios: e4ff47b en el original y 11d571f en Render.
- El cotejo de los 36 tabs de los tres libros confirmó iguales los historiales de Planeación y EPP. Diferencias: catálogo de 8 escuelas en Neon, valores No/vacío en dos campos de 52 filas del padrón y 23 registros técnicos de sesión. No se copiaron ni sobrescribieron datos de alumnos para el rollback.
- Verificación local con DATABASE_URL ficticia inaccesible: acceso real de Abril correcto, 44 planeaciones visibles, EPP sin excepciones. Inicio 7.156 s; EPP 2.201 s. No son garantías de respuesta idéntica en todas las redes.
- 251 regresiones y 5 pruebas específicas de contingencia aprobadas. Las pruebas de guardado usan datos ficticios.

Acceso principal: https://red-neuronal-usaer-2e.streamlit.app/

Render debe redirigir a ese acceso, sin otra instancia escritora de Sheets. Un cambio de base no garantiza disponibilidad absoluta de Google ni de los hosts gratuitos. La recuperación de PostgreSQL se realizará explícitamente desde staging-sql después de conciliar las capturas que se acumulen en Sheets.
