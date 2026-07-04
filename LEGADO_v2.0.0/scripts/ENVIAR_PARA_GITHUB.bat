@echo off
setlocal enabledelayedexpansion

echo ============================================================
echo   ENVIAR PARA GITHUB - O-olho-de-DEUS
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/6] Configurando autor...
git config user.name "Lelolima"
git config user.email "lelolima@users.noreply.github.com"

echo [2/6] Corrigindo commit...
git commit --amend --author="Lelolima ^<lelolima@users.noreply.github.com^>" --no-edit 2>nul
if errorlevel 1 echo    (Commit pode ja estar correto)

echo [3/6] Renomeando branch...
git branch -M master main 2>nul
if errorlevel 1 echo    (Branch pode ja ser main)

echo [4/6] Configurando remote...
git remote remove origin 2>nul
git remote add origin https://github.com/Lelolima/Project-Eyes-of-God-2.9.git

echo [5/6] Enviando para GitHub...
echo.
echo *** ATENCAO ***
echo Se pedir senha, use um GitHub Token:
echo 1. Acesse: https://github.com/settings/tokens
echo 2. Generate new token (classic)
echo 3. Marque "repo" e generate
echo 4. Copie e cole o token como senha
echo.
echo Pressione qualquer tecla para continuar...
pause >nul

git push -u origin main --force

if errorlevel 1 (
    echo.
    echo ============================================================
    echo   ERRO NO PUSH
    echo ============================================================
    echo.
    echo Solucoes:
    echo 1. Use SSH: ssh-keygen e adicione em github.com/settings/keys
    echo 2. Use Token: https://github.com/settings/tokens
    echo ============================================================
    pause
    exit /b 1
)

echo.
echo ============================================================
echo   ENVIO CONCLUIDO COM SUCESSO!
echo ============================================================
echo.
echo Acesse: https://github.com/Lelolima/Project-Eyes-of-God-2.9
echo.
pause