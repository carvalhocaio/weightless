# Weightless

API FastAPI para listar repositórios do GitHub de um usuário.

## Descrição

Este projeto expõe uma API construída com [FastAPI](https://fastapi.tiangolo.com/) que retorna os
repositórios mais recentes de um usuário do GitHub, incluindo as linguagens utilizadas em cada
repositório.

## Funcionalidades

- Endpoint de saúde (`/`)
- Listagem dos repositórios mais recentes do GitHub (`/github/repos/{username}`)
- Suporte a CORS
- Deploy pronto para [Vercel](https://vercel.com/)

## Instalação

1. Clone o repositório.
2. Instale as dependências:

   ```sh
   pip install -r requirements.txt
   ```

3. Crie um arquivo `.env` na raiz do projeto e adicione sua chave do GitHub:

   ```
   GITHUB_TOKEN=seu_token_github
   ```

## Uso

Para rodar localmente:

```sh
make run
```

Acesse [http://localhost:8000](http://localhost:8000).

## Endpoints

- `GET /`  
  Retorna mensagem de status.

- `GET /github/repos/{username}`  
  Retorna até 3 repositórios mais recentes do usuário informado, com as linguagens utilizadas.

- `GET /docs`
  Retorna a documentação da API.

## Deploy

O projeto está configurado para deploy automático na Vercel, utilizando o arquivo [`vercel.json`](vercel.json).

## Ferramentas de Desenvolvimento

- [FastAPI](https://fastapi.tiangolo.com/)
- [Uvicorn](https://www.uvicorn.org/)
- [httpx](https://www.python-httpx.org/)
- [python-decouple](https://github.com/henriquebastos/python-decouple)
- [ruff](https://github.com/astral-sh/ruff) (lint e formatador)

---

Feito por [carvalhocaio](https://github.com/carvalhocaio)