# Script de Organização - Separar Legado v2.0.0 do Novo v3.0.1
# Execute este script para organizar os arquivos

$basePath = "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
$legacyPath = "$basePath\LEGADO_v2.0.0"

Write-Host "=== ORGANIZAÇÃO DE ARQUIVOS ===" -ForegroundColor Cyan
Write-Host "Separando projeto LEGADO (v2.0.0) do projeto NOVO (v3.0.1)"
Write-Host ""

# Criar estrutura de pastas LEGADO
Write-Host "[1/5] Criando estrutura de pastas para LEGADO..." -ForegroundColor Yellow
$folders = @(
    "$legacyPath\src",
    "$legacyPath\tests",
    "$legacyPath\assets",
    "$legacyPath\scripts"
)

foreach ($folder in $folders) {
    if (!(Test-Path $folder)) {
        New-Item -ItemType Directory -Path $folder -Force | Out-Null
        Write-Host "  Criado: $folder" -ForegroundColor Green
    }
}

# Mover arquivos LEGADO
Write-Host ""
Write-Host "[2/5] Movendo arquivos LEGADO (v2.0.0)..." -ForegroundColor Yellow

$legacyFiles = @(
    @{Source="security_system.py"; Dest="src\security_system.py"},
    @{Source="requirements.txt"; Dest="requirements.txt"},
    @{Source="config.json"; Dest="config.json"}
)

foreach ($file in $legacyFiles) {
    $srcPath = "$basePath\$($file.Source)"
    $destPath = "$legacyPath\$($file.Dest)"
    if (Test-Path $srcPath) {
        Move-Item -Path $srcPath -Destination $destPath -Force
        Write-Host "  Movido: $($file.Source)" -ForegroundColor Green
    }
}

# Mover testes LEGADO
Write-Host ""
Write-Host "[3/5] Movendo testes LEGADO..." -ForegroundColor Yellow

$legacyTests = @(
    "test_security_system.py",
    "validate_install.py"
)

foreach ($test in $legacyTests) {
    $srcPath = "$basePath\tests\$test"
    $destPath = "$legacyPath\tests\$test"
    if (Test-Path $srcPath) {
        Move-Item -Path $srcPath -Destination $destPath -Force
        Write-Host "  Movido: $test" -ForegroundColor Green
    }
}

# Mover scripts LEGADO
Write-Host ""
Write-Host "[4/5] Movendo scripts LEGADO..." -ForegroundColor Yellow

$legacyScripts = @(
    "*.bat",
    "deploy.py",
    "deploy-gitpython.py",
    "fix-and-push.py",
    "enviar-github.py",
    "check-repo.py",
    "upload-github-api.py"
)

foreach ($script in $legacyScripts) {
    $items = Get-ChildItem -Path $basePath -Filter $script -File
    foreach ($item in $items) {
        Move-Item -Path $item.FullName -Destination "$legacyPath\scripts\$($item.Name)" -Force
        Write-Host "  Movido: $($item.Name)" -ForegroundColor Green
    }
}

# Mover assets
Write-Host ""
Write-Host "[5/5] Movendo pasta assets..." -ForegroundColor Yellow

if (Test-Path "$basePath\assets") {
    Move-Item -Path "$basePath\assets" -Destination "$legacyPath\assets" -Force
    Write-Host "  Movido: assets/" -ForegroundColor Green
}

# Criar arquivo de manifesto LEGADO
Write-Host ""
Write-Host "Criando manifesto do projeto LEGADO..." -ForegroundColor Yellow

$manifesto = @"
# PROJETO LEGADO - Olho de Deus v2.0.0

**Data da Movimentação:** $(Get-Date -Format "yyyy-MM-dd")
**Motivo:** Separação do projeto novo v3.0.1 para organização

## ARQUIVOS CONTIDOS NESTA PASTA

### Código Principal (src/)
- security_system.py - Sistema original v2.0.0 (445 linhas)

### Testes (tests/)
- test_security_system.py - Testes unitários originais (10 testes)
- validate_install.py - Script de validação de instalação

### Scripts (scripts/)
- *.bat - Scripts Windows de deploy/instalação
- deploy.py, deploy-gitpython.py - Scripts de deploy Python
- fix-and-push.py, enviar-github.py - Scripts de Git
- check-repo.py, upload-github-api.py - Utilitários Git

### Assets
- assets/ - SVGs demonstrativos do dashboard

### Configuração
- requirements.txt - Dependências pip antigas
- config.json - Configuração antiga do sistema

## NÃO USAR ESTES ARQUIVOS PARA O PROJETO v3.0.1!

Os arquivos nesta pasta são do projeto LEGADO v2.0.0 e NÃO DEVEM ser usados
para o projeto novo v3.0.1. Eles foram movidos para:
- Preservar o histórico do projeto original
- Permitir consulta de código antigo se necessário
- Manter scripts de deploy originais como referência

## PROJETO NOVO v3.0.1

O projeto NOVO v3.0.1 está na pasta raiz e contém:
- src/edge/, src/cloud/, src/forensic/, src/privacy/, src/fairness/, src/hitl/
- main.py - Entry point novo
- pyproject.toml - Configuração Poetry
- setup_secure_install.py - Instalação segura
- docker-compose.yml - Docker support
- Documentação completa (CLAUDE.md, AUDITORIA_*.md, etc.)

"@

$manifesto | Out-File -FilePath "$legacyPath\MANIFESTO_LEGADO.md" -Encoding UTF8
Write-Host "  Criado: MANIFESTO_LEGADO.md" -ForegroundColor Green

# Resumo final
Write-Host ""
Write-Host "=== ORGANIZAÇÃO CONCLUÍDA ===" -ForegroundColor Cyan
Write-Host ""
Write-Host "LEGADO (v2.0.0): $legacyPath" -ForegroundColor Yellow
Write-Host "NOVO (v3.0.1):   $basePath" -ForegroundColor Green
Write-Host ""
Write-Host "Arquivos movidos:" -ForegroundColor White
Write-Host "  - security_system.py (código original)" -ForegroundColor Gray
Write-Host "  - requirements.txt, config.json" -ForegroundColor Gray
Write-Host "  - test_security_system.py, validate_install.py" -ForegroundColor Gray
Write-Host "  - *.bat scripts de deploy" -ForegroundColor Gray
Write-Host "  - assets/ (SVGs)" -ForegroundColor Gray
Write-Host ""
Write-Host "Agora você pode:" -ForegroundColor Cyan
Write-Host "  1. Renomear '$basePath' para 'Olho-de-Deus-CORRIGIDO-3.0.1'" -ForegroundColor White
Write-Host "  2. Renomear '$legacyPath' para 'Olho-de-Deus-LEGADO-2.0.0'" -ForegroundColor White
Write-Host ""