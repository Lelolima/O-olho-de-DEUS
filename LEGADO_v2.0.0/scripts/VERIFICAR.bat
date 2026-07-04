@echo off
echo ============================================================
echo   VERIFICACAO DO REPOSITORIO
echo ============================================================
echo.

cd /d "%~dp0"

echo [1/4] Verificando commit local...
git log --oneline -5
echo.

echo [2/4] Verificando autor...
git log -1 --format="Autor: %%an <%%ae>"
echo.

echo [3/4] Verificando remote...
git remote -v
echo.

echo [4/4] Verificando branch...
git branch -a
echo.

echo ============================================================
echo   VERIFICACAO DO REPITORIO REMOTO
echo ============================================================
echo.
echo Abrindo repositorio no navegador...
start https://github.com/Lelolima/Project-Eyes-of-God-2.9
echo.
echo Verifique no GitHub:
echo 1. Todos os arquivos estao la?
echo 2. O README aparece corretamente?
echo 3. O commit mostra "Lelolima" como autor?
echo 4. Ha 18+ arquivos no total?
echo.
pause