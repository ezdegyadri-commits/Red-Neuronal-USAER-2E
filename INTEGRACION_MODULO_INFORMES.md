# USAER 2E 2.0 — Entrega incremental del módulo Informes

**Alcance:** integración local del parche sobre `codex-validacion-spa`, con regresiones adicionales de PostgreSQL y navegador.

## Implementado

- Tabla SQLAlchemy `informes_educativos_spa`, vinculada al alumnado por clave foránea, ciclo y autor.
- `GET /api/informes?alumno_id=...`, `POST /api/informes`, `GET /api/informes/{id}`, `PUT /api/informes/{id}`, `GET /api/informes/{id}/historial`, `GET /api/informes/{id}/pdf`.
- Validación por escuela y cuenta autora, con el alcance institucional de Dirección. Las revisiones concurrentes devuelven `409`. El contenido y el historial se guardan en la misma transacción.
- Entrada **Informes** en la SPA y acceso directo desde el expediente, con editor de antecedentes, avances, dificultades, intervenciones y recomendaciones.
- Recuperación de hasta tres informes autorizados recientes como referentes contextuales del motor de propuesta pedagógica local. El texto no se envía a un servicio de IA externo por esta integración.

## Verificación local

- `python tests/test_informes_spa_manual.py` ejecuta la comprobación rápida contra SQLite temporal mediante HTTP real.
- `python tests/test_postgres_spa.py -v` prueba la migración sintética, creación, edición concurrente, historial, PDF, aislamiento por escuela y recuperación después de reiniciar FastAPI. Configure `USAER_PG_BIN` con los binarios locales según `PILOTO_LOCAL.md`.
- Con `USAER_PLAYWRIGHT` apuntando al módulo Playwright, la misma suite abre Edge, inicia sesión como docente, crea el informe desde un expediente, descarga el PDF y recupera el contenido desde un navegador nuevo tras el reinicio.

## Integración segura en la rama local

1. Conservar los cambios actuales de Codex (`git status`) y crear una rama de integración derivada, nunca trabajar en `main`.
2. Aplicar los archivos del ZIP **comparando diffs**, porque Codex puede haberlos modificado después de la exportación; no sobrescribir ciegamente versiones posteriores.
3. En entorno sintético SQLite, reiniciar con usuario de prueba: `Base.metadata.create_all()` crea la tabla nueva.
4. En PostgreSQL de pruebas, crear primero la tabla **con el rol propietario**, mediante una migración controlada. El rol operativo no debe crear el esquema; verificar SQL y probar rollback antes de desplegar. No ejecutar scripts de esquema contra producción.
5. Con dependencias del proyecto disponibles, compilar la SPA desde `piloto_spa/frontend`: `npm ci && npm run build`. Abrir la aplicación aislada y comprobar **Informes** en navegador.
6. Ejecutar las pruebas de integración actuales antes de cualquier merge y comprobar autorización, permisos, PDF y reapertura tras reiniciar.

## Pendiente antes de producción

- Validar la maqueta y formatos oficiales de informes ante el equipo académico; el PDF actual es una **exportación funcional simple**, no una reproducción certificada de un anexo institucional.
- Verificar el módulo en PostgreSQL de pruebas con el mismo perfil de infraestructura que usará la SPA, y con pruebas de concurrencia de usuarios distintos.
- Completar la captura de metadatos adicionales, firmas y el ciclo de revisión institucional de informes.
- Conectar informes al resto de los procesos longitudinales con reglas validadas por el equipo.

**Estado:** módulo incremental. La equivalencia con los formatos institucionales de Streamlit requiere la validación académica indicada arriba.

Para la base PostgreSQL **exclusiva de pruebas**, el paquete incluye `tools/migrar_informes_spa.py`. Requiere `USAER_SPA_MODE=postgres-synthetic` y `USAER_SPA_ROLE=owner`, verifica la marca de base sintética y crea únicamente la tabla nueva. **No se autoriza ejecutar contra producción.**
