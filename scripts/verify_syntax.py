"""
Script de verificação de sintaxe Python.

Uso: python verify_syntax.py
"""

import py_compile
import sys
from pathlib import Path

# Arquivos para verificar
files_to_check = [
    "src/cloud/database.py",
    "src/cloud/init_db.py",
    "src/cloud/api/routes/alerts.py",
    "src/cloud/api/routes/evidence.py",
    "src/hitl/dashboard_server.py",
]

def main():
    """Verifica sintaxe de todos os arquivos."""
    print("=" * 50)
    print("VERIFICAÇÃO DE SINTAXE PYTHON")
    print("=" * 50)
    print()

    errors = []
    base_path = Path(__file__).parent

    for file in files_to_check:
        file_path = base_path / file
        if not file_path.exists():
            print(f"⚠️  {file} - Não encontrado")
            continue

        try:
            py_compile.compile(str(file_path), doraise=True)
            print(f"✅ {file} - OK")
        except py_compile.PyCompileError as e:
            print(f"❌ {file} - ERRO: {e}")
            errors.append((file, str(e)))

    print()
    print("=" * 50)

    if errors:
        print(f"❌ {len(errors)} erro(s) encontrado(s)")
        return 1
    else:
        print(f"✅ Todos os {len(files_to_check)} arquivos válidos!")
        return 0

if __name__ == "__main__":
    sys.exit(main())