# 🛡️ Script Seguro de Envio para GitHub
# Execute antes de commitar para garantir que nenhum segredo seja enviado

Write-Host "=== VERIFICAÇÃO DE SEGURANÇA PRÉ-COMMIT ===" -ForegroundColor Cyan
Write-Host ""

$basePath = "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
$hasCriticalIssues = $false

# 1. Verifica se .env existe na raiz
Write-Host "[1/5] Verificando arquivos sensíveis..." -ForegroundColor Yellow

$sensitiveFiles = @(
    ".env",
    "*.key",
    "logs\*",
    "evidence\*",
    "forensic_logs\*",
    "__pycache__",
    "*.log"
)

foreach ($file in $sensitiveFiles) {
    $items = Get-ChildItem -Path $basePath -Filter $file -Recurse -ErrorAction SilentlyContinue
    if ($items.Count -gt 0) {
        # Verifica se está no .gitignore
        $gitignore = Get-Content "$basePath\.gitignore" -Raw
        $fileName = $file.TrimEnd('*')
        if ($gitignore -notlike "*$fileName*") {
            Write-Host "  ⚠️  ATENÇÃO: $file encontrado e NÃO está no .gitignore!" -ForegroundColor Red
            $hasCriticalIssues = $true
        } else {
            Write-Host "  ✓  $file está no .gitignore" -ForegroundColor Green
        }
    }
}

# 2. Verifica se .env existe
Write-Host ""
Write-Host "[2/5] Verificando existência de .env..." -ForegroundColor Yellow
if (Test-Path "$basePath\.env") {
    Write-Host "  ⚠️  CRÍTICO: Arquivo .env encontrado na raiz!" -ForegroundColor Red
    Write-Host "      Este arquivo NÃO deve ser commitado!" -ForegroundColor Red
    $hasCriticalIssues = $true

    # Oferece para remover
    $response = Read-Host "  Deseja mover .env para LEGADO_v2.0.0/? (s/n)"
    if ($response -eq 's' -or $response -eq 'S') {
        Move-Item "$basePath\.env" "$basePath\LEGADO_v2.0.0\" -Force
        Write-Host "      ✓  .env movido para LEGADO_v2.0.0/" -ForegroundColor Green
    }
} else {
    Write-Host "  ✓  Nenhum arquivo .env encontrado" -ForegroundColor Green
}

# 3. Verifica .gitignore
Write-Host ""
Write-Host "[3/5] Verificando .gitignore..." -ForegroundColor Yellow
$gitignoreContent = Get-Content "$basePath\.gitignore" -Raw
$requiredIgnores = @('.env', '*.key', '*.log', '__pycache__/', 'logs/')

foreach ($ignore in $requiredIgnores) {
    if ($gitignoreContent -like "*$ignore*") {
        Write-Host "  ✓  $ignore está no .gitignore" -ForegroundColor Green
    } else {
        Write-Host "  ⚠️  $ignore NÃO está no .gitignore!" -ForegroundColor Yellow
    }
}

# 4. Verifica staging area
Write-Host ""
Write-Host "[4/5] Verificando arquivos em staging para commit..." -ForegroundColor Yellow
$stagedFiles = git diff --cached --name-only 2>$null

if ($null -eq $stagedFiles) {
    Write-Host "  ℹ️  Nenhum arquivo em staging area" -ForegroundColor Cyan
} else {
    foreach ($file in $stagedFiles) {
        if ($file -like "*.env" -or $file -like "*.key" -or $file -like "*.log") {
            Write-Host "  ⚠️  CRÍTICO: $file está em staging e será commitado!" -ForegroundColor Red
            $hasCriticalIssues = $true
        }
    }

    if (-not $hasCriticalIssues) {
        Write-Host "  ✓  Nenhum arquivo sensível em staging" -ForegroundColor Green
    }
}

# 5. Verifica .env.example (deve ser template, não real)
Write-Host ""
Write-Host "[5/5] Verificando .env.example (deve ser template)..." -ForegroundColor Yellow
if (Test-Path "$basePath\.env.example") {
    $envExample = Get-Content "$basePath\.env.example" -Raw

    # Verifica se tem segredos reais (não templates)
    $hasRealSecrets = $false

    if ($envExample -like "*sk-*" -or $envExample -like "*ghp_*" -or $envExample -like "*xox*") {
        Write-Host "  ⚠️  ATENÇÃO: .env.example pode conter chaves reais!" -ForegroundColor Red
        $hasRealSecrets = $true
    }

    if ($envExample -like "*sua-chave*" -or $envExample -like "*seu-*" -or $envExample -like "*aqui*") {
        Write-Host "  ✓  .env.example contém apenas templates (palavras genéricas)" -ForegroundColor Green
    } elseif (-not $hasRealSecrets) {
        Write-Host "  ℹ️  .env.example parece válido" -ForegroundColor Cyan
    }

    if ($hasRealSecrets) {
        $hasCriticalIssues = $true
    }
}

# Resumo final
Write-Host ""
Write-Host "=== RESUMO DA VERIFICAÇÃO ===" -ForegroundColor Cyan

if ($hasCriticalIssues) {
    Write-Host ""
    Write-Host "  ⛔ CRÍTICO: Problemas de segurança encontrados!" -ForegroundColor Red
    Write-Host "     Resolva antes de fazer commit." -ForegroundColor Red
    Write-Host ""
    Write-Host "  Ações recomendadas:" -ForegroundColor Yellow
    Write-Host "  1. Remova .env se existir" -ForegroundColor White
    Write-Host "  2. Verifique staging area: git status" -ForegroundColor White
    Write-Host "  3. Remova arquivos sensíveis: git reset HEAD <arquivo>" -ForegroundColor White
    exit 1
} else {
    Write-Host ""
    Write-Host "  ✅ SEM PROBLEMAS CRÍTICOS ENCONTRADOS" -ForegroundColor Green
    Write-Host "     Pode prosseguir com o commit." -ForegroundColor Green
    Write-Host ""

    # Oferece próximo passo
    Write-Host "  Próximo passo: git commit -m \"sua mensagem\"" -ForegroundColor Cyan
}