# AGENTS.md - Orientacoes Para Agentes de IA

## 1. Descricao Curta do Produto

Este repositorio contem o Gestivo, um sistema de gestao financeira empresarial para pequenas e medias empresas que ainda controlam o financeiro por planilhas ou processos manuais.

O produto deve comecar como um sistema simples de controle financeiro, fluxo de caixa, contas a pagar, contas a receber, categorias, importacao de planilhas e relatorios basicos.

Nao transforme este projeto em ERP completo. Nao implemente CRM no MVP.

## 2. Prioridades do MVP

As prioridades do MVP sao:

1. Cadastro self-service de empresa e usuario admin.
2. Trial gratuito de 30 dias.
3. Bloqueio de rotas financeiras quando a assinatura vencer.
4. Renovacao manual por `platform_admin`.
5. Categorias financeiras.
6. Lancamentos financeiros.
7. Contas a pagar e receber como visoes filtradas dos lancamentos.
8. Dashboard simples do mes atual.
9. Importacao CSV/XLSX de ate 5 MB.
10. Exportacao CSV de lancamentos.

O objetivo do MVP e provar que uma empresa consegue sair de uma planilha simples para um controle financeiro mais organizado, seguro e visual.

## 3. Regras Obrigatorias

Escopo:

- Nao transformar o projeto em ERP completo.
- Nao implementar CRM no MVP.
- Nao implementar funcionalidades futuras sem autorizacao explicita.
- Nao expandir escopo por conta propria.

Dados financeiros:

- Nao usar `float` para valores monetarios.
- Usar `Decimal` no backend, schemas, services, importacao e calculos.
- Usar `NUMERIC` ou `DECIMAL` no banco de dados para valores monetarios.
- Todo dado financeiro deve estar vinculado a `company_id`.
- Usuario comum nunca deve enviar `company_id` como fonte de verdade.
- O backend deve obter `company_id` a partir do usuario autenticado.
- Toda listagem, detalhe, edicao, exclusao, relatorio, importacao e exportacao deve filtrar por `company_id`.

Exclusao e historico:

- Evitar exclusao fisica de lancamentos financeiros.
- Preferir soft delete com `deleted_at` ou cancelamento por status.
- Lancamentos com `deleted_at` preenchido nao devem aparecer em listagens, relatorios, saldo ou exportacoes.

Assinatura:

- Cadastro publico nunca cria `platform_admin`.
- Primeiro usuario da empresa vira `company_admin`.
- Empresa nasce com trial gratuito de 30 dias.
- Status de assinatura no MVP: `trialing`, `active`, `pending_payment`, `canceled`, `blocked`.
- Nao usar status `expired` no MVP.
- Trial vencido ou assinatura vencida vira `pending_payment`.
- Login deve continuar funcionando com assinatura vencida.
- Rotas financeiras devem exigir assinatura valida.

## 4. Funcionalidades Proibidas no MVP

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
- relatorios avancados fora do escopo;
- exportacao PDF;
- exportacao Excel formatada.

Se uma tarefa parecer exigir qualquer item acima, pare e peca autorizacao explicita.

## 5. Padrao de Trabalho Esperado

Antes de propor ou implementar mudancas relevantes:

1. Leia `PROJECT_CONTEXT.md`.
2. Leia este `AGENTS.md`.
3. Confirme que a mudanca esta dentro do escopo do MVP.
4. Mantenha as alteracoes pequenas e focadas.
5. Prefira seguir a arquitetura e os nomes ja definidos.
6. Nao introduza bibliotecas, padroes ou modulos grandes sem necessidade clara.
7. Adicione ou atualize testes quando a mudanca afetar regra de negocio, seguranca, dinheiro, multiempresa ou assinatura.

Ao trabalhar no codigo:

- preserve alteracoes existentes que nao foram feitas por voce;
- nao reverta trabalho do usuario sem pedido explicito;
- use nomes claros e consistentes;
- mantenha regras de negocio em services, nao espalhadas apenas em handlers de rota;
- garanta que endpoints financeiros usam dependencies de autenticacao e assinatura valida.

## 6. Cuidados Tecnicos

Stack definida:

- Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x, Alembic.
- Frontend: React, Vite, TypeScript, Tailwind CSS, TanStack Query, React Hook Form, Zod, TanStack Table, Recharts.
- Banco: PostgreSQL.
- Ambiente local: Docker Compose com servicos `backend`, `frontend` e `postgres`.

Banco e dinheiro:

- Campos monetarios devem ser `NUMERIC(14,2)` ou `DECIMAL(14,2)`.
- Valores monetarios devem ser tratados como `Decimal`.
- Prefira serializar valores monetarios como string no JSON.
- Nunca faca calculo financeiro com `float`.

Multiempresa:

- Toda query operacional de usuario comum deve usar `company_id` da sessao autenticada.
- Endpoints `platform_admin` sao a unica excecao controlada.
- Testes devem garantir que uma empresa nao acessa dados de outra.

Datas financeiras:

- `competence_date`: relatorios gerenciais.
- `due_date`: contas a pagar, contas a receber e fluxo previsto.
- `settled_at`: fluxo realizado e saldo atual.
- `created_at`: auditoria tecnica.

Importacao:

- Aceitar CSV e XLSX.
- Limitar arquivos a 5 MB.
- Criar apenas `financial_transactions`.
- Nao criar contatos.
- Nao criar categorias automaticamente.
- Mapear contato, cliente ou fornecedor para `counterparty_name`.
- Validar `amount` como `Decimal`.
- Respeitar `company_id` da empresa autenticada.

Logs e auditoria minima:

- Tabelas principais devem ter `created_at` e `updated_at`.
- Entidades financeiras devem ter `created_by` e `updated_by`.
- Nao logar senhas, hash de senha, tokens JWT ou dados sensiveis desnecessarios.

## 7. Nao Expandir Escopo Sem Autorizacao

Este projeto deve permanecer enxuto ate o MVP estar validado.

Nao implemente funcionalidades futuras apenas porque parecem uteis. Nao antecipe ERP, CRM, pagamentos online, integracoes externas, IA, automacoes de comunicacao, relatorios avancados ou permissoes complexas.

Quando houver duvida, escolha a opcao mais simples que mantenha:

- controle financeiro confiavel;
- seguranca dos dados;
- isolamento por empresa;
- precisao monetaria;
- escopo do MVP.

Qualquer expansao fora do `PROJECT_CONTEXT.md` precisa de autorizacao explicita do usuario.
