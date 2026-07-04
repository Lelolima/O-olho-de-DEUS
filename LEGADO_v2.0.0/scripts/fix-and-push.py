#!/usr/bin/env python3
"""Corrige autor e faz push para o repositorio"""

import subprocess
import os

os.chdir(r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido")

def git(args):
    return subprocess.run(["git"] + args, capture_output=True, text=True)

# Configurar autor correto
print("Configurando autor...")
git(["config", "user.name", "Lelolima"])
git(["config", "user.email", "lelolima@users.noreply.github.com"])

# Amend para corrigir autor
print("Corrigindo autor do commit...")
result = git(["commit", "--amend", "--author=Lelolima <lelolima@users.noreply.github.com>", "--no-edit"])
if result.returncode != 0:
    print(f"Aviso amend: {result.stderr}")

# Renomear branch
print("Renomeando branch para main...")
git(["branch", "-M", "master", "main"])

# Verificar status
print("\nStatus:")
print(git(["status", "--short"]).stdout)
print("\nLog:")
print(git(["log", "--oneline", "-1"]).stdout)

# Push
print("\nFazendo push...")
result = git(["push", "-u", "origin", "main", "--force"])
print(result.stdout)
if result.stderr:
    print(result.stderr)

if result.returncode == 0:
    print("\n✅ PUSH REALIZADO COM SUCESSO!")
    print("https://github.com/Lelolima/Project-Eyes-of-God-2.9")
else:
    print("\n❌ Erro no push. Verifique a conexão SSH.")