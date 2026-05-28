# Roadmap do MVP Final

Documento criado na Sessao 1: Auditoria, Alinhamento e Atualizacao do Contexto.

Data da auditoria: 2026-05-27.

## 1. Objetivo do MVP Final

O MVP final deve estar pronto para deploy e uso por clientes iniciais. O foco continua sendo
gestao financeira empresarial simples para pequenas e medias empresas que hoje dependem de
planilhas.

O produto deve provar que uma empresa consegue:

- criar conta sem intervencao manual;
- receber trial gratuito;
- cadastrar e importar lancamentos;
- acompanhar dashboard, contas a pagar e contas a receber;
- manter dados isolados por empresa;
- ser bloqueada quando a assinatura vencer;
- ser reativada manualmente por um administrador da plataforma.

O MVP final nao deve virar ERP completo, CRM, gateway de pagamento, sistema fiscal ou sistema de
folha.

## 2. O Que Ja Existe

### Backend

- FastAPI configurado em `backend/app/main.py`.
- CORS configurado por variavel de ambiente.
- Health check em `/health`.
- SQLAlchemy 2.x e Alembic configurados.
- PostgreSQL configurado via Docker Compose.
- Autenticacao JWT.
- Hash de senha com bcrypt.
- Cadastro self-service em `/auth/register`.
- Login em `/auth/login`.
- Endpoint `/auth/me`.
- Empresas vinculadas a usuarios.
- Criacao segura de `platform_admin` por script.
- Assinatura simplificada em campos da tabela `companies`.
- Status de assinatura sem `expired`: `trialing`, `active`, `pending_payment`, `canceled`, `blocked`.
- Renovacao manual por `platform_admin`.
- Historico de pagamentos manuais em `manual_payments`.
- Categorias financeiras.
- Lancamentos financeiros.
- Contas a pagar e receber como visoes filtradas de lancamentos.
- Dashboard inicial.
- Importacao CSV/XLSX com upload, preview, mapeamento, validacao e confirmacao.
- Testes automatizados concentrados em assinatura e acesso.

### Frontend

- React/Vite/TypeScript configurado.
- Login e cadastro.
- Layout autenticado para empresa.
- Layout inicial para `platform_admin`.
- Dashboard.
- Categorias.
- Contatos.
- Lancamentos.
- Contas a pagar.
- Contas a receber.
- Importacao de planilhas.
- Admin inicial de assinaturas e renovacao manual.
- Bloqueio visual basico quando assinatura esta invalida.

### Infraestrutura Local

- `docker-compose.yml` com `backend`, `frontend` e `postgres`.
- Volume persistente para PostgreSQL.
- `.env.example` com variaveis principais.
- README inicial com comandos de execucao.

## 3. Divergencias Entre Documentacao e Implementacao

### Contatos Fora do Escopo

A documentacao define que nao deve haver modulo de contatos/clientes/fornecedores no MVP. A
implementacao atual possui:

- model `Contact`;
- migration de `contacts`;
- rotas `/contacts`;
- tela `ContactsPage`;
- `contact_id` em `financial_transactions`;
- selecao de contato na tela de lancamentos.

Decisao pendente para o MVP final: remover/ocultar contatos e migrar para `counterparty_name`, ou
autorizar explicitamente contatos como excecao de escopo.

### Saldo Inicial Ausente

A documentacao define `companies.opening_balance` e `companies.opening_balance_date`. A
implementacao atual nao possui esses campos.

Impacto:

- dashboard calcula saldo atual apenas com entradas liquidadas menos saidas liquidadas;
- empresas que entram com saldo anterior terao saldo incorreto.

### Soft Delete Ausente

A documentacao define que lancamentos com `deleted_at` devem ser ignorados em listagens,
relatorios, saldo e exportacoes. A implementacao atual usa `status=canceled` e `canceled_at`, mas
nao possui `deleted_at`.

Decisao pendente: manter cancelamento como mecanismo oficial do MVP ou adicionar `deleted_at`.

### Exportacao CSV Ausente

Exportacao CSV de lancamentos faz parte do MVP documentado, mas ainda nao existe endpoint nem tela
dedicada.

### Job Diario de Expiracao

A regra de expiracao esta implementada dentro do fluxo de consulta de status de assinatura, mas nao
existe uma rotina operacional separada para execucao diaria.

### Importacao XLSX

