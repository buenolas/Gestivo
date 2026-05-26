# Project Context - Sistema de Gestao Financeira Empresarial

## 1. Visao Geral

Este projeto e um sistema de gestao financeira empresarial para pequenas e medias empresas que ainda controlam o financeiro por planilhas, anotacoes manuais ou processos pouco padronizados.

O produto nao deve comecar como ERP completo nem como CRM. O nucleo inicial e controle financeiro simples, confiavel e orientado a fluxo de caixa.

## 2. Problema Resolvido

Muitas empresas pequenas nao conseguem enxergar com clareza:

- quanto entrou;
- quanto saiu;
- quais contas estao vencendo;
- quais recebimentos estao atrasados;
- qual e o saldo atual;
- se o caixa pode ficar negativo;
- quais despesas pesam mais no resultado.

O sistema deve transformar dados financeiros desorganizados em uma visao clara, segura e mais automatizada do dinheiro da empresa.

## 3. Publico-Alvo

O publico inicial sao pequenas empresas, prestadores de servico e negocios locais que ja possuem algum controle financeiro, mas ainda dependem de planilhas ou controle manual.

Perfis esperados:

- pequenas lojas;
- clinicas;
- escritorios;
- prestadores de servico;
- restaurantes ou lanchonetes em fase inicial;
- negocios familiares;
- empresas que usam Excel ou Google Sheets para controlar entradas e saidas.

O MVP deve evitar nichos que exijam complexidade fiscal, estoque avancado ou emissao de nota fiscal.

## 4. Escopo do MVP

O MVP deve permitir que uma empresa:

- crie uma conta self-service;
- crie automaticamente sua empresa;
- receba trial gratuito de 30 dias;
- acesse funcionalidades financeiras enquanto a assinatura estiver valida;
- cadastre categorias financeiras;
- cadastre lancamentos financeiros;
- controle entradas e saidas;
- veja contas a pagar e contas a receber como visoes filtradas dos lancamentos;
- veja dashboard simples do mes atual;
- veja saldo atual com base em saldo inicial e lancamentos liquidados;
- importe planilhas CSV/XLSX de ate 5 MB;
- exporte lancamentos em CSV;
- seja bloqueada nas rotas financeiras quando o trial ou assinatura vencer;
- seja reativada manualmente por um platform admin apos pagamento confirmado fora da plataforma.

## 5. Funcionalidades Fora do MVP

Nao implementar no MVP:

- ERP completo;
- CRM;
- modulo de contatos/clientes/fornecedores;
- emissao de nota fiscal;
- integracao bancaria;
- conciliacao bancaria;
- gateway de pagamento;
- Stripe;
- Mercado Pago;
- Pix automatizado;
- boleto;
- cartao de credito;
- webhook de pagamento;
- folha de pagamento;
- estoque avancado;
- integracao com contabilidade;
- aplicativo mobile nativo;
- IA;
- WhatsApp automatico;
- e-mail automatico;
- recorrencia avancada;
- permissoes complexas;
- relatorios avancados;
- exportacao PDF;
- exportacao Excel formatada.

Qualquer expansao de escopo precisa de autorizacao explicita.

## 6. Diferencial: Importacao de Planilhas

O principal diferencial estrategico do MVP e ajudar empresas que ja possuem dados financeiros em planilhas a migrar para um sistema organizado.

Importacao no MVP:

- aceitar CSV e XLSX;
- limitar arquivos a 5 MB;
- seguir o fluxo: upload, preview, mapeamento, validacao, confirmacao e criacao dos lancamentos;
- criar apenas financial_transactions;
- nao criar contatos;
- nao criar categorias automaticamente;
- vincular categoria apenas se ela ja existir para a empresa;
- mapear cliente, fornecedor ou contato da planilha para `counterparty_name`;
- validar valores monetarios com Decimal;
- respeitar sempre o `company_id` da empresa autenticada.

Nao incluir IA, conciliacao, categorizacao automatica ou deteccao avancada de duplicidade no MVP.

## 7. Stack Tecnica Definida

Backend:

- Python 3.12;
- FastAPI;
- Pydantic v2;
- SQLAlchemy 2.x;
- Alembic;
- bcrypt para hash de senha;
- JWT para autenticacao.

Frontend:

- React;
- Vite;
- TypeScript;
- Tailwind CSS;
- TanStack Query;
- React Hook Form;
- Zod;
- TanStack Table;
- Recharts.

Banco de dados:

- PostgreSQL;
- banco unico no MVP;
- isolamento logico por `company_id`.

