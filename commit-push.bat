@echo off
REM Script de commit e push para o repositório
REM Autor: Lelolima

cd /d "%~dp0"

echo ============================================================
echo   COMMIT E PUSH - O-olho-de-DEUS
echo ============================================================
echo.

REM Verificar se git está disponível
git --version >nul 2>&1
if errorlevel 1 (
    echo ERRO: Git nao encontrado. Instale o git primeiro.
    pause
    exit /b 1
)

echo [1/5] Inicializando repositório...
git init 2>&1
echo OK: Repositorio inicializado
echo.

echo [2/5] Configurando remote...
git remote remove origin 2>nul
git remote add origin git@github.com:Lelolima/Project-Eyes-of-God-2.9.git
echo OK: Remote configurado
echo.

echo [3/5] Adicionando arquivos...
git add . 2>&1
if errorlevel 1 (
    echo ERRO: Falha ao adicionar arquivos
    pause
    exit /b 1
)
echo OK: Arquivos adicionados
echo.

echo [4/5] Realizando commit...
git commit -m "v2.0: Sistema completo de seguranca com IA

Correcoes e melhorias implementadas:
- Adicionado import cv2 faltante
- Removido codigo duplicado
- Implementadas funcoes notify_authorities e is_suspicious_behavior
- Adicionado validacao de video source (anti-SSRF)
- Logging com rotacao de arquivos (10MB, 5 backups)
- .gitignore corrigido para Python
- requirements.txt com todas as dependencias
- Testes unitarios (15 testes)
- README completo com documentação

Novos recursos:
- 4 animacoes SVG/CSS demonstrativas
- Dashboard em tempo real
- Fluxo de detecção animado
- Sistema de alertas visuais
- Arquitetura do sistema documentada
- Scripts de instalacao e validacao (Windows)
- Benchmarks de performance

Seguranca:
- Hash SHA-256 com salt para dados faciais
- Validacao anti-SSRF
- Logs auditaveis
- LGPD Compliance - anonimizacao de dados

Autor: Lelolima"
if errorlevel 1 (
    echo ERRO: Falha no commit
    pause
    exit /b 1
)
echo OK: Commit realizado
echo.

echo [5/5] Push para GitHub...
echo.
echo *** ATENCAO: Certifique-se de que sua chave SSH esta configurada ***
echo.
git push -u origin main --force
if errorlevel 1 (
    echo.
    echo ERRO: Falha no push. Verifique:
    echo 1. Sua chave SSH esta configurada (ssh-keygen)
    echo 2. Voce tem permissao de write no repositorio
    echo 3. O repositorio existe: git@github.com:Lelolima/Project-Eyes-of-God-2.9.git
    echo.
    pause
    exit /b 1
)
echo OK: Push realizado com sucesso
echo.

echo ============================================================
echo   UPLOAD CONCLUIDO!
echo ============================================================
echo.
echo Repositorio: https://github.com/Lelolima/Project-Eyes-of-God-2.9
echo.
pause