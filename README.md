# Gestao Financeira Empresarial

Sistema de gestao financeira empresarial para pequenas e medias empresas que ainda controlam entradas, saidas, contas a pagar, contas a receber e relatorios em planilhas ou processos manuais.

O projeto deve permanecer enxuto no MVP: controle financeiro simples, importacao de planilhas, dashboard basico, trial gratuito e renovacao manual de assinatura. Nao e um ERP completo e nao deve virar CRM no MVP.

## Stack

- Backend: Python 3.12, FastAPI, SQLAlchemy 2.x, Pydantic v2, Alembic, JWT e bcrypt.
- Frontend: React, Vite, TypeScript, Tailwind CSS e TanStack Query.
- Banco de dados: PostgreSQL.
- Ambiente local: Docker Compose com servicos `backend`, `frontend` e `postgres`.

## Funcionalidades do MVP

- Cadastro self-service de empresa e primeiro usuario admin.
- Trial gratuito de 30 dias.
- Login com JWT.
- Bloqueio de funcionalidades financeiras quando a assinatura estiver vencida.
- Renovacao manual por usuario `platform_admin`.
- Categorias financeiras.
- Lancamentos financeiros de entrada e saida.
- Contas a pagar e contas a receber como visoes filtradas dos lancamentos.
- Dashboard simples do mes atual.
- Importacao CSV/XLSX de ate 5 MB.
- Historico de pagamentos manuais.

## Fora do MVP

Nao implementar sem autorizacao explicita:

- ERP completo;
- CRM;
- gateway de pagamento;
- Stripe, Mercado Pago, Pix automatizado, boleto ou cartao;
- nota fiscal;
- integracao bancaria ou conciliacao bancaria;
- folha de pagamento;
- estoque avancado;
- aplicativo mobile nativo;
- IA;
- WhatsApp ou e-mail automatico;
- relatorios avancados;
- exportacao PDF ou Excel formatado.

## Regras criticas

### Multiempresa

- Todo dado financeiro deve pertencer a uma empresa via `company_id`.
- Usuarios comuns nao devem enviar `company_id` como fonte de verdade.
- O backend deve obter `company_id` a partir do usuario autenticado.
- Listagens, detalhes, edicoes, exclusoes, relatorios, importacoes e exportacoes devem filtrar por `company_id`.
- Endpoints `platform_admin` sao a unica excecao controlada.

### Dinheiro

- Nunca usar `float` para valores monetarios.
- Usar `Decimal` no backend, schemas, services, importacao e calculos.
- Usar `NUMERIC` ou `DECIMAL`, preferencialmente `NUMERIC(14,2)`, no PostgreSQL.
- Preferir serializar dinheiro como string no JSON.

### Assinatura

Status usados no MVP:

- `trialing`: periodo gratuito ativo;
- `active`: assinatura paga ativa;
- `pending_payment`: trial ou assinatura vencida aguardando pagamento/liberacao;
- `canceled`: cancelamento manual;
- `blocked`: bloqueio administrativo futuro.

Nao usar status `expired` no MVP.

O usuario deve conseguir fazer login com assinatura vencida, mas rotas financeiras devem exigir assinatura valida.

### Datas financeiras

- `competence_date`: relatorios gerenciais.
- `due_date`: contas a pagar, contas a receber e fluxo previsto.
- `settled_at`: fluxo realizado e saldo atual.
- `created_at`: auditoria tecnica.

## Como rodar localmente

Requisitos:

- Docker;
- Docker Compose;
- Git.

Copie o arquivo de ambiente e preencha os valores obrigatorios antes de subir os containers.
Nao versionar `.env` real.

```bash
cp .env.example .env
```

Valores obrigatorios para ambiente local:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`

Suba os containers:

```bash
docker compose up --build
```

Aplique as migrations:

```bash
docker compose exec backend alembic upgrade head
```

Crie um usuario interno `platform_admin`:

```bash
docker compose exec backend python -m app.scripts.create_platform_admin --name "Nome Admin" --email admin@exemplo.com
```

O comando solicita a senha no terminal. Evite passar senha por argumento de linha de comando, porque isso pode ficar salvo no historico do shell.

Servicos locais:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health

## Comandos uteis

Rodar testes do backend:

```bash
docker compose exec backend pytest
```

Rodar migrations:

```bash
docker compose exec backend alembic upgrade head
```

Criar nova migration manualmente:

```bash
docker compose exec backend alembic revision -m "descricao_da_migration"
```

Build do frontend:

```bash
docker compose exec frontend npm run build
```

## Estrutura do projeto

```text
.
├── backend/
│   ├── alembic/
│   ├── app/
│   │   ├── api/
│   │   ├── core/
│   │   ├── db/
│   │   ├── models/
│   │   ├── schemas/
│   │   ├── scripts/
│   │   └── services/
│   └── tests/
├── frontend/
│   └── src/
│       ├── pages/
│       ├── api.ts
│       ├── App.tsx
│       └── types.ts
├── artifacts/
├── docker-compose.yml
├── PROJECT_CONTEXT.md
├── AGENTS.md
└── README.md
```

## Documentos importantes

- `PROJECT_CONTEXT.md`: fonte de verdade do produto, escopo do MVP, regras de negocio e ordem geral de implementacao.
- `AGENTS.md`: instrucoes obrigatorias para agentes de IA que trabalharem neste repositorio.

Antes de propor ou implementar mudancas relevantes, leia esses dois arquivos.

## Notas de seguranca

- Nunca versionar `.env` real, tokens, chaves privadas ou credenciais.
- Em producao, configurar `APP_DEBUG=false`, `JWT_SECRET_KEY` forte e `BACKEND_CORS_ORIGINS` somente com origens confiaveis.
- O frontend armazena o JWT em `localStorage` no MVP. Isso simplifica o fluxo inicial, mas aumenta impacto em caso de XSS; antes de uso amplo em producao, revisar CSP, sanitizacao de UI e considerar cookies `HttpOnly` com protecao CSRF.

## Status atual

O projeto ja possui uma base funcional com backend FastAPI, frontend React/Vite, PostgreSQL via Docker Compose, migrations Alembic, autenticacao, trial, bloqueio por assinatura, administracao de renovacao manual, categorias, lancamentos, contas a pagar/receber, dashboard e importacao.

Ainda existem pontos de alinhamento com o escopo documentado, especialmente exportacao CSV, saldo inicial, soft delete e revisao do modulo de contatos.
