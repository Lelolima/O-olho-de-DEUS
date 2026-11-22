"""Carregador mínimo de arquivos ``.env`` (sem dependências).

Regras: linhas ``CHAVE=valor``; ``#`` inicia comentário de linha; aspas simples ou
duplas ao redor do valor são removidas; variáveis já definidas no ambiente **não**
são sobrescritas (o ambiente real tem prioridade).
"""

from __future__ import annotations

import os
import re
from pathlib import Path

_LINE = re.compile(r"^\s*(?:export\s+)?([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*)\s*$")


def parse_env(text: str) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw in text.splitlines():
        if not raw.strip() or raw.lstrip().startswith("#"):
            continue
        match = _LINE.match(raw)
        if not match:
            continue
        key, value = match.group(1), match.group(2).strip()
        if len(value) >= 2 and value[0] == value[-1] and value[0] in "\"'":
            value = value[1:-1]
        values[key] = value
    return values


def load_env_file(path: str | Path = ".env", override: bool = False) -> list[str]:
    """Carrega ``path`` em ``os.environ``; retorna as chaves aplicadas."""
    file = Path(path)
    if not file.is_file():
        return []
    applied = []
    for key, value in parse_env(file.read_text(encoding="utf-8")).items():
        if override or key not in os.environ:
            os.environ[key] = value
            applied.append(key)
    return applied
