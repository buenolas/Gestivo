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

## Deploy de demonstracao na Vercel

O deploy usa dois projetos Vercel criados para o mesmo repositorio:

- `gestao-financeira-api`, com Root Directory `backend`;
- `gestao-financeira-web`, com Root Directory `frontend`;
- PostgreSQL Neon persistente, conectado ao projeto da API;
- Brevo API para os e-mails de verificacao.

Este desenho evita depender do recurso Vercel Services. O ambiente gratuito e destinado
somente a demonstracao e testes, sem clientes pagantes ou dados financeiros reais.

Ambiente de demonstracao publicado em 11 de junho de 2026:

- Frontend: https://gestao-financeira-web-bubas-software.vercel.app
- API: https://gestao-financeira-api-six.vercel.app
- Health check: https://gestao-financeira-api-six.vercel.app/health

Os deploys iniciais foram feitos pela Vercel CLI. Para habilitar deploy automatico por
push e variaveis Preview para todas as branches, conecte a conta GitHub nas configuracoes
da conta Vercel e depois conecte os dois projetos ao repositorio.

O SSO Deployment Protection do projeto web deve permanecer desativado para que a
demonstracao seja acessivel publicamente. O segredo atual do cron e a senha inicial do
`platform_admin` ficam apenas em `secrets/cron_secret.txt` e
`secrets/platform_admin_password.txt`, ambos ignorados pelo Git.

### 1. Criar os projetos

Importe o repositorio `buenolas/gestao-financeira` duas vezes na Vercel.

No projeto da API:

- defina Root Directory como `backend`;
- mantenha o framework FastAPI detectado pela Vercel;
- use `backend/vercel.json`.

No projeto web:

- defina Root Directory como `frontend`;
- mantenha o framework Vite detectado pela Vercel;
- use `frontend/vercel.json`.

Publique primeiro a API. A URL final dela sera usada no build do frontend.

### 2. Provisionar o Neon

No Marketplace da Vercel, instale Neon no projeto `gestao-financeira-api`.
Crie um banco para demonstracao e copie duas strings de conexao:

- `DATABASE_URL`: conexao pooled, com `-pooler` no hostname;
- `MIGRATION_DATABASE_URL`: conexao direta, sem `-pooler`.

O runtime FastAPI usa `DATABASE_URL`. Alembic usa `MIGRATION_DATABASE_URL`, com fallback
para `DATABASE_URL` apenas no ambiente local.

### 3. Variaveis da API

Configure em Production e Preview:

```text
APP_NAME=Gestao Financeira Empresarial
APP_ENV=production
APP_DEBUG=false
DATABASE_URL=<neon-pooled-url-com-driver-postgresql+psycopg>
MIGRATION_DATABASE_URL=<neon-direct-url-com-driver-postgresql+psycopg>
JWT_SECRET_KEY=<segredo-aleatorio-com-ao-menos-32-caracteres>
CRON_SECRET=<outro-segredo-aleatorio-com-ao-menos-32-caracteres>
JWT_ALGORITHM=HS256
ACCESS_TOKEN_EXPIRE_MINUTES=60
BACKEND_CORS_ORIGINS=<url-publica-do-frontend>
FRONTEND_URL=<url-publica-do-frontend>
EMAIL_DELIVERY_MODE=brevo_api
EMAIL_FROM=<remetente-validado-na-brevo>
EMAIL_FROM_NAME=Gestao Financeira Empresarial
EMAIL_VERIFICATION_TOKEN_EXPIRE_MINUTES=60
BREVO_API_KEY=<chave-da-brevo>
BREVO_API_URL=https://api.brevo.com/v3/smtp/email
GOOGLE_CLIENT_ID=<oauth-web-client-id-do-google>
```

Se o Neon fornecer uma URL iniciada por `postgresql://`, troque apenas o esquema para
`postgresql+psycopg://`. Preserve os demais parametros, incluindo `sslmode=require`.

Use o mesmo OAuth Web Client ID em `GOOGLE_CLIENT_ID` e `VITE_GOOGLE_CLIENT_ID`.
No Google Cloud Console, o cliente OAuth deve ser do tipo Aplicativo da Web e deve
incluir `https://gestao-financeira-web-bubas-software.vercel.app` em Origens JavaScript
autorizadas. O fluxo usa Google Identity Services com ID token, portanto nao precisa de
URI de redirecionamento para o endpoint `/auth/google`.

### 4. Migrations e administrador

Execute a partir de uma maquina confiavel, sem registrar os segredos no Git:

```bash
cd backend
alembic upgrade head
python -m app.scripts.create_platform_admin \
  --name "Lucas Almeida Bueno" \
  --email "lucasdealmeidabueno@gmail.com"
```

O segundo comando solicita a senha no terminal. Nao use `--password` em historicos de
shell ou pipelines.

### 5. Variaveis do frontend

Configure em Production e Preview:

```text
VITE_API_URL=<url-publica-da-api-sem-barra-final>
VITE_GOOGLE_CLIENT_ID=<mesmo-oauth-web-client-id-do-google>
```

Depois de obter a URL definitiva do frontend, atualize `BACKEND_CORS_ORIGINS` e
`FRONTEND_URL` na API e faca um novo deploy da API.

### 6. Cron de assinaturas

`backend/vercel.json` chama diariamente:

```text
GET /internal/cron/expire-subscriptions
```

A Vercel envia `Authorization: Bearer <CRON_SECRET>`. Chamadas sem o segredo retornam
`401`. O endpoint apenas atualiza trials e assinaturas vencidas para `pending_payment`.

### 7. Checklist de publicacao

1. Execute `pytest` em `backend`.
2. Execute `npm test` e `npm run build` em `frontend`.
3. Execute `alembic upgrade head` usando a URL direta do Neon.
4. Publique a API e confirme `GET /health`.
5. Publique o frontend com `VITE_API_URL` apontando para a API.
6. Confirme cadastro, e-mail, onboarding, login, lancamentos, dashboard, importacao e exportacao.
7. Confirme isolamento entre empresas, bloqueio por assinatura e renovacao pelo admin.
8. Revise os Runtime Logs da Vercel para erros e vazamento de dados sensiveis.

### Rollback

Para codigo, use Instant Rollback no projeto afetado pela Vercel. Para alteracoes de
schema, nao execute downgrade automatico: restaure o deploy anterior, corrija a migration
de forma aditiva e aplique uma nova revisao Alembic.

Antes de uso comercial, migre os dois projetos para Vercel Pro, configure retencao/PITR
adequada no Neon e reavalie a hospedagem do backend Python.
