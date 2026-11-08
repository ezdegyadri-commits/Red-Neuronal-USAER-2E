@echo off
title Cargar Base de Datos Real a Uppcoder (PostgreSQL)
cd /d "%~dp0"
echo ======================================================================
echo    CARGADOR OFICIAL DE DATOS REALES A POSTGRESQL (UPPCODER)
echo    USAER 02-E - Zona 001 | Ciclo Escolar 2026-2027
echo ======================================================================
echo.
echo Este script cargara en tu base de datos PostgreSQL de Uppcoder:
echo   - 8 Escuelas Primarias oficiales (Zona 001)
echo   - 15 Integrantes del personal
echo   - 15 Cuentas de usuarios con roles protegidos
echo   - 259 Alumnos reales del padron oficial
echo   - 167 Planeaciones historicas
echo   - 9 Evaluaciones Psicopedagogicas (EPP)
echo   - 103 Anexos de Deteccion de BAP
echo.
set /p DB_URL="Pega aqui la DATABASE_URL de PostgreSQL de Uppcoder: "

if "%DB_URL%"=="" (
    echo.
    echo ERROR: No ingresaste ninguna URL. Operacion cancelada.
    pause
    exit /b
)

echo.
echo Conectando y cargando datos reales a PostgreSQL...
python tools\migrar_base_datos_real_a_postgres.py --url "%DB_URL%"
echo.
echo ======================================================================
echo Proceso concluido.
echo ======================================================================
pause

