# Preparación de un piloto remoto privado de USAER 2E

## Activación de la prueba escolar sintética

La estación Windows y los binarios locales de PostgreSQL sirven para el ensayo
local. La red escolar aún debe alcanzar una interfaz privada del equipo por VPN
institucional o red institucional enrutada. Mantén PostgreSQL en loopback.
Antes de activar, el operador confirma la autorización, el equipo siempre
encendido, DNS privado, regla de firewall limitada a la subred escolar/VPN y la
confianza de la CA en el cliente. Evita una redirección de puertos del router.

1. Aprovisiona el clúster y las bases según la sección siguiente. Con la
   conexión del propietario en `USAER_SPA_POSTGRES_TEST_URL` ejecuta
   `python tools/preparar_piloto_postgres.py` para crear el esquema, el padrón
   ficticio y la cuenta inicial de Dirección. Después reemplaza la variable en
   la sesión de arranque con la conexión del rol operativo. Usa el gestor de
   secretos institucional.
2. Completa EPP y planeaciones con datos ficticios antes del ensayo. Usa una
   cuenta individual por participante, con escuela y función acotadas.
   Dirección crea las cuentas desde la API de cuentas con reautenticación.
   Entrega cada contraseña aleatoria por un canal privado. No reutilices las
   cuentas de los tests ni sus contraseñas.
3. Desde la raíz del repositorio en la estación autorizada, ejecuta el siguiente
   comando después de sustituir los cuatro parámetros de infraestructura. El
   certificado PEM debe incluir la cadena requerida y el SAN exacto. Mantén la
   clave PEM en almacenamiento restringido.

   ```powershell
   .\iniciar_candidata.ps1 -ActivarPrivado -Puerto 8443 `
     -IpPrivada '<IPv4 privada de la interfaz autorizada>' `
     -NombreTLS '<DNS privado>' -Certificado '<cadena.pem>' -ClaveTLS '<clave.pem>'
   ```

4. Desde la computadora de la escuela conectada a la ruta autorizada, ejecuta
   `curl.exe --fail --show-error https://<DNS privado>:8443/api/health`. Abre
   `https://<DNS privado>:8443/` en el navegador. Exige una conexión confiable
   sin omitir la validación del certificado. Desde un equipo fuera de la ruta
   privada, verifica que el puerto no sea accesible.
5. Como docente, abre un expediente, consulta la EPP, abre una planeación, edita,
   guarda, cierra el navegador, vuelve a iniciar sesión, reabre y descarga el PDF.
   Reinicia FastAPI y vuelve a consultar la revisión. Con una cuenta de otra
   escuela verifica el rechazo del expediente y de la planeación. Registra fecha,
   red de origen, resultado y tiempo de respuesta, sin incluir datos educativos.
6. Para detener la prueba, usa Ctrl+C en el iniciador y retira la regla privada
   de acceso según el procedimiento institucional. El cierre de FastAPI
   conserva PostgreSQL y las hojas oficiales continúan operativas.

FastAPI registra origen, método, plantilla de ruta y estado HTTP. Los registros
omiten parámetros de consulta e identificadores de documentos. Custodia la
salida del proceso en almacenamiento restringido y acuerda su retención.

### Aprovisionamiento local independiente

Ejemplo para un equipo Windows con los binarios de PostgreSQL en `PATH`. Usa
una carpeta nueva bajo almacenamiento restringido y confirma que 5444 esté
libre. Ejecuta los comandos desde una terminal local. No los ejecutes sobre
un clúster preexistente.

```powershell
initdb -D '<carpeta nueva>/cluster' -U spa_bootstrap --pwprompt --auth=scram-sha-256 --encoding=UTF8 --locale=C
pg_ctl -D '<carpeta nueva>/cluster' -l '<carpeta nueva>/postgres.log' -o '-h 127.0.0.1 -p 5444' -w start
psql -h 127.0.0.1 -p 5444 -U spa_bootstrap -d postgres -W
```

En `psql`, crea las dos bases independientes y establece contraseñas nuevas
mediante los avisos interactivos. La base de migración es opcional si solo se
ensaya la SPA.

