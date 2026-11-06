# Contexto do Produto - Gestivo

## 1. Visao e fase atual

Gestivo e uma plataforma de gestao empresarial para pequenas e medias empresas. A gestao financeira segue como uma base central, e o produto esta evoluindo para reunir tambem funcionalidades de CRM e relacionamento comercial.

O Gestivo superou o enquadramento de MVP. Sua evolucao deve acompanhar as necessidades do produto e as prioridades do usuario. CRM faz parte da direcao aprovada; a existencia da direcao nao significa que um CRM completo ja esteja implementado.

A area de Contrapartes e o ponto de partida atual para organizar pessoas e empresas relacionadas aos lancamentos. Os fluxos adicionais de CRM serao definidos e implementados progressivamente, conforme forem priorizados.

## 2. Problema que o produto resolve

Pequenas empresas muitas vezes dependem de planilhas, anotacoes manuais e processos dispersos para acompanhar o dinheiro e as relacoes com clientes e outras empresas.

O Gestivo deve ajudar a empresa a:

- entender entradas, saidas, vencimentos, recebimentos e saldo;
- organizar categorias e lancamentos financeiros;
- acompanhar relacoes comerciais por meio de funcionalidades de CRM que serao desenvolvidas progressivamente;
- manter informacoes e rotinas empresariais organizadas em uma plataforma segura e simples de usar.

## 3. Publico-alvo

O produto atende pequenas empresas, prestadores de servico e negocios locais que precisam organizar o financeiro e melhorar a gestao das relacoes comerciais.

Perfis esperados incluem pequenas lojas, clinicas, escritorios, prestadores de servico, restaurantes, negocios familiares e empresas que hoje dependem de planilhas ou controles manuais.

## 4. Escopo e direcao do produto

### Gestao financeira

A plataforma possui fluxos para cadastro de empresa e usuario, autenticacao, assinatura, categorias financeiras, lancamentos, contas a pagar e receber como visoes de lancamentos, dashboard, fluxo de caixa, importacao de planilhas e exportacao de dados.

As regras de acesso por empresa, assinatura e precisao monetaria continuam obrigatorias durante a evolucao do produto.

### CRM e relacionamento comercial

CRM passa a ser uma frente central do Gestivo, junto com gestao financeira. A base atual inclui Contrapartes, apresentadas como uma lista unificada de pessoas e empresas relacionada aos lancamentos.

A evolucao deve permitir que o produto tenha mais recursos de relacionamento comercial, conforme pedidos e prioridades concretas do usuario. Nao restringir futuras funcionalidades de CRM por regras antigas que as classificavam como fora do MVP. Tambem nao presumir etapas, campos, automacoes ou processos especificos de CRM antes de serem definidos.

### Acesso e assinatura

O sistema oferece cadastro self-service, trial de 30 dias, controle de acesso por assinatura, renovacao manual excepcional por platform_admin e integracao Stripe Billing, Checkout, webhooks e Customer Portal.

## 5. Principios e limites de produto

- Manter o produto simples de aprender e adequado a pequenas e medias empresas.
- Evoluir os fluxos financeiros e de CRM de forma coerente e integrada.
- Nao transformar o Gestivo em um ERP completo.
- Nao tratar CRM, Contrapartes ou funcionalidades de relacionamento como areas proibidas.
- Definir o escopo de cada funcionalidade nova de CRM a partir dos pedidos e prioridades do usuario.
- Emissao fiscal, integracao e conciliacao bancaria, folha de pagamento, estoque avancado, integracao contabil, outros gateways de pagamento, automacoes de comunicacao, aplicativo mobile nativo e permissoes complexas nao fazem parte da direcao atual e exigem autorizacao especifica.
- A integracao Stripe para cobranca recorrente da plataforma ja foi autorizada; essa decisao nao autoriza outros gateways ou pagamentos automatizados.

## 6. Importacao de dados financeiros

A importacao financeira aceita CSV e XLSX de ate 5 MB e cria lancamentos financeiros.

