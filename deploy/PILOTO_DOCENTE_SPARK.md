# Piloto docente privado en Spark

Desde `~/app`, con el código del piloto disponible, ejecuta en la terminal privada:

```sh
pixi run -e web-fastapi bash -c 'cd "$HOME/app/usaer2e" && python -m deploy.cuentas_docentes_spark'
```

Introduce tres claves aleatorias distintas, de al menos 16
caracteres, y entrégalas individualmente por un canal privado. El alta
conserva las cuentas habilitadas que ya tengan su asignación exacta.

| Cuenta | Escuela ficticia | Función |
| --- | --- | --- |
| `docente.a.piloto` | A | Maestra de Apoyo |
| `psicologia.a.piloto` | A | Psicología |
| `docente.b.piloto` | B | Maestra de Apoyo |

Desde el HTTPS privado, usa tres perfiles de navegador separados. Abre EPP
y crea una planeación individual, una aportación de guía grupal y un informe.
Para la guía grupal, Dirección debe registrar primero un alumno ficticio
con atención Grupal. Los dos alumnos iniciales tienen atención Individual.
Espera la confirmación de guardado, cierra sesión y reabre con la misma cuenta.
Comprueba que la cuenta B no abre documentos de A y que Psicología solo
puede editar las columnas de su función y no ve el informe de Apoyo.
Para la prueba de Spark, haz un solo acceso simultáneo por cuenta y anota
RAM, disco y CPU del panel antes y después. Tras un periodo de inactividad
sin sondeos, mide el primer acceso y repite la reapertura. Durante una
ventana acordada, repite la comprobación tras un reinicio del supervisor.

## Límites durante la prueba

La [matriz de paridad](../MATRIZ_PARIDAD_FUNCIONAL.md) detalla las diferencias.
Limita el piloto a prácticas sintéticas. Excluye informes administrativos,
emisión y firma de actas y oficios, firmas institucionales de EPP, envío de
formatos como documentos oficiales, importación de padrones reales, reportes
institucionales y el asistente histórico de ejemplo. El autoguardado por celda
se comprueba en la guía grupal. Usa el guardado explícito en los demás editores
y confirma la reapertura. El respaldo excluye sesiones e intentos de acceso.

## Actualización y respaldo

Antes de actualizar, desde `~/app`, con `pg_dump` 17 disponible, guarda
una copia nueva en un directorio privado:

```sh
install -d -m 700 "$HOME/.config/usaer-spark/respaldos"
pixi run -e web-fastapi bash -c 'cd "$HOME/app/usaer2e" && python -m deploy.respaldo_spark "$1"' +  respaldo "$HOME/.config/usaer-spark/respaldos/piloto-$(date -u +%Y%m%dT%H%M%SZ).dump"
```

Conserva una copia cifrada fuera de la pila. Comprueba la recuperación con
`pg_restore --no-owner --no-privileges --single-transaction` en una base
vacía de ensayo, usando una cuenta de restauración autorizada. Verifica que
`spa_sesiones` esté vacía y coteja usuarios, alumnos y documentos. La cuenta
operativa de la restauración requiere sus propios permisos.

En el clon actualiza la rama Spark mediante `git fetch` y `git merge --ff-only`
del commit revisado. Reejecuta el activador con el mismo host, base y cuenta
de migración y conserva el archivo privado de configuración para reutilizar
la credencial del rol operativo. Reinicia desde el supervisor en la ventana
acordada y verifica `/api/health` y una planeación guardada. La actualización
mantiene la base existente. La restauración se ensaya por separado.
