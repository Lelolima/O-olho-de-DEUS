#!/usr/bin/env python3
"""Script de deploy autônomo para o repositório"""

import subprocess
import os
import sys

REPO_PATH = r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"
REMOTE_URL = "git@github.com:Lelolima/Project-Eyes-of-God-2.9.git"

def run_cmd(cmd, cwd=None):
    """Executa comando e retorna output"""
    result = subprocess.run(cmd, shell=True, cwd=cwd or REPO_PATH,
                          capture_output=True, text=True)
    return result.returncode, result.stdout, result.stderr

def main():
    print("=" * 60)
    print("DEPLOY AUTONOMO - O-olho-de-DEUS")
    print("=" * 60)
    print()

    # Passo 1: Git init
    print("[1/5] git init...")
    rc, out, err = run_cmd("git init")
    if rc != 0 and "already been initialized" not in err:
        print(f"  Erro: {err}")
    else:
        print("  OK: Repositório inicializado")

    # Passo 2: Configurar user
    print("[2/5] Configurando autor...")
    run_cmd("git config user.name 'Lelolima'")
    run_cmd("git config user.email 'lelolima@users.noreply.github.com'")
    print("  OK: Autor configurado")

    # Passo 3: Remote
    print("[3/5] Configurando remote...")
    run_cmd("git remote remove origin")
    rc, _, _ = run_cmd(f"git remote add origin {REMOTE_URL}")
    if rc != 0:
        print(f"  Aviso: Não foi possível adicionar remote")
    else:
        print("  OK: Remote configurado")

    # Passo 4: Add e commit
    print("[4/5] Adicionando arquivos e commit...")
    rc, out, err = run_cmd("git add .")
    if rc != 0:
        print(f"  Erro no add: {err}")
        return 1

    commit_msg = """v2.0: Sistema de segurança com IA

Correções e melhorias:
- Import cv2, remoção de código duplicado
- Funções notify_authorities e is_suspicious_behavior implementadas
- Validação anti-SSRF, logging com rotação
- Testes unitários, README completo
- 4 animações SVG/CSS demonstrativas

Autor: Lelolima"""

    rc, out, err = run_cmd(f"git commit -m \"{commit_msg}\"")
    if rc != 0:
        if "nothing to commit" in err:
            print("  Aviso: Nada para commitar")
        else:
            print(f"  Erro no commit: {err}")
            return 1
    else:
        print("  OK: Commit realizado")

    # Passo 5: Push
    print("[5/5] Push para GitHub...")
    print("  (Isto pode pedir sua senha/chave SSH)")
    rc, out, err = run_cmd("git push -u origin main --force")

    if rc != 0:
        print(f"\n  ERRO no push:")
        print(f"  {err}")
        print("\n" + "=" * 60)
        print("POSSIVEIS SOLUCOES:")
        print("1. Verifique se a chave SSH está configurada")
        print("2. Teste: ssh -T git@github.com")
        print("3. Adicione a chave em: https://github.com/settings/keys")
        print("=" * 60)
        return 1

    print("  OK: Push realizado com sucesso!")
    print()
    print("=" * 60)
    print("DEPLOY CONCLUIDO!")
    print("https://github.com/Lelolima/Project-Eyes-of-God-2.9")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())