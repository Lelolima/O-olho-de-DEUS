@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   ATUALIZAR REPOSITORIO - O-olho-de-DEUS
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/5] Adicionando todos os arquivos...
git add .
if errorlevel 1 (
    echo ERRO ao adicionar arquivos
    pause
    exit /b 1
)
echo OK

echo [2/5] Verificando alteracoes...
git status --short
echo.

echo [3/5] Criando commit...
git commit -m "README atualizado com animacoes SVG e correcoes

- Animacoes dashboard, fluxo, alerta, arquitetura
- Documentacao completa
- Autor: Lelolima" 2>&1
if errorlevel 1 echo (Nenhuma alteracao nova ou commit Mantido)
echo.

echo [4/5] Verificando remoto...
git remote -v
echo.

echo [5/5] Enviando para GitHub (force push)...
echo.
echo *** Se pedir senha, use GitHub Token ***
echo Token: https://github.com/settings/tokens
echo (Marque 'repo' ao criar)
echo.
git push -u origin main --force

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   ERRO NO PUSH
    echo ============================================================
    echo.
    echo Verifique:
    echo 1. Token GitHub: https://github.com/settings/tokens
    echo 2. SSH: ssh-keygen e github.com/settings/keys
    echo.
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   ENVIO CONCLUIDO!
echo ============================================================
echo.
echo Repositorio: https://github.com/Lelolima/Project-Eyes-of-God-2.9
echo.
echo O que foi enviado:
echo - README.md com animacoes SVG
echo - assets/ com 4 animacoes
echo - src/ com codigo corrigido
echo - tests/ com testes unitarios
echo - Scripts de instalacao/validacao
echo.
pause