@echo off
REM Script de validação rápida - O-olho-de-DEUS
echo ============================================================
echo   VALIDACAO DE INSTALACAO - O-olho-de-DEUS
echo ============================================================
echo.

REM Verificar Python
echo [1/5] Verificando Python...
python --version 2>nul
if errorlevel 1 (
    echo ERRO: Python nao encontrado
    exit /b 1
)
echo OK: Python instalado
echo.

REM Verificar dependencias
echo [2/5] Verificando dependencias...
python -c "import cv2" 2>nul && echo OK: opencv-python || echo ERRO: cv2 faltando
python -c "import numpy" 2>nul && echo OK: numpy || echo ERRO: numpy faltando
python -c "import tensorflow" 2>nul && echo OK: tensorflow || echo ERRO: tensorflow faltando
python -c "import requests" 2>nul && echo OK: requests || echo ERRO: requests faltando
echo.

REM Verificar sintaxe
echo [3/5] Verificando sintaxe...
python -m py_compile src\security_system.py 2>&1
if errorlevel 1 (
    echo ERRO: Sintaxe invalida
    exit /b 1
)
echo OK: Sintaxe valida
echo.

REM Verificar config
echo [4/5] Verificando config.json...
if not exist config.json (
    echo ERRO: config.json nao encontrado
    exit /b 1
)
python -c "import json; json.load(open('config.json'))" 2>&1
if errorlevel 1 (
    echo ERRO: config.json invalido
    exit /b 1
)
echo OK: config.json valido
echo.

REM Verificar estrutura
echo [5/5] Verificando estrutura de pastas...
if not exist src\security_system.py (
    echo ERRO: src/security_system.py nao encontrado
    exit /b 1
)
echo OK: Estrutura completa
echo.

echo ============================================================
echo   VALIDACAO CONCLUIDA - SISTEMA PRONTO
echo ============================================================
echo.
echo Para instalar dependencias: pip install -r requirements.txt
echo Para executar: python src\security_system.py
echo.
pause