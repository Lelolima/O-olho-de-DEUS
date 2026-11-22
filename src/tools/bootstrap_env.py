"""Gera um ``.env`` local com segredos novos e o primeiro operador.

Uso:
    python -m src.tools.bootstrap_env --operator admin --role admin
    python -m src.tools.bootstrap_env --operator op1 --password-stdin < senha.txt

A senha é lida com ``getpass`` (não aparece no terminal nem no histórico) e só o
hash PBKDF2 é gravado em ``OPERATOR_USERS``. Os valores gerados nunca são impressos.
"""

from __future__ import annotations

import argparse
import getpass
import json
import logging
import os
import secrets
import sys
from pathlib import Path

from cryptography.fernet import Fernet

# Importar o módulo de auth dispara avisos de servidor (JWT/operadores ausentes)
# que não se aplicam a esta ferramenta: silencia-os só durante o import.
logging.disable(logging.WARNING)
try:
    from src.cloud.api.middleware.auth import hash_password
finally:
    logging.disable(logging.NOTSET)

MIN_PASSWORD_LENGTH = 12
VALID_ROLES = ("operator", "supervisor", "admin")


def build_env(operator: str, role: str, password: str) -> str:
    if len(password) < MIN_PASSWORD_LENGTH:
        raise ValueError(f"A senha precisa ter ao menos {MIN_PASSWORD_LENGTH} caracteres")
    if role not in VALID_ROLES:
        raise ValueError(f"Papel inválido: {role} (use {', '.join(VALID_ROLES)})")
    users = {operator: {"role": role, "password_hash": hash_password(password)}}
    lines = [
        "# Gerado por python -m src.tools.bootstrap_env. NÃO versionar este arquivo.",
        f"JWT_SECRET={secrets.token_hex(32)}",
        f"ENCRYPTION_KEY={Fernet.generate_key().decode()}",
        f"OPERATOR_USERS={json.dumps(users, separators=(',', ':'))}",
        "DATABASE_URL=",
        "TSA_ENABLED=false",
        "API_HOST=127.0.0.1",
        "API_PORT=8000",
        "CORS_ORIGINS=http://localhost:3000",
        "LOG_LEVEL=INFO",
        "",
    ]
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Gera .env com segredos e o primeiro operador")
    parser.add_argument("--operator", required=True, help="nome de usuário do operador")
    parser.add_argument("--role", default="operator", choices=VALID_ROLES)
    parser.add_argument("--output", default=".env", help="arquivo de saída (padrão: .env)")
    parser.add_argument("--force", action="store_true", help="sobrescreve o arquivo se existir")
    parser.add_argument("--password-stdin", action="store_true", help="lê a senha da entrada padrão")
    args = parser.parse_args(argv)

    out = Path(args.output)
    if out.exists() and not args.force:
        print(f"{out} já existe; use --force para sobrescrever", file=sys.stderr)
        return 1

    if args.password_stdin:
        password = sys.stdin.readline().rstrip("\r\n")
    else:
        password = getpass.getpass("Senha do operador: ")
        if getpass.getpass("Confirme a senha: ") != password:
            print("As senhas não conferem", file=sys.stderr)
            return 1

    try:
        content = build_env(args.operator, args.role, password)
    except ValueError as exc:
        print(str(exc), file=sys.stderr)
        return 1

    out.write_text(content, encoding="utf-8")
    if os.name != "nt":
        out.chmod(0o600)
    print(f"{out} gerado com o operador '{args.operator}' ({args.role}). Segredos não exibidos.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
