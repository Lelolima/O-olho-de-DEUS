#!/usr/bin/env python3
"""
Envia o projeto para o GitHub de forma autonoma
"""
import subprocess
import sys

REPO = r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"

def run(cmd, show_output=True):
    result = subprocess.run(cmd, shell=True, cwd=REPO,
                          capture_output=True, text=True, encoding='utf-8', errors='ignore')
    if show_output:
        if result.stdout: print(result.stdout)
        if result.stderr: print(result.stderr)
    return result.returncode, result.stdout, result.stderr

print("=" * 60)
print("ENVIANDO PARA GITHUB")
print("=" * 60)

# Configurar autor
print("\n[1/5] Configurando autor...")
run('git config user.name "Lelolima"')
run('git config user.email "lelolima@users.noreply.github.com"')

# Amend commit
print("\n[2/5] Corrigindo autor do commit...")
rc, out, err = run('git commit --amend --author="Lelolima <lelolima@users.noreply.github.com>" --no-edit --quiet')
if rc == 0:
    print("OK: Autor corrigido")
else:
    print(f"Info: {err}")

# Renomear branch
print("\n[3/5] Renomeando branch para main...")
run('git branch -M master main')

# Configurar remote
print("\n[4/5] Configurando remote...")
run('git remote remove origin')
run('git remote add origin https://github.com/Lelolima/Project-Eyes-of-God-2.9.git')

# Push
print("\n[5/5] Fazendo push (isto pode demorar)...")
print("Nota: Se pedir senha, use GitHub Token ou configure SSH")
print("-" * 60)
rc, out, err = run('git push -u origin main --force')
print("-" * 60)

if rc == 0:
    print("\n" + "=" * 60)
    print("SUCESSO! Repositorio atualizado:")
    print("https://github.com/Lelolima/Project-Eyes-of-God-2.9")
    print("=" * 60)
else:
    print("\n" + "=" * 60)
    print("O Push requer autenticacao:")
    print("1) HTTPS: Cole seu GitHub Token como senha")
    print("   Token: https://github.com/settings/tokens")
    print("2) SSH: ssh-keygen e adicione em github.com/settings/keys")
    print("=" * 60)
    print(f"\nErro: {err}")