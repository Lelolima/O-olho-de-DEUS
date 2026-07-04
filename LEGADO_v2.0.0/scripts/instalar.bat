@echo off
REM Script de instalacao - O-olho-de-DEUS
echo ============================================================
echo   INSTALACAO - O-olho-de-DEUS
echo ============================================================
echo.

echo [1/3] Verificando pip...
python -m pip --version 2>nul
if errorlevel 1 (
    echo ERRO: pip nao encontrado
    exit /b 1
)
echo OK: pip disponivel
echo.

echo [2/3] Instalando dependencias...
python -m pip install -r requirements.txt
if errorlevel 1 (
    echo ERRO: Falha na instalacao
    exit /b 1
)
echo OK: Dependencias instaladas
echo.

echo [3/3] Criando pastas necessarias...
if not exist incidents\images mkdir incidents\images
if not exist logs mkdir logs
if not exist models mkdir models
echo OK: Pastas criadas
echo.

echo ============================================================
echo   INSTALACAO CONCLUIDA
echo ============================================================
echo.
echo Para validar: validar.bat
echo Para executar: python src\security_system.py
echo.
pause