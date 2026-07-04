#!/usr/bin/env python3
"""Verifica o repo local e tenta push via subprocess"""
import subprocess
import os

os.chdir(r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido")

print("=" * 60)
print("VERIFICACAO DO REPOSITORIO LOCAL")
print("=" * 60)

# Git status
print("\n[1/4] Git status:")
result = subprocess.run(["git", "status", "--short"], capture_output=True, text=True)
if result.stdout.strip():
    print(f"  Arquivos modificados: {result.stdout.strip()}")
else:
    print("  Tudo em dia (working tree clean)")

# Git log
print("\n[2/4] Últimos commits:")
result = subprocess.run(["git", "log", "--oneline", "-3"], capture_output=True, text=True)
print(result.stdout)

# Remote
print("[3/4] Remote configurado:")
result = subprocess.run(["git", "remote", "-v"], capture_output=True, text=True)
print(result.stdout)

# Branch
print("[4/4] Branch atual:")
result = subprocess.run(["git", "branch"], capture_output=True, text=True)
print(result.stdout)

# Arquivos
print("\n" + "=" * 60)
print("ARQUIVOS DO PROJETO")
print("=" * 60)
for root, dirs, files in os.walk("."):
    if ".git" in root: continue
    for f in files:
        path = os.path.join(root, f).replace(".\\", "")
        print(f"  {path}")

print("\n" + "=" * 60)
print("TENTAR PUSH AGORA?")
print("=" * 60)
print("Execute no PowerShell:")
print('  cd "C:\\Users\\Thinkin pad 8g\\olho-de-deus-corrigido"')
print("  git push -u origin main --force")
print()
print("Ou acesse: https://github.com/Lelolima/Project-Eyes-of-God-2.9")