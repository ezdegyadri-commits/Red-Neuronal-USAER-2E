param(
    [string]$Python = $env:USAER_PILOTO_PYTHON,
    [string]$NpmCli = $env:USAER_NPM_CLI,
    [ValidateRange(1024, 65535)][int]$Puerto = 8010,
    [switch]$SoloCompilar,
    [switch]$ActivarPrivado,
    [string]$IpPrivada,
    [string]$NombreTLS,
    [string]$Certificado,
    [string]$ClaveTLS
)

$ErrorActionPreference = 'Stop'
$raiz = $PSScriptRoot
if (!$Python) {
    $entorno = Join-Path $raiz '.venv/Scripts/python.exe'
    $Python = if (Test-Path -LiteralPath $entorno) { $entorno } else { (Get-Command python.exe).Source }
}
$node = (Get-Command node.exe).Source
if ($NpmCli) {
    $NpmCli = (Resolve-Path -LiteralPath $NpmCli).Path
} else {
    $npm = (Get-Command npm.cmd).Source
}

function Invoke-Npm {
    if ($NpmCli) { & $node $NpmCli @args } else { & $npm @args }
    if ($LASTEXITCODE -ne 0) { throw 'Falló la preparación de React.' }
}

Push-Location $raiz
try {
    & $Python -c 'import fastapi, openpyxl, psycopg2, reportlab, sqlalchemy, uvicorn'
    if ($LASTEXITCODE -ne 0) {
        throw 'Instala las dependencias de requirements.txt en el intérprete de la candidata.'
    }
    Push-Location (Join-Path $raiz 'piloto_spa/frontend')
    try {
        if (!(Test-Path -LiteralPath 'node_modules/.package-lock.json')) { Invoke-Npm ci }
        Invoke-Npm run build
    } finally { Pop-Location }
    if ($SoloCompilar) { return }

    if (!$env:USAER_SPA_POSTGRES_TEST_URL) {
        throw 'Configura USAER_SPA_POSTGRES_TEST_URL con PostgreSQL sintético local y el rol operativo.'
    }
    if (!$ActivarPrivado -and ($IpPrivada -or $NombreTLS -or $Certificado -or $ClaveTLS)) {
        throw 'El perfil de red requiere -ActivarPrivado después de autorizar VPN, firewall y certificados.'
    }
    $modoAnterior = $env:USAER_SPA_MODE
    $rolAnterior = $env:USAER_SPA_ROLE
    $puertoAnterior = $env:USAER_SPA_PORT
    $urlAnterior = $env:DATABASE_URL
    $lanAnterior = $env:USAER_SPA_LAN_IP
    $hostAnterior = $env:USAER_SPA_TLS_HOST
    $certAnterior = $env:USAER_SPA_TLS_CERT
    $claveAnterior = $env:USAER_SPA_TLS_KEY
    try {
        $env:USAER_SPA_MODE = 'postgres-synthetic'
        $env:USAER_SPA_ROLE = 'runtime'
        $env:USAER_SPA_PORT = [string]$Puerto
        $env:DATABASE_URL = $env:USAER_SPA_POSTGRES_TEST_URL
        $env:USAER_SPA_LAN_IP = $null
        $env:USAER_SPA_TLS_HOST = $null
        $env:USAER_SPA_TLS_CERT = $null
        $env:USAER_SPA_TLS_KEY = $null
        if ($ActivarPrivado) {
            if (!$IpPrivada -or !$NombreTLS -or !$Certificado -or !$ClaveTLS) {
                throw 'Indica -IpPrivada, -NombreTLS, -Certificado y -ClaveTLS.'
            }
            if (!(Get-NetIPAddress -AddressFamily IPv4 -IPAddress $IpPrivada -ErrorAction SilentlyContinue)) {
                throw 'La IP indicada no está asignada a este equipo.'
            }
            $ips = [Net.Dns]::GetHostAddresses($NombreTLS)
            if (!$ips -or ($ips | Where-Object { $_.IPAddressToString -ne $IpPrivada })) {
                throw 'El nombre privado debe resolver exclusivamente a la IP de escucha.'
            }
            $env:USAER_SPA_LAN_IP = $IpPrivada
            $env:USAER_SPA_TLS_HOST = $NombreTLS
            $env:USAER_SPA_TLS_CERT = (Resolve-Path -LiteralPath $Certificado).Path
            $env:USAER_SPA_TLS_KEY = (Resolve-Path -LiteralPath $ClaveTLS).Path
            & $Python (Join-Path $raiz 'tools/verificar_tls_privado.py')
            if ($LASTEXITCODE -ne 0) { throw 'El certificado y la clave no pasaron la comprobación privada.' }
        }
        & $Python -c 'from piloto_spa.backend.main import verificar_base_piloto; from data.database import get_engine; verificar_base_piloto(); get_engine()'
        if ($LASTEXITCODE -ne 0) { throw 'La base sintética o el esquema operativo no pasaron la comprobación.' }
        if ($ActivarPrivado) {
            Write-Host "Candidata privada: https://${NombreTLS}:$Puerto/  (Ctrl+C para detener)"
        } else {
            Write-Host "Candidata local: http://127.0.0.1:$Puerto/  (Ctrl+C para detener)"
        }
        & $Python (Join-Path $raiz 'iniciar_piloto.py')
        if ($LASTEXITCODE -ne 0) { throw 'FastAPI terminó con un error. Revisa el mensaje de arranque.' }
    } finally {
        $env:USAER_SPA_MODE = $modoAnterior
        $env:USAER_SPA_ROLE = $rolAnterior
        $env:USAER_SPA_PORT = $puertoAnterior
        $env:DATABASE_URL = $urlAnterior
        $env:USAER_SPA_LAN_IP = $lanAnterior
        $env:USAER_SPA_TLS_HOST = $hostAnterior
        $env:USAER_SPA_TLS_CERT = $certAnterior
        $env:USAER_SPA_TLS_KEY = $claveAnterior
    }
} finally { Pop-Location }
