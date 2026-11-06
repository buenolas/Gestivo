# AGENTS.md - Orientacoes Para Agentes de IA

## 1. Produto e direcao atual

Este repositorio contem o Gestivo, uma plataforma de gestao empresarial para pequenas e medias empresas. A base financeira continua sendo central, e o produto esta evoluindo para integrar tambem funcionalidades de CRM.

O Gestivo ja nao deve ser descrito nem limitado como um MVP. A direcao atual combina gestao financeira com relacionamento comercial. A area de Contrapartes e a base existente para essa frente; nao apresente o CRM como completo antes de suas funcionalidades estarem implementadas.

CRM faz parte da direcao autorizada do produto. Desenvolva os fluxos concretos conforme os pedidos e prioridades do usuario, sem inventar requisitos de CRM que ainda nao foram definidos. Nao transforme o produto em um ERP completo.

## 2. Diretrizes de produto

- Preserve e evolua os fluxos financeiros existentes.
- Considere CRM e gestao de contrapartes como areas centrais de evolucao do produto.
- Mantenha a experiencia clara para empresas pequenas e medias.
- Prefira mudancas pequenas, coerentes com a arquitetura e com o pedido do usuario.
- Nao adicione modulos sem relacao com gestao financeira ou CRM sem autorizacao explicita.
- Mantenha o historico das decisoes relevantes atualizado em PROJECT_CONTEXT.md.

## 3. Regras obrigatorias de dados financeiros

- Nunca usar float para valores monetarios.
- Usar Decimal no backend, schemas, services, importacao e calculos.
- Usar NUMERIC ou DECIMAL no banco de dados para valores monetarios.
- Todo dado financeiro deve estar vinculado a company_id.
- Usuario comum nunca deve enviar company_id como fonte de verdade.
- O backend deve obter company_id a partir do usuario autenticado.
- Toda listagem, detalhe, edicao, exclusao, relatorio, importacao e exportacao deve filtrar por company_id.

## 4. Exclusao e historico

- Evitar exclusao fisica de lancamentos financeiros.
- Preferir soft delete com deleted_at ou cancelamento por status.
- Lancamentos removidos ou cancelados nao devem aparecer em listagens, relatorios, saldo ou exportacoes.
- Acoes de exclusao de empresas, perfis e dados relacionados devem respeitar os prazos de retencao definidos no produto.

## 5. Assinaturas e acesso

- Cadastro publico nunca cria platform_admin.
- Primeiro usuario da empresa vira company_admin.
- Empresa nasce com trial gratuito de 30 dias.
- Os status de assinatura usados atualmente sao trialing, active, pending_payment, canceled e blocked.
- Nao introduzir o status expired sem uma decisao explicita de produto.
- Trial vencido ou assinatura vencida vira pending_payment.
- Login deve continuar funcionando com assinatura vencida.
- Rotas financeiras devem exigir assinatura valida.
- Stripe Billing, Checkout, webhooks e Customer Portal fazem parte da integracao ja autorizada; outros gateways exigem autorizacao explicita.

## 6. Regras de importacao financeira

- Aceitar CSV e XLSX de ate 5 MB.
- A importacao financeira cria somente lancamentos financeiros.
- Nao criar categorias automaticamente.
- Mapear contato, cliente ou fornecedor da planilha para a contraparte do lancamento.
- Validar amount como Decimal.
- Respeitar company_id da empresa autenticada.
- Futuras importacoes de dados de CRM devem ter escopo e validacoes proprios, definidos quando forem solicitadas.

## 7. Seguranca, arquitetura e auditoria

- Toda query operacional de usuario comum deve usar company_id da sessao autenticada.
- Endpoints platform_admin sao a unica excecao controlada.
- Manter regras de negocio em services, nao apenas em handlers de rota.
- Toda entidade deve validar pertencimento a empresa autenticada.
- Tabelas principais devem ter created_at e updated_at.
- Entidades financeiras devem ter created_by e updated_by quando aplicavel.
- Nao logar senhas, hashes de senha, tokens JWT ou dados sensiveis desnecessarios.
- Preserve alteracoes existentes que nao foram feitas por voce.

## 8. Padrao de trabalho

Antes de mudancas relevantes:

1. Leia PROJECT_CONTEXT.md e este arquivo.
2. Confirme que a mudanca segue a direcao financeira e CRM do produto ou uma autorizacao explicita.
3. Confira a arquitetura, os nomes e os fluxos ja existentes.
4. Mantenha a implementacao focada e nao introduza bibliotecas ou modulos grandes sem necessidade.
5. Adicione ou atualize testes quando a mudanca afetar regra de negocio, seguranca, dinheiro, multiempresa ou assinatura.
6. Atualize a documentacao quando a mudanca alterar a direcao ou o comportamento do produto.

Quando houver duvida sobre uma funcionalidade especifica de CRM, use o pedido atual e o contexto do produto; nao trate CRM como proibido nem suponha detalhes que o usuario nao definiu.

## 9. Limites do produto

O Gestivo combina gestao financeira e CRM, mas nao deve virar um ERP completo. Emissao fiscal, integracao bancaria, conciliacao bancaria, folha de pagamento, estoque avancado, integracao contabil, novos gateways de pagamento, automacoes de comunicacao, aplicativo mobile nativo e permissoes complexas nao fazem parte da direcao atual e exigem autorizacao especifica antes de serem implementados.

A integracao Stripe existente e uma excecao ja autorizada para cobranca da plataforma. Essa autorizacao nao se estende a outros gateways nem a automacoes de pagamento.