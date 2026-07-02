#!/usr/bin/env python3
"""
Upload direto via GitHub API - sem git command line
"""
import base64
import os
import sys

# Configurações
REPO_OWNER = "Lelolima"
REPO_NAME = "Project-Eyes-of-God-2.9"
BRANCH = "main"
LOCAL_PATH = r"C:\Users\Thinkin pad 8g\olho-de-deus-corrigido"

# Arquivos para upload (relativos ao LOCAL_PATH)
FILES_TO_UPLOAD = [
    "README.md",
    ".gitignore",
    "config.json",
    "requirements.txt",
    "instalar.bat",
    "validar.bat",
    "commit-push.bat",
    "src/__init__.py",
    "src/security_system.py",
    "tests/test_security_system.py",
    "tests/validate_install.py",
    "assets/interface-dashboard.svg",
    "assets/fluxo-deteccao.svg",
    "assets/alerta-seguranca.svg",
    "assets/arquitetura-sistema.svg",
]

def get_token():
    """Pede token ao usuário"""
    print("=" * 60)
    print("GITHUB TOKEN NECESSARIO")
    print("=" * 60)
    print()
    print("1. Acesse: https://github.com/settings/tokens")
    print("2. Generate new token (classic)")
    print("3. Marque: repo, workflow, delete_repo")
    print("4. Copie o token gerado")
    print()
    return input("Cole seu token aqui: ").strip()

def api_request(token, method, path, data=None):
    """Faz requisição à API do GitHub"""
    import urllib.request
    import json

    url = f"https://api.github.com/{path}"
    headers = {
        "Authorization": f"token {token}",
        "Accept": "application/vnd.github.v3+json",
    }
    if data:
        headers["Content-Type"] = "application/json"
        req = urllib.request.Request(url, data=json.dumps(data).encode(), headers=headers, method=method)
    else:
        req = urllib.request.Request(url, headers=headers, method=method)

    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as e:
        error_body = e.read().decode()
        print(f"HTTP {e.code}: {error_body}")
        return None
    except Exception as e:
        print(f"Erro: {e}")
        return None

def get_file_sha(token, file_path):
    """Pega o SHA de um arquivo existente"""
    result = api_request(token, "GET", f"repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}?ref={BRANCH}")
    return result.get("sha") if result else None

def upload_file(token, file_path, content, message, sha=None):
    """Upload de um arquivo"""
    data = {
        "message": message,
        "content": content,
        "branch": BRANCH,
    }
    if sha:
        data["sha"] = sha

    result = api_request(token, "PUT", f"repos/{REPO_OWNER}/{REPO_NAME}/contents/{file_path}", data)
    return result

def main():
    token = get_token()
    if not token:
        print("Token não fornecido")
        return 1

    print("\n" + "=" * 60)
    print("INICIANDO UPLOAD")
    print("=" * 60)

    commit_count = 0
    for file_path in FILES_TO_UPLOAD:
        local_file = os.path.join(LOCAL_PATH, file_path)

        if not os.path.exists(local_file):
            print(f"⚠️  Arquivo local não existe: {file_path}")
            continue

        # Ler conteúdo e converter para base64
        with open(local_file, "rb") as f:
            content_bytes = f.read()
        content_b64 = base64.b64encode(content_bytes).decode("utf-8")

        # Tentar upload
        print(f"Enviando: {file_path}...", end=" ")

        # Tentar get SHA se já existe
        sha = get_file_sha(token, file_path)

        result = upload_file(
            token,
            file_path,
            content_b64,
            f"Update {file_path} - Lelolima",
            sha
        )

        if result:
            print("✅ OK")
            commit_count += 1
        else:
            print("❌ Falhou")

    print()
    print("=" * 60)
    print(f"UPLOAD CONCLUÍDO: {commit_count}/{len(FILES_TO_UPLOAD)} arquivos")
    print(f"Repositório: https://github.com/{REPO_OWNER}/{REPO_NAME}")
    print("=" * 60)
    return 0

if __name__ == "__main__":
    sys.exit(main())