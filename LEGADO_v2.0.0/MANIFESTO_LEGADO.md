# 📜 PROJETO LEGADO - Olho de Deus v2.0.0

**Data da Movimentação:** 2026-07-04  
**Versão:** 2.0.0 (LEGADO)  
**Motivo:** Separação do projeto novo v3.0.1 para organização

---

## ⚠️ NÃO USAR ESTES ARQUIVOS PARA O PROJETO v3.0.1!

Os arquivos nesta pasta são do projeto **LEGADO v2.0.0** e **NÃO DEVEM** ser usados para o projeto novo v3.0.1.

Eles foram movidos para:
- ✅ Preservar o histórico do projeto original
- ✅ Permitir consulta de código antigo se necessário
- ✅ Manter scripts de deploy originais como referência

---

## 📁 ARQUIVOS CONTIDOS NESTA PASTA

### Código Principal (src/)
| Arquivo | Descrição |
|---------|-----------|
| `security_system.py` | Sistema original v2.0.0 (445 linhas) |

### Testes (tests/)
| Arquivo | Descrição |
|---------|-----------|
| `test_security_system.py` | Testes unitários originais (10 testes) |
| `validate_install.py` | Script de validação de instalação |

### Scripts (scripts/)
| Arquivo | Descrição |
|---------|-----------|
| `*.bat` (6 arquivos) | Scripts Windows de deploy/instalação |
| `deploy.py` | Script de deploy Python |
| `deploy-gitpython.py` | Deploy com GitPython |
| `fix-and-push.py` | Script de correção e push Git |
| `enviar-github.py` | Envio para GitHub |
| `check-repo.py` | Verificação de repositório |
| `upload-github-api.py` | Upload via API do GitHub |

### Assets (assets/)
| Arquivo | Descrição |
|---------|-----------|
| `interface-dashboard.svg` | Diagrama da interface |
| `fluxo-deteccao.svg` | Fluxo de detecção |
| `alerta-seguranca.svg` | Alerta de segurança |
| `arquitetura-sistema.svg` | Arquitetura do sistema |

### Configuração
| Arquivo | Descrição |
|---------|-----------|
| `requirements.txt` | Dependências pip antigas |
| `config.json` | Configuração antiga do sistema |

---

## 🆕 PROJETO NOVO v3.0.1

O projeto **NOVO v3.0.1** está na pasta **raiz** (um nível acima) e contém:

### Estrutura Moderna
```
../ (pasta raiz do projeto v3.0.1)
├── src/
│   ├── edge/           # Edge AI Processing
│   ├── cloud/          # Cloud Backend
│   ├── forensic/       # Forensic Logging
│   ├── privacy/        # Privacy by Design
│   ├── fairness/       # Fairness-Aware ML
│   └── hitl/           # HITL Dashboard
├── main.py             # Entry point novo
├── pyproject.toml      # Configuração Poetry
├── setup_secure_install.py
└── Documentação completa
```

### Diferenças Principais

| Característica | LEGADO v2.0.0 | NOVO v3.0.1 |
|----------------|---------------|-------------|
| **Processamento** | Centralizado | Edge-to-Cloud |
| **Privacidade** | Sem masking | Dynamic masking (blur) |
| **Cadeia de Custódia** | Hash simples | Merkle Tree + TSA |
| **HITL** | Sem revisão humana | Dashboard HITL completo |
| **Fairness** | Sem métricas | 4 métricas de viés |
| **LGPD** | Não conforme | Privacy by Design |
| **Autenticação** | Básica | JWT OAuth2 |
| **Persistência** | Arquivos | PostgreSQL |

---

## 📞 COMO VOLTAR AQUI

Se precisar consultar o código antigo:

1. Abra esta pasta: `LEGADO_v2.0.0`
2. Para rodar o sistema antigo (não recomendado):
   ```bash
   cd LEGADO_v2.0.0
   pip install -r requirements.txt
   python src/security_system.py
   ```

---

## 📝 NOTAS

- O código v2.0.0 foi **substituído** pelo v3.0.1
- Use **apenas** os arquivos da raiz para desenvolvimento
- Esta pasta é apenas para **referência histórica**

---

**Organizado em:** 2026-07-04  
**Responsável:** Claude Opus 4.8  
**Projeto Atual v3.0.1:** pasta raiz (`../`)