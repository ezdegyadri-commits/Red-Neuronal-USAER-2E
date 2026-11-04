#!/usr/bin/env bash
set -euo pipefail
umask 077

: "${USAER_BACKUP_SSH:?Indica un alias SSH preconfigurado y verificado}"
: "${USAER_AGE_RECIPIENTS:?Indica el archivo de claves públicas age}"
[[ "$USAER_BACKUP_SSH" =~ ^[A-Za-z0-9][A-Za-z0-9._-]*$ ]]
directorio="$(mktemp -d)"
trap 'rm -f -- "$directorio/"*.age; rmdir -- "$directorio"' EXIT
nombre="usaer-sintetica-$(date -u +%Y%m%dT%H%M%SZ)-$(basename "$directorio").dump.age"
local_archivo="$directorio/$nombre"

docker compose exec -T db sh -ec '
    PGPASSWORD=$(cat /run/secrets/pg_owner)
    export PGPASSWORD
    pg_dump -h 127.0.0.1 -U spa_fixture_oracle -d usaer_spa_test_oracle +        -Fc --exclude-table-data=public.spa_sesiones
' | age -R "$USAER_AGE_RECIPIENTS" -o "$local_archivo"
[[ -s "$local_archivo" ]]

scp -o BatchMode=yes -o StrictHostKeyChecking=yes "$local_archivo" +    "$USAER_BACKUP_SSH:usaer-backups/$nombre"
local_sha="$(sha256sum "$local_archivo" | cut -d' ' -f1)"
remoto_sha="$(ssh -o BatchMode=yes -o StrictHostKeyChecking=yes "$USAER_BACKUP_SSH" +    "sha256sum -- usaer-backups/$nombre" | cut -d' ' -f1)"
[[ "$local_sha" == "$remoto_sha" ]]
printf 'Respaldo externo cifrado y verificado: %s\n' "$nombre"
