# Piloto sintético en Uppcoder · web-fastapi

Usa el servicio FastAPI del stack existente y su PostgreSQL 17 interno. El
perfil usa por defecto `zja3x8j3-postgresql-17:5432`, base `usaer_2e_2_0`,
usuario `ezdegyadri`. Mantén el stack privado durante el ensayo.

## Actualizar e instalar

En la terminal de **web-fastapi**, usa el mismo intérprete Python del servicio:

```sh
cd ~/app/usaer2e
git fetch origin refs/heads/codex-oracle-arm64:refs/remotes/origin/codex-oracle-arm64
git switch codex-oracle-arm64
git merge --ff-only origin/codex-oracle-arm64
python -m pip install -r requirements.txt
python -m pip check
test -s piloto_spa/frontend/dist/index.html
test -s piloto_spa/frontend/dist/app.js
test -s piloto_spa/frontend/dist/app.css
```

Usa el frontend compilado que trae la rama. La instalación Python conserva
los paquetes ya instalados que satisfacen los requisitos. Si el proveedor
añadió dependencias a un archivo versionado del clon, revisa primero
`git status --short`. El avance rápido preserva los cambios locales y
se detiene si interfieren.

## Entorno administrado

Configura estas variables en el entorno persistente del servicio **web-fastapi**.
Los secretos se guardan en Uppcoder y deben estar disponibles para la terminal
de migración y para el servicio que inicia la aplicación.

| Variable | Valor |
| --- | --- |
| `USAER_UPPCODER_SYNTHETIC` | `1` |
| `USAER_UPPCODER_PUBLIC_HOST` | Host exacto de la dirección HTTPS que muestra el stack, sin `https://`, puerto ni ruta |
| `USAER_UPPCODER_DB_HOST`, `USAER_UPPCODER_DB_NAME`, `USAER_UPPCODER_DB_USER` | Opcionales. Destino interno, base sintética y rol restringido |
| `USAER_UPPCODER_DB_PASSWORD` | Contraseña del usuario PostgreSQL configurado, como secreto |
| `USAER_UPPCODER_DIRECTOR_PASSWORD` | Contraseña inicial aleatoria de al menos 16 caracteres, como secreto |
| `PORT` | El puerto asignado por Uppcoder. Si el entorno no lo define, el arranque usa 8000 |
| `USAER_UPPCODER_PROXY_IPS` | Opcional. Usa las IP o redes concretas que confirme el operador del proxy si se necesita la IP real del cliente. El valor por defecto confía solo en loopback |

Confirma que la base está dedicada a la prueba y el rol puede crear tablas
en `public`. La migración rechaza tablas USAER preexistentes sin marca
sintética. No ejecutes esta operación contra una base con expedientes reales.

```sh
cd ~/app/usaer2e
python -m deploy.uppcoder migrar
```

La migración crea las tablas y dos alumnos ficticios. Puedes repetirla.
La contraseña inicial se usa solo para crear `direccion.piloto`.
Después se puede retirar ese secreto del entorno y cambiar la contraseña
desde la aplicación. Conserva el secreto PostgreSQL.

## Arranque persistente y comprobación

En la tarjeta FastAPI del stack, conecta o actualiza el repositorio con
la rama `codex-oracle-arm64`. Uppcoder ejecuta `startup-app.sh` desde
la carpeta de la aplicación. Si el servicio permite indicar un comando
personalizado con el clon existente, usa `sh ~/app/usaer2e/startup-app.sh`.
El proceso queda bajo el supervisor del stack. Ejecutar ese script en
la terminal solo sirve como diagnóstico en primer plano.
[Guía oficial de Uppcoder](https://portal.uppcoder.com/guides/deploy-fastapi-postgresql)

Abre el enlace HTTPS de la tarjeta y prueba con el navegador autenticado
en Uppcoder si el stack sigue privado. Si la ruta es accesible al cliente
de diagnóstico, comprueba:

```sh
curl -fsS 'https://HOST_HTTPS_DEL_STACK/api/health'
curl -fsS -o /dev/null 'https://HOST_HTTPS_DEL_STACK/'
curl -fsS -o /dev/null 'https://HOST_HTTPS_DEL_STACK/assets/app.js'
```

La salud responde `status: ok` solo después del arranque y la conexión a
PostgreSQL. La SPA exige una cuenta para consultar alumnado. Verifica
el inicio de sesión con `direccion.piloto` y usa exclusivamente el
padrón ficticio. Mantén el acceso público deshabilitado durante esta
comprobación.
