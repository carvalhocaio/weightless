# Weightless

[![Tests](https://github.com/carvalhocaio/weightless/actions/workflows/tests.yml/badge.svg)](https://github.com/carvalhocaio/weightless/actions/workflows/tests.yml)
[![Python 3.11+](https://img.shields.io/badge/python-3.11%2B-blue.svg)](https://www.python.org/downloads/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.104%2B-009688.svg?style=flat&logo=FastAPI&logoColor=white)](https://fastapi.tiangolo.com)
[![Code style: Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)

API FastAPI para listar repositórios do GitHub de um usuário com caching, validação robusta e 
monitoramento avançado.

## 📋 Descrição

**Weightless** é uma API moderna construída com [FastAPI](https://fastapi.tiangolo.com/) que 
fornece acesso otimizado aos repositórios mais recentes de usuários do GitHub. A API inclui sistema 
de cache inteligente, validação de entrada robusta, logging estruturado, tratamento de erros 
abrangente e suporte a monitoramento em produção.

### 🎯 Características Principais

- **Cache Inteligente**: Sistema de cache em memória para repositórios e linguagens
- **Logging Estruturado**: Logs detalhados com correlation IDs para rastreamento de requisições
- **Validação Robusta**: Validação completa de usernames do GitHub usando Pydantic
- **Tratamento de Erros**: Tratamento abrangente de erros com códigos de status apropriados
- **Monitoramento**: Integração opcional com Sentry para monitoramento de erros
- **Documentação Automática**: Interface Swagger UI integrada
- **CORS Configurável**: Suporte a CORS com configuração flexível
- **Testes Abrangentes**: Suite de testes com cobertura de 90%+
- **CI/CD**: Pipeline automatizado com GitHub Actions

## 🚀 Funcionalidades

### Endpoints Disponíveis

- **`GET /`** - Informações da API e links para documentação
- **`GET /health`** - Endpoint de health check para monitoramento
- **`GET /github/repos/{username}`** - Repositórios mais recentes do usuário com linguagens
- **`GET /docs`** - Documentação interativa (Swagger UI)
- **`GET /redoc`** - Documentação alternativa (ReDoc)

### Recursos Avançados

- ⚡ **Cache com TTL configurável** para otimização de performance
- 🔒 **Validação de entrada** com mensagens de erro detalhadas  
- 📊 **Logging estruturado** com contexto de requisições
- 🛡️ **Rate limiting** e tratamento de limites da API do GitHub
- 🔄 **Retry automático** com backoff exponencial
- 📈 **Monitoramento de erros** com Sentry (opcional)
- 🌐 **CORS configurável** para integração frontend
- 🏥 **Health checks** para containers e load balancers

## 📦 Instalação

### Pré-requisitos

- Python 3.11 ou superior
- Token de acesso pessoal do GitHub ([criar aqui](https://github.com/settings/tokens))

### Passos de Instalação

1. **Clone o repositório**:
   ```bash
   git clone https://github.com/carvalhocaio/weightless.git
   cd weightless
   ```

2. **Crie um ambiente virtual**:
   ```bash
   python -m venv .venv
   source .venv/bin/activate  # Linux/macOS
   # ou
   .venv\Scripts\activate     # Windows
   ```

3. **Instale as dependências**:
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure as variáveis de ambiente**:
   ```bash
   cp .env.example .env  # Se disponível
   # ou crie manualmente:
   echo "GITHUB_TOKEN=seu_token_aqui" > .env
   ```

## ⚙️ Configuração

A aplicação suporta configuração através de variáveis de ambiente ou arquivo `.env`:

### Variáveis Obrigatórias

```bash
GITHUB_TOKEN=ghp_xxxxxxxxxxxxxxxxxxxx  # Token de acesso do GitHub
```

### Variáveis Opcionais

```bash
# CORS
CORS_ORIGINS=http://localhost:3000,http://127.0.0.1:3000

# Cache (em segundos)
CACHE_TTL_REPOS=300      # Cache de repositórios (5 min)
CACHE_TTL_LANGUAGES=600  # Cache de linguagens (10 min)

# API
API_TIMEOUT=30.0         # Timeout de requisições (segundos)
MAX_RETRIES=3            # Máximo de tentativas

# Aplicação
APP_NAME=Weightless API
APP_VERSION=1.0.0
DEBUG=false

# Logging
LOG_LEVEL=INFO

# Monitoramento (opcional)
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx
```

## 🏃‍♂️ Uso

### Executar Localmente

```bash
# Usando o Makefile
make run

# Ou diretamente
uvicorn api.main:app --reload
```

A API estará disponível em [http://localhost:8000](http://localhost:8000).

### Exemplos de Uso

#### 1. Informações da API
```bash
curl http://localhost:8000/
```

**Resposta**:
```json
{
  "message": "Welcome to Weightless API",
  "docs": "http://localhost:8000/docs",
  "version": "1.0.0"
}
```

#### 2. Health Check
```bash
curl http://localhost:8000/health
```

**Resposta**:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

#### 3. Repositórios do Usuário
```bash
curl http://localhost:8000/github/repos/octocat
```

**Resposta**:
```json
[
  {
    "name": "Hello-World",
    "full_name": "octocat/Hello-World",
    "description": "This your first repo!",
    "html_url": "https://github.com/octocat/Hello-World",
    "languages": {"C": 78.1, "Makefile": 21.9},
    "created_at": "2011-01-26T19:01:12Z",
    "updated_at": "2011-01-26T19:14:43Z",
    "pushed_at": "2011-01-26T19:06:43Z",
    "stargazers_count": 80,
    "watchers_count": 9,
    "language": "C",
    "forks_count": 9,
    "archived": false,
    "disabled": false
  }
]
```

### Códigos de Status HTTP

| Código | Descrição |
|--------|-----------|
| `200` | Sucesso |
| `404` | Usuário não encontrado |
| `422` | Formato de username inválido |
| `429` | Limite de rate exceeded |
| `500` | Erro interno do servidor |
| `502` | Erro da API do GitHub |
| `504` | Timeout da requisição |

## 🛠️ Desenvolvimento

### Comandos Disponíveis

```bash
# Executar aplicação
make run

# Linting
make lint

# Formatação de código  
make format

# Testes
pytest

# Testes com cobertura
pytest --cov=api --cov-report=html

# Testes específicos
pytest tests/test_github_service.py -v
```

### Estrutura do Projeto

```
weightless/
├── api/                        # Código principal da aplicação
│   ├── config/                 # Configurações e logging
│   │   ├── logging.py          # Setup de logging estruturado
│   │   └── settings.py         # Configurações da aplicação
│   ├── models/                 # Modelos Pydantic
│   │   └── repository.py       # Modelos de dados
│   ├── services/               # Lógica de negócio
│   │   └── github.py           # Serviço do GitHub com cache
│   └── main.py                 # Aplicação FastAPI principal
├── tests/                      # Testes automatizados
│   ├── conftest.py             # Fixtures compartilhadas
│   ├── test_main.py            # Testes dos endpoints
│   ├── test_github_service.py  # Testes do serviço
│   └── test_models.py          # Testes dos modelos
├── .github/workflows/          # CI/CD GitHub Actions
├── requirements.txt            # Dependências Python
├── pytest.ini                  # Configuração de testes
├── ruff.toml                   # Configuração do linter
└── Makefile                    # Comandos de desenvolvimento
```

### Ferramentas de Qualidade

- **[Ruff](https://github.com/astral-sh/ruff)**: Linting e formatação ultrarrápidos
- **[pytest](https://pytest.org/)**: Framework de testes com fixtures avançadas
- **[pytest-cov](https://pytest-cov.readthedocs.io/)**: Cobertura de código (meta: 90%+)
- **[pytest-asyncio](https://pytest-asyncio.readthedocs.io/)**: Suporte a testes assíncronos

### Pipeline CI/CD

O projeto utiliza GitHub Actions para:

- ✅ Testes automatizados em Python 3.11 e 3.12
- 📊 Relatórios de cobertura via Codecov
- 🔍 Análise estática de código com Ruff
- 🚀 Execução em múltiplas versões do Python

## 🚢 Deployment

### Docker (Recomendado)

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["uvicorn", "api.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

### Variáveis de Ambiente para Produção

```bash
# Essenciais
GITHUB_TOKEN=ghp_production_token
LOG_LEVEL=INFO

# Performance
CACHE_TTL_REPOS=600
CACHE_TTL_LANGUAGES=900
API_TIMEOUT=45.0

# Monitoramento
SENTRY_DSN=https://xxxxx@sentry.io/xxxxx

# CORS (ajuste para seu domínio)
CORS_ORIGINS=https://meuapp.com,https://www.meuapp.com
```

### Health Check para Load Balancers

```bash
curl -f http://localhost:8000/health || exit 1
```

## 🔧 Troubleshooting

### Problemas Comuns

**❌ Erro 401: Bad credentials**
- Verifique se `GITHUB_TOKEN` está configurado corretamente
- Confirme se o token tem permissões adequadas

**❌ Erro 403: Rate limit exceeded**
- Aguarde o reset do rate limit (exibido nos headers)
- Considere usar um token com limite mais alto

**❌ Erro 422: Invalid username format**
- Username deve ter 1-39 caracteres
- Apenas letras, números e hífens (não no início/fim)

**❌ Timeout errors**
- Aumente `API_TIMEOUT` nas configurações
- Verifique conectividade com api.github.com

### Logs e Debugging

```bash
# Habilitar logs detalhados
export LOG_LEVEL=DEBUG

# Verificar logs estruturados
tail -f app.log | jq .

# Monitorar cache hits/misses
grep "Cache" app.log
```

## 🤝 Contribuindo

1. Fork o projeto
2. Crie uma branch para sua feature (`git checkout -b feature/nova-feature`)
3. Commit suas mudanças (`git commit -am 'Add: nova feature'`)
4. Push para a branch (`git push origin feature/nova-feature`)
5. Abra um Pull Request

### Padrões de Commit

- `feat:` Nova funcionalidade
- `fix:` Correção de bug
- `docs:` Documentação
- `style:` Formatação (sem mudança de lógica)
- `refactor:` Refatoração de código
- `test:` Testes
- `chore:` Manutenção


## 🛠️ Stack Tecnológica

- **[FastAPI](https://fastapi.tiangolo.com/)** - Framework web moderno e rápido
- **[Uvicorn](https://www.uvicorn.org/)** - Servidor ASGI de alta performance
- **[httpx](https://www.python-httpx.org/)** - Cliente HTTP assíncrono
- **[Pydantic](https://docs.pydantic.dev/)** - Validação de dados e settings
- **[structlog](https://www.structlog.org/)** - Logging estruturado
- **[Sentry](https://sentry.io/)** - Monitoramento de erros (opcional)

---

**Desenvolvido por [carvalhocaio](https://github.com/carvalhocaio)**

> 💡 **Dica**: Visite `/docs` para interagir com a API através da interface Swagger!