Ambiente local:

- Docker Compose;
- servicos `backend`, `frontend` e `postgres`;
- backend conecta ao banco usando hostname interno `postgres`, nunca `localhost`.

Exemplo conceitual:

```text
DATABASE_URL=postgresql+psycopg://app_user:app_password@postgres:5432/app_db
```

## 8. Regras Criticas de Negocio

Multiempresa:

- todo dado financeiro deve estar vinculado a `company_id`;
- usuario comum nunca envia `company_id` como fonte de verdade;
- backend obtem `company_id` a partir do usuario autenticado;
- toda listagem, detalhe, edicao, exclusao, relatorio, importacao e exportacao deve filtrar por `company_id`;
- endpoints de `platform_admin` sao a unica excecao controlada;
- testes devem garantir que uma empresa nao acessa dados de outra.

Assinatura:

- cadastro e self-service;
- primeiro usuario da empresa vira `company_admin`;
- cadastro publico nunca cria `platform_admin`;
- empresa nasce com trial gratuito de 30 dias;
- status de assinatura: `trialing`, `active`, `pending_payment`, `canceled`, `blocked`;
- nao usar status `expired` no MVP;
- trial vencido vira `pending_payment`;
- assinatura ativa vencida vira `pending_payment`;
- usuario com assinatura vencida pode fazer login;
- rotas financeiras devem ser bloqueadas quando a assinatura nao estiver valida;
- `auth/me` e `subscription/status` continuam acessiveis mesmo com assinatura vencida.

Renovacao manual:

- feita por `platform_admin`;
- sempre cria registro em `manual_payments`;
- se a assinatura ainda estiver ativa, soma 30 dias ao vencimento atual;
- se a assinatura estiver vencida, conta 30 dias a partir da data de pagamento ou confirmacao;
- nao implementar gateway de pagamento no MVP.

Datas financeiras:

- `competence_date`: relatorios gerenciais;
- `due_date`: contas a pagar, contas a receber e fluxo previsto;
- `settled_at`: fluxo realizado e saldo atual;
- `created_at`: auditoria tecnica.

## 9. Cuidados Com Dados Financeiros

Valores monetarios:

- nunca usar `float` para dinheiro;
- usar `Decimal` no backend, schemas, services, importacao e calculos;
- usar `NUMERIC(14,2)` ou `DECIMAL(14,2)` no PostgreSQL;
- preferir trafegar valores monetarios como string no JSON.

Campos monetarios principais:

- `companies.opening_balance`;
- `plans.price`;
- `manual_payments.amount`;
- `financial_transactions.amount`.

Saldo atual:

```text
opening_balance + entradas liquidadas - saidas liquidadas
```

Considerar apenas:

```text
status = settled
settled_at >= opening_balance_date
deleted_at IS NULL
```

Exclusao:

- evitar exclusao fisica de lancamentos financeiros;
- preferir soft delete com `deleted_at` ou status `canceled`;
- relatorios, saldo, listagens e exportacoes devem ignorar registros com `deleted_at` preenchido.

Auditoria minima:

- tabelas principais devem ter `created_at` e `updated_at`;
- entidades financeiras devem ter `created_by` e `updated_by`;
- logs tecnicos devem registrar eventos importantes sem expor senha, tokens ou dados sensiveis desnecessarios.

## 10. Ordem Geral de Implementacao

1. Criar estrutura base do repositorio.
2. Configurar backend FastAPI.
3. Configurar PostgreSQL no Docker Compose.
4. Configurar Alembic.
5. Criar tipos, base model e enums compartilhados.
6. Criar models iniciais.
7. Criar migration inicial.
8. Implementar seguranca base.
9. Implementar cadastro self-service.
10. Implementar login e `auth/me`.
11. Implementar status e bloqueio de assinatura.
12. Implementar criacao segura de `platform_admin`.
13. Implementar admin de assinaturas e pagamento manual.
14. Implementar job diario de expiracao.
15. Configurar frontend base.
16. Criar fluxo frontend de cadastro e login.
17. Criar tela de status/bloqueio de assinatura.
18. Implementar categorias financeiras.
19. Implementar lancamentos financeiros.
20. Implementar primeiro dashboard funcional.
21. Validar primeiro fluxo funcional completo.
22. Implementar contas a pagar e receber.
23. Implementar importacao de planilhas.
24. Implementar relatorios.
25. Implementar exportacao CSV.
26. Refinar UX.
27. Executar testes e revisao final.