```sql
CREATE ROLE spa_fixture_escolar LOGIN;
\password spa_fixture_escolar
CREATE ROLE spa_runtime_escolar LOGIN;
\password spa_runtime_escolar
CREATE DATABASE usaer_spa_test_escolar OWNER spa_fixture_escolar;
COMMENT ON DATABASE usaer_spa_test_escolar IS 'USAER SPA synthetic only';
REVOKE CONNECT ON DATABASE usaer_spa_test_escolar FROM PUBLIC;
GRANT CONNECT ON DATABASE usaer_spa_test_escolar TO spa_runtime_escolar;
CREATE ROLE spa_fixture_migracion_escolar LOGIN;
\password spa_fixture_migracion_escolar
CREATE DATABASE usaer_spa_test_migracion_escolar OWNER spa_fixture_migracion_escolar;
COMMENT ON DATABASE usaer_spa_test_migracion_escolar IS 'USAER SPA synthetic only';
REVOKE CONNECT ON DATABASE usaer_spa_test_migracion_escolar FROM PUBLIC;
\connect usaer_spa_test_escolar
REVOKE CREATE ON SCHEMA public FROM PUBLIC;
GRANT USAGE ON SCHEMA public TO spa_runtime_escolar;
ALTER DEFAULT PRIVILEGES FOR ROLE spa_fixture_escolar IN SCHEMA public
  GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO spa_runtime_escolar;
\quit
```

Ejecuta entonces la siembra con la conexión de `spa_fixture_escolar`, como
indica el paso 1. La conexión de arranque usa `spa_runtime_escolar` y las
contraseñas deben codificarse en la URL si contienen caracteres reservados.

### Respaldo de la instancia

Usa los binarios del mismo PostgreSQL, el rol propietario de la base **sintética**
y un destino protegido. En una terminal separada, configura `PGHOST=127.0.0.1`,
`PGPORT` con el puerto sintético y `PGUSER` con el propietario. Carga
`PGPASSWORD` en esa sesión desde el gestor de secretos y retírala al terminar.

```powershell
pg_dump -Fc --exclude-table-data=public.spa_sesiones -f '<ruta protegida>/piloto.dump' usaer_spa_test_<servicio>
pg_restore --list '<ruta protegida>/piloto.dump'
# Cambia PGUSER y PGPASSWORD al propietario de la base de restauración.
pg_restore --no-owner --exit-on-error --dbname=usaer_spa_test_<restauracion> '<ruta protegida>/piloto.dump'
Remove-Item Env:PGPASSWORD
```

Prepara la base de restauración vacía y su rol propietario antes de ejecutar el
último paso. Verifica los documentos restaurados y exige iniciar sesión de nuevo.
La reversión de un despliegue consiste en cerrar el piloto y volver al respaldo
verificado en otra base, sin restaurar encima de una base en uso.

## Captura paralela de Sheets

`tools/migracion_paralela.py` trabaja únicamente con copias sintéticas y
archiva pestañas en el esquema `copia_usaer` de otra base local
`usaer_spa_test_migracion_<nombre>`. La escritura exige la marca
`USAER SPA synthetic only`, puerto explícito distinto de 5432 y el rol
`spa_fixture_migracion_<nombre>`. El esquema archivado queda separado de
las tablas que usa React. Las inconsistencias se cuentan, y los lotes se
verifican reconstruyendo las pestañas en el orden original.

Con un JSON sintético marcado o una copia de Sheets titulada exactamente
`USAER_SPA_COPIA_SINTETICA_V1`, ejecuta primero la vista previa. El acceso a
Sheets usa una identidad dedicada con acceso de lector solo a la copia y un
token OAuth con alcance `spreadsheets.readonly`. El programa pide el token
sin mostrarlo y consulta únicamente con GET.

```powershell
python tools/migracion_paralela.py --json '<copia-sintetica.json>'
python tools/migracion_paralela.py --id-copia-sintetica '<ID de la copia de prueba>'
# Configura USAER_MIGRACION_TEST_URL desde el gestor de secretos y revisa el informe.
python tools/migracion_paralela.py --json '<copia-sintetica.json>' --aplicar
python tools/migracion_paralela.py --revertir '<huella del lote>' --aplicar
```

Cada nueva captura preserva los lotes anteriores y reutiliza las filas idénticas.
La reversión retira las filas exclusivas del lote y conserva su constancia. Para
respaldar solo la captura, usa `pg_dump -Fc -n copia_usaer` sobre la base de
migración y restaura en una base independiente. El informe enumera pestañas
ausentes, errores de identidad y relaciones sin conciliar. La publicación al
modelo operativo requiere mapeo validado por módulo y aprobación separada. El
ensayo del adaptador usa respuestas simuladas; la conexión a una copia Google
real de prueba requiere el ID y la identidad de lectura autorizados.

La autorización para la prueba sintética no habilita datos reales. Antes de
una copia real se requieren autorización institucional expresa y acotada,
inventario de campos y participantes, entorno protegido, custodia y retención
acordadas, verificación desde la escuela y validación de cada proyección e
historial. La herramienta actual no habilita un modo de importación de datos
reales.

## Alojamiento recomendado