A arquitetura documentada mencionava Pandas/OpenPyXL. A implementacao atual usa parser proprio com
`zipfile` e `ElementTree`.

Decisao pendente: manter parser proprio se for suficiente para o MVP ou trocar para OpenPyXL para
maior compatibilidade.

### Encoding de Textos

Ha textos com caracteres quebrados em arquivos Python, TSX e README. Isso afeta qualidade percebida
e precisa ser corrigido antes de uso por clientes.

### Bibliotecas Frontend Planejadas

A stack planejada menciona React Hook Form, Zod, TanStack Table e Recharts. O frontend atual ainda
nao usa essas bibliotecas.

Decisao recomendada: nao adicionar bibliotecas apenas por planejamento. Adicionar somente se
resolverem problemas concretos do MVP final.

### Role de Usuario

A documentacao previa `company_member`; o codigo usa `user`.

Decisao pendente: renomear para `company_member` antes de clientes ou documentar `user` como papel
reservado futuro.

## 4. O Que Falta Para MVP Final

### Prioridade 1 - Pronto Para Cliente

- Corrigir textos com encoding quebrado.
- Ajustar tela de bloqueio para mensagem simples e clara.
- Garantir que `.env.example` e README expliquem ambiente de producao/deploy.
- Configurar fluxo operacional de migrations em deploy.
- Validar `APP_DEBUG=false` em producao.
- Validar CORS por ambiente.
- Garantir ausencia de segredos reais versionados.
- Criar checklist de deploy.

### Prioridade 2 - Regras Financeiras Criticas

- Implementar `opening_balance` e `opening_balance_date`.
- Ajustar saldo atual para considerar saldo inicial.
- Decidir e aplicar politica final de exclusao/cancelamento.
- Garantir que calculos ignorem registros cancelados e, se existir, `deleted_at`.
- Ampliar testes de Decimal e saldo.

### Prioridade 3 - Fechar Escopo do MVP

- Resolver divergencia do modulo de contatos.
- Implementar exportacao CSV de lancamentos.
- Garantir que exportacao respeite filtros e `company_id`.
- Revisar importacao para nao criar categorias nem contatos automaticamente.
- Decidir parser XLSX final.

### Prioridade 4 - Assinatura e Operacao

- Criar rotina executavel para expiracao diaria de assinaturas.
- Documentar como agendar a rotina no ambiente de deploy.
- Testar bloqueio de rotas financeiras com assinatura vencida.
- Testar login e rotas permitidas quando assinatura esta vencida.
- Revisar admin de renovacao manual.

### Prioridade 5 - Qualidade e Confianca

- Criar testes de isolamento multiempresa.
- Criar testes de lancamentos, contas a pagar/receber, dashboard, importacao e exportacao.
- Rodar build do frontend.
- Rodar testes backend em Docker Compose.
- Revisar UX de estados vazios, loading, erros e confirmacoes.
- Atualizar README apos ajustes finais.

## 5. Features Que Entram Agora no MVP Final

Entram agora, por serem necessarias para uso real por clientes iniciais:

- preparacao para deploy;
- checklist operacional de deploy;
- correcao de encoding;
- tela de bloqueio simples;
- saldo inicial da empresa;
- saldo atual correto;
- exportacao CSV;
- rotina diaria de expiracao de assinatura;
- testes de isolamento por empresa;
- testes de bloqueio por assinatura;
- testes de dinheiro com Decimal;
- revisao de importacao para fluxo compreensivel por usuario nao tecnico;
- revisao de README e documentacao operacional.

## 6. Features Que Continuam Fora do MVP

Continuam fora do MVP:

- ERP completo;
- CRM;
- modulo completo de clientes, fornecedores ou contatos, salvo autorizacao explicita;
- gateway de pagamento;
- Stripe;
- Mercado Pago;
- Pix automatizado;
- boleto;
- cartao de credito;
- webhook;
- nota fiscal;
- integracao bancaria;
- conciliacao bancaria;
- estoque avancado;
- folha de pagamento;
- app mobile nativo;
- IA;
- WhatsApp automatico;
- e-mail automatico;
- permissoes complexas;
- relatorios avancados;
- exportacao PDF;
- exportacao Excel formatada;
- integracao contabil;
- autenticacao social, como Google, ate decisao especifica.

## 7. Riscos

### Riscos Tecnicos

