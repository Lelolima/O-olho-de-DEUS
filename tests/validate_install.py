#!/usr/bin/env python3
"""
Script de validação de instalação
Verifica se todas as dependências e configurações estão corretas
"""

import sys
import json
from pathlib import Path


def print_header(text):
    print("\n" + "=" * 60)
    print(f"  {text}")
    print("=" * 60)


def check_python_version():
    """Verifica versão do Python"""
    print_header("Versão do Python")
    version = sys.version_info
    print(f"Python {version.major}.{version.minor}.{version.micro}")

    if version.major < 3 or (version.major == 3 and version.minor < 9):
        print("❌ Python 3.9+ necessário")
        return False
    print("✅ Versão OK")
    return True


def check_dependencies():
    """Verifica dependências instaladas"""
    print_header("Dependências")

    deps = {
        'cv2': 'opencv-python',
        'numpy': 'numpy',
        'tensorflow': 'tensorflow',
        'requests': 'requests'
    }

    all_ok = True
    for module, package in deps.items():
        try:
            mod = __import__(module)
            version = getattr(mod, '__version__', 'desconhecida')
            print(f"✅ {package}: {version}")
        except ImportError:
            print(f"❌ {package}: NÃO INSTALADO")
            all_ok = False

    return all_ok


def check_config():
    """Verifica arquivo de configuração"""
    print_header("Configuração")

    config_path = Path('config.json')
    if not config_path.exists():
        print("❌ config.json não encontrado")
        return False

    try:
        with open(config_path, 'r') as f:
            config = json.load(f)

        required_keys = ['security_level', 'video_sources', 'log_level']
        for key in required_keys:
            if key not in config:
                print(f"❌ Chave '{key}' faltando em config.json")
                return False

        print(f"✅ Configuração válida")
        print(f"   Fontes de vídeo: {len(config['video_sources'])}")
        print(f"   Nível de segurança: {config['security_level']}")
        print(f"   Level de log: {config['log_level']}")
        return True

    except json.JSONDecodeError as e:
        print(f"❌ JSON inválido: {e}")
        return False


def check_directories():
    """Verifica diretórios necessários"""
    print_header("Diretórios")

    dirs = ['incidents', 'logs', 'models']
    all_ok = True

    for d in dirs:
        path = Path(d)
        if path.exists():
            print(f"✅ {d}/ existe")
        else:
            print(f"⚠️  {d}/ não existe (será criado na execução)")

    return all_ok


def check_source_code():
    """Verifica código fonte"""
    print_header("Código Fonte")

    src_path = Path('src/security_system.py')
    if not src_path.exists():
        print("❌ src/security_system.py não encontrado")
        return False

    # Verificar imports
    with open(src_path, 'r', encoding='utf-8') as f:
        content = f.read()

    required_imports = ['import cv2', 'import numpy', 'import tensorflow', 'import requests']
    for imp in required_imports:
        if imp not in content:
            print(f"❌ Import faltando: {imp}")
            return False

    print("✅ Código fonte válido")
    print("✅ Todos os imports presentes")
    return True


def run_syntax_check():
    """Verifica sintaxe Python"""
    print_header("Sintaxe Python")

    src_path = Path('src/security_system.py')
    try:
        with open(src_path, 'r', encoding='utf-8') as f:
            compile(f.read(), src_path, 'exec')
        print("✅ Sintaxe válida")
        return True
    except SyntaxError as e:
        print(f"❌ Erro de sintaxe: {e}")
        return False


def main():
    print("\n" + "🔍" * 30)
    print("  VALIDAÇÃO DE INSTALAÇÃO - O-olho-de-DEUS")
    print("🔍" * 30)

    results = []
    results.append(("Python", check_python_version()))
    results.append(("Dependências", check_dependencies()))
    results.append(("Configuração", check_config()))
    results.append(("Diretórios", check_directories()))
    results.append(("Código Fonte", check_source_code()))
    results.append(("Sintaxe", run_syntax_check()))

    print_header("Resultado Final")

    passed = sum(1 for _, r in results if r)
    total = len(results)

    for name, result in results:
        status = "✅" if result else "❌"
        print(f"{status} {name}")

    print(f"\n{passed}/{total} verificações passaram")

    if passed == total:
        print("\n🎉 Sistema pronto para execução!")
        print("\nPara iniciar: python src/security_system.py")
        return 0
    else:
        print("\n⚠️  Corrija os erros acima antes de executar")
        return 1


if __name__ == "__main__":
    sys.exit(main())