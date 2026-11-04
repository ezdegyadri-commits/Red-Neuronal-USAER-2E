# Piloto SPA local

Requiere el entorno Python del repositorio con sus dependencias, incluida FastAPI. Usa únicamente datos ficticios. El lanzador normal escucha en `127.0.0.1` y fija una base SQLite local independiente de la configuración de Streamlit.

Desde la raíz del repositorio en PowerShell, compila primero el frontend:

~~~powershell
Push-Location piloto_spa/frontend
npm ci
npm run build
Pop-Location
~~~

Con el entorno Python preparado:

```powershell
.\.venv\Scripts\python.exe tools\preparar_piloto_local.py
.\.venv\Scripts\python.exe iniciar_piloto.py
```

El primer comando crea `data/piloto_sintetico.db` y solicita la contraseña de `piloto.local`. Ejecútalo antes del primer arranque y una sola vez por base. Si usas otro intérprete, indica su ruta absoluta o define `USAER_PILOTO_PYTHON` antes de abrir `iniciar_piloto.bat`.

Abre `http://127.0.0.1:8000`. Si Uvicorn informa que el puerto está ocupado, selecciona uno libre para este piloto:

```powershell
$env:USAER_SPA_PORT = '8010'
.\.venv\Scripts\python.exe iniciar_piloto.py
```

La verificación de salud consulta SQLite. FastAPI sirve el frontend compilado desde el mismo origen y comprueba sus archivos al arrancar. Las sesiones duran hasta ocho horas y se invalidan al cerrar sesión. Los documentos confirmados se conservan en el archivo SQLite.

## Pruebas

```powershell
.\.venv\Scripts\python.exe tests\test_piloto_aislado.py -v
.\.venv\Scripts\python.exe tests\test_end_to_end_spa.py -v
.\.venv\Scripts\python.exe tests\test_concurrencia_25_usuarios.py -v
```

La primera prueba utiliza HTTP real, un puerto local libre, dos procesos Uvicorn consecutivos y una base temporal. Las otras dos usan el cliente ASGI y fixtures temporales. La prueba de concurrencia representa 25 hilos sobre un documento y una sesión compartida.

## Contratos de guardado

Abre primero el documento y devuelve su `revision` al guardar. El servidor devuelve `409` cuando recibe una revisión obsoleta. Vuelve a abrir el documento y concilia el cambio antes de reintentar. Para las planeaciones el servidor valida propietario o Dirección. Para los documentos vinculados a alumnado valida el alcance escolar. Actas, oficios y estadísticas globales se reservan a Dirección en este piloto.

Este perfil está destinado a uso local. La preparación de un entorno compartido requiere validar VPN, HTTPS, operación y permisos según PREPARACION_PILOTO_REMOTO_USAER_2E.md.

## Validación con PostgreSQL local

El perfil PostgreSQL es sintético. El lanzador toma la conexión de `USAER_SPA_POSTGRES_TEST_URL` y solo acepta `127.0.0.1`, un puerto explícito distinto de 5432 y una base `usaer_spa_test_<servicio>`. Usa el rol `spa_fixture_<servicio>` sin privilegios elevados. La aplicación comprueba la marca de la base antes de crear tablas. El puerto HTTP también es local.

Para reproducir la prueba, señala el directorio de binarios de PostgreSQL que contiene `initdb`, `pg_ctl`, `pg_dump` y `pg_restore`. El test crea un clúster temporal, tres bases con roles separados y contraseñas aleatorias. Después de las comprobaciones detiene el clúster. El respaldo excluye las filas de `spa_sesiones` para evitar reactivar tokens al restaurar.

```powershell
$env:USAER_PG_BIN = 'C:\ruta\al\directorio\bin'
.\.venv\Scripts\python.exe tests\test_postgres_spa.py -v
```

Las sesiones actuales se guardan como huellas en SQL. Sobreviven a reinicios del proceso, caducan en ocho horas y se revocan al cerrar sesión o cambiar la contraseña. El frontend usa una cookie HttpOnly y las escrituras con cookie exigen una cabecera de la SPA. Para acceso remoto se requiere configurar y probar TLS, hosts permitidos, servidor de borde y políticas de intentos y acceso. El lanzador permanece en loopback.

### Arranque de la candidata local

En Windows puedes ejecutar `./iniciar_candidata.ps1` desde PowerShell. El
iniciador comprueba dependencias, prepara el frontend, valida la marca sintética
y los permisos del rol operativo, comprueba el esquema y arranca en loopback.
Requiere Node.js, npm, un Python con `requirements.txt` y una base local
sintética preparada previamente. Si hay más de un intérprete, indica
`-Python C:\ruta\python.exe`. Para compilar sin abrir la base, usa `-SoloCompilar`.
El script no instala PostgreSQL ni aprovisiona cuentas.

Con el frontend compilado y el esquema de la base sintética ya preparado, configura
`USAER_SPA_POSTGRES_TEST_URL` con la conexión local de pruebas. Para un rol operativo
sin permisos DDL configura también `USAER_SPA_ROLE=runtime`. Usa
`iniciar_piloto.bat` desde esa terminal, con `.venv` disponible o con
`USAER_PILOTO_PYTHON` apuntando al intérprete del proyecto. Si el puerto 8000 está
ocupado, define `USAER_SPA_PORT=8010` y abre `http://127.0.0.1:8010/`.
El rol operativo requiere que la tabla de Informes ya exista. La prueba integral
verifica su creación con el rol propietario sintético.

En **Alumnos y Expedientes**, el personal de apoyo con escuela asignada y Dirección
pueden revisar el Excel, confirmar el plan de cambios y exportar el padrón autorizado.
La pestaña **Seguimiento** reúne registros existentes sin crear copias editables.
Dirección puede vincular un acta a un expediente. Los docentes no reciben el acta
ni su texto en la línea de tiempo o en propuestas pedagógicas.

Para crear un plan, selecciona el alumno o grupo, el ciclo y el formato. El historial de planeación permite recuperar una revisión como un guardado nuevo. En el documento vinculado al padrón, el panel de propuestas puede usar un PDA del catálogo y permite revisar y modificar la actividad antes de incorporarla.
