# Activar el piloto privado de USAER en Uppcoder Spark

Ejecuta en la terminal de `web-fastapi`. Copia el **host** del enlace HTTPS
del stack, sin esquema ni ruta. Conserva el acceso privado.
Si el volumen está lleno y Git no puede escribir, recupera primero la
caché de pip con `cd ~/app && pixi run -e web-fastapi python -m pip cache purge`.

```sh
cd ~/app/usaer2e
git fetch origin refs/heads/codex-uppcoder-spark:refs/remotes/origin/codex-uppcoder-spark
git switch -c codex-uppcoder-spark --track origin/codex-uppcoder-spark
cd ~/app
pixi run -e web-fastapi python usaer2e/deploy/activar_spark.py --host 'HOST_DEL_STACK' --limpiar-cache
```

En una actualización posterior, sustituye `git switch -c …` por
`git switch codex-uppcoder-spark && git merge --ff-only origin/codex-uppcoder-spark`.
Si la terminal ya tiene activado el Python de `web-fastapi`, usa ese
intérprete para el mismo comando. Si Pixi está administrado desde otra
carpeta, ejecuta `pixi run -e web-fastapi` desde el directorio de su
manifiesto y pasa la ruta absoluta al script.

El instalador informa el espacio libre, limpia únicamente la caché de pip
y `node_modules` del clon cuando se solicita, y usa los assets React
compilados. Requiere 400 MiB libres cuando necesita instalar dependencias
y 64 MiB cuando ya están satisfechas. Comprueba además el consumo de disco
del panel, porque la cuota del proveedor puede diferir del espacio libre
que informa Linux. Para identificar otros consumos, usa:

```sh
df -h ~/app
du -x -h -d 1 ~/app ~/.cache 2>/dev/null | sort -h
```

El perfil usa primero el secreto que Uppcoder inyecta para la conexión
exacta a la base existente. Si la terminal no recibe ese secreto,
el instalador lo pide sin eco y lo conserva solo en
`~/.config/usaer-spark/config.json` con permisos `0600`. No pases
contraseñas como argumentos ni imprimas variables de entorno. La clave
inicial de `direccion.piloto` se pide solo en la primera migración y
queda almacenada como hash en PostgreSQL. La migración solo admite el
perfil sintético y protege bases USAER previamente pobladas.
[Conexión PostgreSQL y supervisor de Uppcoder](https://portal.uppcoder.com/guides/deploy-fastapi-postgresql)

Tras migrar, el instalador respalda el ejemplo de `~/app/main.py` fuera
de Git y deja el adaptador que importa la SPA. El supervisor existente
detecta el cambio en el módulo. Si el proceso no se recarga, usa **Restart**
en la página del stack. No inicies otro Uvicorn. Comprueba que el proceso
del supervisor sigue siendo único:

```sh
ps -eo pid,ppid,rss,etime,args | grep '[u]vicorn'
```

Desde el navegador autenticado abre el enlace HTTPS del stack, consulta
`/api/health`, inicia sesión y prueba con el padrón ficticio. Guarda una
planeación, reinicia desde el panel, vuelve a abrirla y descarga su PDF.
Para medir Spark, registra RAM, disco y CPU del panel antes y después.
Prueba primero una cuenta. Amplía a 15 solo con margen confirmado en el
presupuesto diario, de forma escalonada, y detente si suben los errores
o se acerca el límite.
