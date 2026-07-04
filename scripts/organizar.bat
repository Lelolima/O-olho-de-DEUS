@echo off
echo === ORGANIZACAO DE ARQUIVOS ===
echo Separando projeto LEGADO (v2.0.0) do projeto NOVO (v3.0.1)
echo.

echo [1/5] Criando estrutura de pastas para LEGADO...
mkdir "LEGADO_v2.0.0\src" 2>nul
mkdir "LEGADO_v2.0.0\scripts" 2>nul
mkdir "LEGADO_v2.0.0\assets" 2>nul
mkdir "LEGADO_v2.0.0\tests" 2>nul
echo   Pastas LEGADO criadas

echo.
echo [2/5] Movendo arquivos LEGADO (v2.0.0)...

if exist "src\security_system.py" (
    move "src\security_system.py" "LEGADO_v2.0.0\src\"
    echo   Movido: security_system.py
)

if exist "requirements.txt" (
    move "requirements.txt" "LEGADO_v2.0.0\"
    echo   Movido: requirements.txt
)

if exist "config.json" (
    move "config.json" "LEGADO_v2.0.0\"
    echo   Movido: config.json
)

echo.
echo [3/5] Movendo testes LEGADO...

if exist "tests\test_security_system.py" (
    move "tests\test_security_system.py" "LEGADO_v2.0.0\tests\"
    echo   Movido: test_security_system.py
)

if exist "tests\validate_install.py" (
    move "tests\validate_install.py" "LEGADO_v2.0.0\tests\"
    echo   Movido: validate_install.py
)

echo.
echo [4/5] Movendo scripts LEGADO...

for %%f in (*.bat) do (
    if not "%%f"=="organizar.bat" (
        move "%%f" "LEGADO_v2.0.0\scripts\"
        echo   Movido: %%f
    )
)

if exist "deploy.py" (
    move "deploy.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: deploy.py
)

if exist "deploy-gitpython.py" (
    move "deploy-gitpython.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: deploy-gitpython.py
)

if exist "fix-and-push.py" (
    move "fix-and-push.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: fix-and-push.py
)

if exist "enviar-github.py" (
    move "enviar-github.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: enviar-github.py
)

if exist "check-repo.py" (
    move "check-repo.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: check-repo.py
)

if exist "upload-github-api.py" (
    move "upload-github-api.py" "LEGADO_v2.0.0\scripts\"
    echo   Movido: upload-github-api.py
)

echo.
echo [5/5] Movendo pasta assets...

if exist "assets" (
    move "assets" "LEGADO_v2.0.0\"
    echo   Movido: assets/
)

echo.
echo === ORGANIZACAO CONCLUÍDA ===
echo.
echo LEGADO (v2.0.0): %CD%\LEGADO_v2.0.0
echo NOVO (v3.0.1):   %CD%
echo.
echo Pressione qualquer tecla para sair...
pause >nul