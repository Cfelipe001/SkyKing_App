@echo off
REM ======================================
REM SKYKING - SCRIPT DE INICIO RAPIDO
REM ======================================

echo ================================================================================
echo           SKYKING - INICIANDO SISTEMA
echo ================================================================================
echo.

REM Verificar si existe el entorno virtual
if not exist ".venv" (
    echo [ERROR] No se encontro el entorno virtual .venv
    echo.
    echo Por favor ejecuta primero:
    echo    python -m venv .venv
    echo    .venv\Scripts\activate
    echo    pip install -r requirements.txt
    echo.
    pause
    exit /b 1
)

REM Activar entorno virtual
echo [1/3] Activando entorno virtual...
call .venv\Scripts\activate.bat
if errorlevel 1 (
    echo [ERROR] No se pudo activar el entorno virtual
    pause
    exit /b 1
)

REM Verificar que existe el archivo .env
echo [2/3] Verificando configuracion...
if not exist ".env" (
    echo [ADVERTENCIA] No se encontro el archivo .env
    echo Se copiara .env.example como plantilla
    copy .env.example .env
    echo.
    echo IMPORTANTE: Edita el archivo .env con tus credenciales antes de continuar
    echo.
    pause
)

REM Ejecutar el servidor
echo [3/3] Iniciando servidor Flask...
echo.
python run.py

REM Si el servidor se detiene, pausar para ver errores
if errorlevel 1 (
    echo.
    echo [ERROR] El servidor se detuvo con errores
    echo Revisa los mensajes de error arriba
    echo.
    pause
)