- Saldo incorreto sem `opening_balance`.
- Vazamento entre empresas se alguma query deixar de filtrar por `company_id`.
- Inconsistencia entre cancelamento e soft delete.
- Parser XLSX proprio pode falhar em planilhas reais mais complexas.
- Falta de testes nos fluxos financeiros principais.
- Deploy pode falhar se variaveis e migrations nao estiverem documentadas.
- CORS e debug podem ficar inseguros em producao se nao forem revisados.

### Riscos de Produto

- Modulo de contatos pode expandir o escopo para CRM.
- Importacao pode frustrar usuarios se erros nao forem explicados com clareza.
- Tela de bloqueio muito tecnica pode gerar confusao em clientes.
- Dashboard com saldo incompleto reduz confianca.
- Ausencia de exportacao CSV reduz reversibilidade percebida.

### Riscos de Operacao

- Renovacao manual depende de `platform_admin` e rotina humana.
- Sem job diario, assinaturas podem ficar vencidas mas ainda ativas ate alguem consultar status.
- Sem checklist de deploy, cada publicacao pode depender de memoria operacional.

## 8. Roadmap Proposto

### Sessao 2 - Higiene de Produto e Deploy

Objetivo: preparar a base para ambiente real sem alterar escopo financeiro.

Tarefas sugeridas:

- corrigir encoding de textos visiveis;
- ajustar tela de bloqueio para texto aprovado;
- revisar `.env.example`;
- adicionar documentacao de deploy;
- adicionar checklist operacional;
- validar build frontend;
- validar testes backend.

### Sessao 3 - Saldo Inicial e Saldo Atual

Objetivo: corrigir a principal regra financeira ausente.

Tarefas sugeridas:

- adicionar `opening_balance` e `opening_balance_date` em `companies`;
- atualizar schemas e tela de empresa/configuracao;
- ajustar dashboard para saldo atual correto;
- criar testes de saldo.

### Sessao 4 - Escopo de Contatos e Lancamentos

Objetivo: resolver divergencia entre contato como modulo e `counterparty_name`.

Tarefas sugeridas:

- decidir remover/ocultar contatos ou manter como excecao;
- se remover: adicionar `counterparty_name`, ajustar frontend, services e importacao;
- se manter: atualizar documentacao e justificar excecao.

### Sessao 5 - Exportacao CSV

Objetivo: entregar reversibilidade dos dados.

Tarefas sugeridas:

- endpoint de exportacao filtrada;
- CSV UTF-8 com BOM;
- filtros de periodo, tipo, status e categoria;
- isolamento por `company_id`;
- botao no frontend;
- testes.

### Sessao 6 - Expiracao de Assinaturas

Objetivo: tornar a assinatura operacional fora do fluxo de consulta.

Tarefas sugeridas:

- criar job/command de expiracao;
- documentar agendamento no deploy;
- testes para trial vencido e assinatura ativa vencida;
- validar login permitido e rotas financeiras bloqueadas.

### Sessao 7 - Importacao e UX Final

Objetivo: deixar a importacao usavel por clientes nao tecnicos.

Tarefas sugeridas:

- mostrar formato esperado da planilha;
- melhorar mensagens de erro;
- decidir parser XLSX;
- revisar comportamento de duplicidades;
- reforcar que nao cria categorias/contatos automaticamente.

### Sessao 8 - Testes e Revisao Final

Objetivo: liberar MVP final para clientes iniciais.

Tarefas sugeridas:

- suite de testes dos fluxos criticos;
- validacao via Docker Compose;
- revisao de README;
- checklist de deploy;
- sanity check de seguranca;
- revisao final de escopo.

## 9. Criterios de Pronto Para MVP Final

O MVP final pode ser considerado pronto quando:

- cadastro, login, trial, bloqueio e renovacao manual funcionarem de ponta a ponta;
- dados financeiros estiverem isolados por `company_id`;
- saldo atual considerar saldo inicial;
- dashboard e contas usarem as datas corretas;
- importacao CSV/XLSX funcionar para planilhas simples;
- exportacao CSV estiver disponivel;
- assinatura vencida bloquear rotas financeiras e manter login;
- deploy estiver documentado;
- testes criticos passarem;
- README e contexto estiverem atualizados;
- nenhuma funcionalidade fora do MVP tiver sido adicionada sem autorizacao.