- Seguir as etapas de upload, visualizacao previa, mapeamento, validacao e confirmacao.
- Nao criar categorias automaticamente.
- Mapear nome de cliente, fornecedor ou contato para a contraparte do lancamento.
- Validar valores monetarios com Decimal.
- Obter company_id a partir da empresa do usuario autenticado.
- Tratar uma futura importacao de dados de CRM como um fluxo separado, com escopo e validacoes definidos quando solicitada.

## 7. Stack tecnica

Backend: Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2.x e Alembic.

Frontend: React, Vite, TypeScript, Tailwind CSS e TanStack Query.

Banco de dados: PostgreSQL com isolamento logico por company_id.

Ambiente local: Docker Compose com servicos backend, frontend e postgres. O backend conecta ao banco pelo hostname interno postgres.

Ambiente de deploy: usar configuracao segura de ambiente, segredo JWT protegido, CORS restrito, banco persistente e migrations aplicadas no processo de publicacao.

## 7.1 Direcao atualizada em 2026-11-06

A decisao de produto registrada nesta data encerra o enquadramento do Gestivo como MVP e incorpora CRM como uma frente central de evolucao. A implementacao existente deve ser verificada no codigo antes de afirmar que uma funcionalidade esta pronta.

A base atual inclui os fluxos financeiros e de assinatura, categorias com subcategorias, lancamentos, dashboard, importacao e exportacao, administracao da plataforma e Contrapartes. As funcionalidades futuras de CRM ainda devem ser especificadas conforme as prioridades do usuario.

O documento historico docs/ROADMAP_MVP_FINAL.md registra o contexto de uma fase anterior. Ele nao define as restricoes atuais do produto.

## 8. Regras de negocio

### Isolamento por empresa

Todo dado financeiro deve pertencer a company_id. O usuario comum nunca informa company_id como fonte de verdade; o backend obtem esse valor da sessao autenticada. Listagens, detalhes, edicoes, exclusoes, relatorios, importacoes e exportacoes devem respeitar esse isolamento.

Endpoints de platform_admin sao a unica excecao controlada.

### Assinatura e acesso

- O cadastro publico cria uma empresa e seu primeiro usuario como company_admin, nunca como platform_admin.
- A empresa recebe trial gratuito de 30 dias.
- Os status de assinatura usados pelo sistema sao trialing, active, pending_payment, canceled e blocked.
- Nao usar expired como status.
- Trial vencido ou assinatura vencida passa para pending_payment.
- Login continua disponivel quando a assinatura vence.
- Rotas financeiras exigem assinatura valida; auth/me e subscription/status permanecem acessiveis.
- A integracao Stripe existente controla a cobranca recorrente e a liberacao apos confirmacao valida.

### Renovacao manual

Renovacoes manuais excepcionais sao feitas por platform_admin e registradas em manual_payments. Quando a assinatura esta ativa, os dias sao somados ao vencimento atual; quando esta vencida, contam a partir da data de pagamento ou confirmacao.

### Datas financeiras

- competence_date: relatorios gerenciais;
- due_date: contas a pagar, contas a receber e fluxo previsto;
- settled_at: fluxo realizado e saldo atual;
- created_at: auditoria tecnica.

## 9. Precisao monetaria e historico

- Nunca calcular dinheiro com float.
- Usar Decimal no backend, schemas, services, importacao e calculos.
- Usar NUMERIC(14,2) ou DECIMAL(14,2) no PostgreSQL e preferir valores como string no JSON.
- Todo dado financeiro deve estar vinculado a company_id.
- O saldo atual considera saldo inicial e entradas liquidadas menos saidas liquidadas, respeitando a data inicial configurada.
- Evitar exclusao fisica de lancamentos financeiros; preferir cancelamento ou soft delete.
- Registros excluidos ou cancelados nao devem afetar listagens, relatorios, saldo nem exportacoes.

## 10. Orientacoes para evolucao

- Preservar a seguranca, o isolamento entre empresas e a precisao financeira durante toda evolucao.
- Manter regras de negocio em services e validar pertencimento a empresa em toda operacao.
- Implementar funcionalidades financeiras e de CRM a partir das prioridades expressas pelo usuario.
- Nao inferir que a autorizacao para evoluir CRM inclui ERP, novos gateways, integracoes bancarias ou outras areas fora da direcao atual.
- Atualizar este documento quando uma decisao mudar a direcao, regras de negocio ou compromissos do produto.