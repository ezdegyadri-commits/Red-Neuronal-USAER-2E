# Piloto sintético USAER 2E en Oracle Cloud

## Requisitos y costo

Verifica en la consola de la región de origen que la cuenta pueda crear
`VM.Standard.A1.Flex` con etiqueta Always Free, Ubuntu ARM64, volumen dentro
del cupo y acceso a una IP pública. Comprueba el estimador antes de crear
recursos y no cambies a una cuenta de pago. Oracle documenta 1,500 OCPU-h
y 9,000 GB-h al mes para A1, equivalentes a 2 OCPU y 12 GB. La capacidad
efectiva depende de la región y la cuenta. Oracle también puede recuperar
instancias gratuitas inactivas. [Oracle Always Free](https://docs.oracle.com/en-us/iaas/Content/FreeTier/freetier_topic-Always_Free_Resources.htm)

Si A1 carece de capacidad, el perfil `compose.piloto-amd64.yaml` reduce
memoria para una E2.1.Micro AMD64 gratuita, sujeta a cupo y disponibilidad.
Es un ensayo sintético de pocos usuarios. Construye la imagen en otro
equipo AMD64 autorizado y cárgala con `docker load` antes de ejecutar
`docker compose -f compose.yaml -f compose.piloto-amd64.yaml up -d --no-build`.
Revisa memoria y reinicios antes de aceptar el ensayo. Este perfil carece
de validación de rendimiento. Render Free es otra opción de evaluación
con adaptación separada. Su suspensión por inactividad y la caducidad de
PostgreSQL la limitan a un piloto desechable. [Render Free](https://render.com/docs/free)

## Ensayo de la imagen y del proxy

Instala Docker Engine y el plugin Compose en la VM autorizada. Prepara una
carpeta fuera del repositorio con cuatro archivos de una línea,
`pg_bootstrap`, `pg_owner`, `pg_runtime` y `direccion_inicial`. Genera
valores aleatorios independientes de al menos 24 caracteres URL-safe
con el gestor de secretos. Aplica permisos de lectura solo al operador
y al UID que lo necesita. La app usa UID 10001. Comprueba el UID efectivo
de PostgreSQL en la imagen elegida antes de asignar ACL. Los secretos de
Compose son archivos montados, por lo que la protección en el host es
obligatoria. La app recibe únicamente el secreto operativo.

Con `USAER_SECRET_DIR` apuntando a esa carpeta y `USAER_PUBLIC_HOST`
definido como DNS sintético, ejecuta:

```bash
docker compose config --quiet
docker buildx build --platform linux/arm64 --load -t usaer-spa-sintetica:oracle .
docker image inspect --format '{{.Architecture}}' usaer-spa-sintetica:oracle
docker compose up -d --no-build
docker compose ps -a
docker compose logs --tail 80 migrar app caddy
```

El valor por defecto enlaza Caddy a loopback y usa una CA interna. Para
una prueba local confiable, exporta el certificado público de la CA de
Caddy, confía explícitamente en él en el equipo de prueba y comprueba
`/api/health` con el nombre del certificado. No uses `curl -k`.

El Dockerfile usa etapas separadas para React y Python. El contexto
excluye archivos de trabajo y el saneamiento reemplaza referencias
nominales heredadas conocidas en la copia sintética. Revisa el inventario
de la imagen antes de distribuirla. No montes credenciales Google, hojas
ni datos reales. No habilites acceso público si la construcción ARM64,
la revisión de imagen y las pruebas de seguridad siguen pendientes.

## HTTPS desde una escuela, después de autorización

1. Configura un DNS público que apunte a la IP aprobada de la VM. Permite
   TCP 80 y 443 en el NSG y el firewall del sistema. Restringe SSH a las
   IP administrativas. No crees reglas para 5432 ni 8000. Compose
   mantiene PostgreSQL y FastAPI en redes internas sin puertos publicados.
2. Exporta `USAER_EDGE_BIND=0.0.0.0` y
   `USAER_CADDYFILE=./deploy/oracle/Caddyfile.public`. Verifica otra vez
   `USAER_PUBLIC_HOST` y ejecuta `docker compose up -d --no-build`.
   Caddy tramitará el certificado cuando el DNS y los puertos respondan.
3. Desde la escuela ejecuta
   `curl --fail --show-error https://<DNS>/api/health`. Después abre
   `https://<DNS>/` con una cuenta ficticia individual. Comprueba el
   acceso autorizado y el rechazo entre escuelas antes de usar la URL
   para una prueba docente.

El trabajo `migrar` verifica la marca sintética y crea las tablas como
propietario. FastAPI comprueba que su rol operativo carezca de DDL.
`create_all` cubre tablas nuevas. Un cambio de columnas o de datos
requiere una migración explícita ensayada en una restauración independiente.
La cuenta `direccion.piloto` se crea solo en una base sin usuarios. Una
base vacía recibe dos escuelas y dos estudiantes ficticios.
Registra cuentas docentes individuales desde Dirección y retira el
archivo inicial de los procedimientos ordinarios una vez rotada la clave.

Consulta `docker compose stats --no-stream`, `docker compose ps -a`,
uso del volumen y registros rotados. Mide 25 sesiones desde una red
separada en la VM real. Las mediciones de Windows solo son de referencia.

## Respaldo y restauración

Configura un destino SSH existente fuera de la VM con carpeta
`usaer-backups`, alias restringido, clave del host verificada y una
clave pública `age` aprobada. Conserva la clave privada de descifrado
fuera de la VM. Ejecuta primero `bash deploy/oracle/respaldar.sh` con
`USAER_BACKUP_SSH` y `USAER_AGE_RECIPIENTS`. Verifica el hash y prueba
restauración antes de instalar y habilitar las unidades systemd de este
directorio. El proceso excluye las filas de sesiones.

Descifra y restaura en otro clúster o una base sintética vacía. Usa
`age -d -i <clave-privada> <respaldo.age> | pg_restore --no-owner
--exit-on-error --dbname=<base-independiente>` con credenciales locales
restringidas. Comprueba padrón, documentos e inicio de sesión nuevo.
Nunca uses `--clean` sobre el piloto activo.

## Migración e IA

La captura de Sheets sigue siendo de solo lectura y guarda lotes
versionados aparte. `tools/proyectar_copia_sintetica.py` admite padrón,
escuelas, anexos III, IV, V y VII y registro de visitas. Usa una base
local separada `usaer_spa_test_proyeccion_<nombre>` con esquema preparado
y el propietario en `USAER_PROYECCION_TEST_URL`. Ejecuta
`python tools/proyectar_copia_sintetica.py <copia.json>` para previsualizar,
y añade `--aplicar` solo después de conciliar. Las diferencias se
preservan. EPP, NEE, planeaciones versionadas, informes y otras relaciones
siguen en archivo de captura hasta validar su proyección.

El adaptador Gemini acepta exclusivamente un identificador de PDA
público. Requiere autorización explícita en la llamada y
`USAER_IA_CURRICULAR_HABILITADA=1`, `USAER_IA_GEMINI_MODELO` y
`USAER_IA_GEMINI_API_KEY` institucional. Compose no proporciona estas
variables. El generador local de la SPA conserva sus fuentes autorizadas
y su revisión docente.
