# 🫰 INSTRUÇÕES RÁPIDAS - ORGANIZAR ARQUIVOS

## Execute a Organização

### Opção 1: Duplo Clique (Mais Fácil)

1. Abra a pasta: `C:\Users\Thinkin pad 8g\olho-de-deus-corrigido`
2. **Duplo clique em `organizar.bat`**
3. Aguarde a mensagem "ORGANIZAÇÃO CONCLUÍDA"

### Opção 2: PowerShell

```powershell
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
.\organizar.bat
```

### Opção 3: PowerShell Script

```powershell
cd "C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
powershell -ExecutionPolicy Bypass -File ".\ORGANIZAR_ARQUIVOS.ps1"
```

---

## O Que Vai Acontecer

O script vai:

1. ✅ Criar pasta `LEGADO_v2.0.0/`
2. ✅ Mover `security_system.py` → `LEGADO_v2.0.0/src/`
3. ✅ Mover `requirements.txt`, `config.json` → `LEGADO_v2.0.0/`
4. ✅ Mover testes antigos → `LEGADO_v2.0.0/tests/`
5. ✅ Mover scripts `.bat` e `.py` antigos → `LEGADO_v2.0.0/scripts/`
6. ✅ Mover pasta `assets/` → `LEGADO_v2.0.0/`

---

## Após a Organização

### Projeto NOVO v3.0.1 (Raiz)
- `src/edge/`, `src/cloud/`, `src/forensic/`, etc.
- `main.py`, `pyproject.toml`
- Documentação completa

### Projeto LEGADO v2.0.0
- `LEGADO_v2.0.0/src/security_system.py`
- `LEGADO_v2.0.0/scripts/` (scripts antigos)
- `LEGADO_v2.0.0/MANIFESTO_LEGADO.md` (explicação)

---

## Verificação

Após executar, **NÃO** deve haver na raiz:
- ❌ `security_system.py`
- ❌ `requirements.txt`
- ❌ `config.json`
- ❌ Arquivos `.bat` (exceto `organizar.bat`)
- ❌ Pasta `assets/`

Se ainda houver, execute o script novamente.

---

**Criado:** 2026-07-04
**Versão:** 3.0.1