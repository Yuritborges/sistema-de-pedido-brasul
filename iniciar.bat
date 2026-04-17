@echo off
chcp 65001 >nul
title Sistema de Cotacao - Brasul

echo ================================================
echo  Sistema de Cotacao - Brasul Construtora
echo ================================================
echo.

echo [1/2] Inicializando banco de dados...
python.exe -c "from app.data.database import init_db; init_db(); print('Banco de dados OK.')"
if %errorlevel% neq 0 (
    echo ERRO ao inicializar banco de dados.
    pause
    exit /b 1
)
echo.

echo [2/2] Iniciando o sistema...
python.exe main.py

pause
