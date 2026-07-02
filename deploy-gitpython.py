#!/usr/bin/env python3
"""
Deploy autônomo usando GitPython - não requer comando git externo
"""

import os
import sys

# Tentar importar GitPython, se não existir, instalar
try:
    import git
except ImportError:
    print("Instalando GitPython...")
    import subprocess
    subprocess.check_call([sys.executable, "-m", "pip", "install", "gitpython", "-q"])
    import git

REPO_PATH = r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
REMOTE_URL = "git@github.com:Lelolima/Project-Eyes-of-God-2.9.git"

def main():
    print("=" * 60)
    print("DEPLOY AUTONOMO - GitPython")
    print("=" * 60)
    print()

    os.chdir(REPO_PATH)

    # Passo 1: Inicializar repositorio
    print("[1/6] Inicializando repositorio...")
    try:
        repo = git.Repo.init(REPO_PATH)
        print("  OK: Repositorio inicializado")
    except Exception as e:
        print(f"  Erro: {e}")
        return 1

    # Passo 2: Configurar user
    print("[2/6] Configurando autor...")
    repo.config_writer().set_value("user", "name", "Lelolima").release()
    repo.config_writer().set_value("user", "email", "lelolima@users.noreply.github.com").release()
    print("  OK: Autor configurado (Lelolima)")

    # Passo 3: Adicionar todos arquivos
    print("[3/6] Adicionando arquivos...")
    try:
        repo.git.add(all=True)
        print("  OK: Arquivos adicionados")
    except Exception as e:
        print(f"  Erro: {e}")
        return 1

    # Passo 4: Verificar status
    print("[4/6] Verificando alteracoes...")
    status = repo.git.status("--porcelain")
    if not status:
        print("  Nenhuma alteracao para commit")
    else:
        print(f"  Arquivos alterados: {len(status.splitlines())}")

    # Passo 5: Commit
    print("[5/6] Realizando commit...")
    commit_msg = """v2.0: Sistema de seguranca com IA

Correcoes e melhorias:
- Import cv2, remocao de codigo duplicado
- Funcoes notify_authorities e is_suspicious_behavior implementadas
- Validacao anti-SSRF, logging com rotacao
- Testes unitarios, README completo
- 4 animacoes SVG/CSS demonstrativas

Autor: Lelolima"""

    try:
        repo.git.commit(m=commit_msg)
        print("  OK: Commit realizado")
    except git.GitCommandError as e:
        if "nothing to commit" in str(e):
            print("  Aviso: Nada para commitar (usando commit anterior)")
        else:
            print(f"  Erro: {e}")
            return 1

    # Passo 6: Configurar remote
    print("[6/6] Configurando remote e push...")
    try:
        repo.create_remote("origin", REMOTE_URL)
        print(f"  OK: Remote adicionado: {REMOTE_URL}")
    except Exception as e:
        if "already exists" in str(e):
            repo.remotes.origin.set_url(REMOTE_URL)
            print(f"  OK: Remote atualizado: {REMOTE_URL}")
        else:
            print(f"  Aviso remote: {e}")

    print()
    print("=" * 60)
    print("PRE-PRONTO! Agora executando push...")
    print("=" * 60)
    print()
    print("NOTA: O push requer autenticacao SSH ou HTTPS.")
    print()
    print("Comandos manuais para push:")
    print(f"  cd {REPO_PATH}")
    print("  git push -u origin main --force")
    print()

    # Tentar push automatico
    print("Tentando push automatico...")
    try:
        origin = repo.remotes.origin
        origin.push(force=True).raise_if_error()
        print()
        print("=" * 60)
        print("PUSH REALIZADO COM SUCESSO!")
        print("https://github.com/Lelolima/Project-Eyes-of-God-2.9")
        print("=" * 60)
        return 0
    except git.GitCommandError as e:
        print(f"ERRO no push: {e}")
        print()
        print("SOLUCAO:")
        print("1. Configure SSH: ssh-keygen e adicione em github.com/settings/keys")
        print("2. Ou use HTTPS com token:")
        print(f"   git remote set-url origin https://github.com/Lelolima/Project-Eyes-of-God-2.9.git")
        print("3. Depois execute: git push -u origin main --force")
        return 1

if __name__ == "__main__":
    sys.exit(main())