La primera opción es una VM Linux x86-64 institucional dedicada, accesible por VPN y sin publicación en Internet. React se compila en CI o en una estación de trabajo y FastAPI sirve los recursos y la API en el mismo origen. PostgreSQL reside en la misma VM, con listener de loopback, volumen exclusivo y copia fuera de la VM. El costo incremental puede ser cero si la institución ya tiene capacidad de cómputo, VPN, almacenamiento de respaldo y PKI. Su disponibilidad no se ha confirmado. Como punto de partida para un ensayo medido, solicitar 4 vCPU, 8 GiB de RAM y espacio separado para base y respaldos. Es una configuración de prueba, no una certificación de capacidad.

| Alternativa | Condiciones documentadas | Decisión |
| --- | --- | --- |
| VM institucional con VPN y PKI | Depende de inventario, autorización, operación y respaldo existentes. Sin hibernación automática si la VM permanece activa. | Preferida. Mantiene la aplicación accesible solo desde la red autorizada. |
| Render Free | Servicio web hiberna tras 15 minutos y suele tardar cerca de un minuto en volver. PostgreSQL gratuito expira a los 30 días. Web gratuito no recibe tráfico de red privada. | Incompatible con el criterio de apertura rápida y piloto privado. [Render Free](https://render.com/docs/free) |
| Oracle Cloud Always Free A1 | En la región de origen, hasta 1.500 OCPU-h y 9.000 GB-h de memoria mensuales. El alta depende de disponibilidad y Oracle puede recuperar máquinas inactivas. | Alternativa sintética condicionada a una cuenta institucional existente, aprobación de uso y capacidad confirmada. [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm) |
| Tailscale Personal | El plan gratuito se dirige a uso personal no comercial. La aplicabilidad institucional requiere revisar elegibilidad con la institución. | Usar la VPN institucional existente para este presupuesto. [Tailscale planes](https://tailscale.com/docs/account/manage-plans/free-plans-discounts) |

## Activación posterior, con autorización

1. Confirmar la VM, propietario operativo, VPN, CA confiable para los dispositivos y subred autorizada. Mantener Uvicorn y PostgreSQL en loopback. El borde HTTPS escucha únicamente en la interfaz privada. Si se usa Caddy con certificados internos, instalar y comprobar la confianza en los dispositivos administrados. [HTTPS interno de Caddy](https://caddyserver.com/docs/automatic-https)
2. Instalar dependencias fijadas, compilar frontend y verificar que la página solo solicite recursos del propio origen. Aprovisionar PostgreSQL sintético con propietario de esquema y cuenta operativa separada. Conceder a esta última únicamente las operaciones necesarias; revisar permisos por tabla antes de abrir el piloto.
3. Generar secretos independientes. El perfil local comprobado usa `USAER_SPA_TLS_CERT` y `USAER_SPA_TLS_KEY`; ambos son obligatorios si se configura TLS. Para el borde privado, mantener HTTPS también en el tramo hacia FastAPI o validar explícitamente los encabezados de proxy, la cookie Secure y el host permitido. El lanzador actual desactiva la confianza en encabezados de proxy.
4. Probar desde un equipo inscrito y otro fuera de VPN. Verificar TLS, control de host, cookies, revocación, rate limit, permisos, adjuntos y descarga. Repetir carga con el tamaño real del conjunto sintético, revisar p95 y asegurar que las sesiones del respaldo no se restauran.
5. Acordar conservación y eliminación de pruebas, custodia de respaldos, recuperación de cuentas y responsable de incidentes. Para la primera ronda se propone purgar los datos sintéticos tras 30 días, previa confirmación del operador. Un piloto con datos educativos requiere una decisión separada.
6. Antes de abrir el servicio privado, cerrar los pendientes de los flujos requeridos, ejecutar la revisión institucional y obtener la autorización expresa. La publicación y la migración de hojas oficiales son decisiones posteriores.

## Riesgos que siguen abiertos

- El perfil HTTPS se probó en loopback con una CA temporal. Falta verificar el borde, los certificados y la VPN institucional de extremo a extremo.
- El límite de acceso usa PostgreSQL o SQLite y cuenta por cuenta/origen. Un proxy que concentra todas las IP necesita configurar sus límites y probar que no bloquea una sesión escolar legítima.
- El cambio y restablecimiento de contraseña existen en la API. Quedan pendientes el ciclo de altas, bajas, recuperación fuera de sesión y revisión de privilegios.
- Los PDF del expediente se limitan a 5 MiB y 40 páginas, se entregan como descarga y se rechazan estructuras activas conocidas. Falta aislamiento de procesamiento y análisis antimalware antes de admitir archivos externos.
- La compilación local elimina las CDN del frontend servido. El lockfile requiere revisión de dependencias antes de cada publicación.
