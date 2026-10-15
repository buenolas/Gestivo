# Stripe no Gestivo

O checkout e a renovacao mensal usam Stripe Billing e Checkout hospedado. O Gestivo guarda os IDs do Customer e da Subscription e só altera o acesso depois de validar webhooks assinados. O retorno do navegador ao Checkout não confirma o pagamento.

## Configurar o ambiente de teste

1. No Dashboard Stripe, ative o ambiente de teste e crie um produto separado para cada plano: Básico, Intermediário, Avançado e Pro.
2. Em cada produto, crie um Price recorrente mensal em BRL, respectivamente `R$ 10,90`, `R$ 21,90`, `R$ 29,90` e `R$ 39,90`. O backend valida moeda, intervalo, valor e estado ativo antes de abrir o Checkout.
3. Copie o ID `price_...` de cada Price de teste.
4. No arquivo `.env` da raiz deste repositório, preencha:

```dotenv
STRIPE_SECRET_KEY=
STRIPE_WEBHOOK_SECRET=
STRIPE_BILLING_PORTAL_CONFIGURATION_ID=
STRIPE_PRICE_ID_BASIC=
STRIPE_PRICE_ID_INTERMEDIATE=
STRIPE_PRICE_ID_ADVANCED=
STRIPE_PRICE_ID_PRO=
```

Use a chave secreta do ambiente de teste (ou uma chave restrita de teste com permissões mínimas para ler Prices e criar sessões do Checkout, Customers e Customer Portal). Não cole a chave em conversas, código, `frontend`, `VITE_*` ou arquivos versionados. O `.env` local já está excluído do Git. A chave publicável `pk_test_...` não é usada: o navegador recebe somente a URL HTTPS do Checkout hospedado.

`STRIPE_BILLING_PORTAL_CONFIGURATION_ID` é opcional. Se preenchida, deve ser o ID de uma configuração de Customer Portal do mesmo ambiente das chaves. Configure o portal para permitir consulta de faturas, atualização do meio de pagamento e troca de assinatura. No catálogo de produtos do portal, inclua os quatro preços mensais configurados nas variáveis `STRIPE_PRICE_ID_BASIC`, `STRIPE_PRICE_ID_INTERMEDIATE`, `STRIPE_PRICE_ID_ADVANCED` e `STRIPE_PRICE_ID_PRO`; isso permite que a confirmação de upgrade mostre o preço e a cobrança antes de o cliente aceitar.

Os Price IDs são específicos do ambiente Stripe. Os IDs de teste não funcionam com uma chave live. Para qualquer ambiente publicado, configure chaves, Prices e segredo de webhook próprios no gerenciador de segredos do backend; nunca envie segredos ao frontend.

## Receber eventos localmente

Instale o [Stripe CLI](https://docs.stripe.com/cli/install), autentique com `stripe login` e rode:

```bash
stripe listen --forward-to localhost:8000/webhooks/stripe
```

O CLI mostra um segredo de assinatura `whsec_...`. Copie-o para `STRIPE_WEBHOOK_SECRET` no `.env` local e recrie o container do backend com `docker compose up -d --force-recreate backend`. Mantenha `stripe listen` aberto enquanto usa o ambiente local. Esse segredo é diferente da chave secreta da API e deve permanecer privado.

Para um endpoint remoto de teste, configure no Dashboard Stripe um destino de webhook de eventos **Snapshot** com o endereço HTTPS `https://<host-da-api>/webhooks/stripe` e cadastre estes eventos. O handler atual recebe eventos Snapshot do Stripe Billing:

- `checkout.session.completed`
- `checkout.session.async_payment_succeeded`
- `checkout.session.async_payment_failed`
- `customer.subscription.created`
- `customer.subscription.updated`
- `customer.subscription.deleted`
- `invoice.paid`
- `invoice.payment_failed`
- `charge.refunded`
- `charge.dispute.created`
- `radar.early_fraud_warning.created`

Copie o segredo `whsec_...` mostrado para aquele endpoint para `STRIPE_WEBHOOK_SECRET`. Cada endpoint tem seu próprio segredo. O handler valida a assinatura sobre o corpo original, registra o ID do evento para idempotência e responde com erro temporário se o banco não conseguir processá-lo, permitindo que o Stripe tente novamente.

Reembolsos, disputas e alertas antecipados de fraude ficam em revisão manual e podem ser consultados em `GET /admin/stripe/risk-events` por um `platform_admin`; depois da análise, o evento pode ser marcado em `PATCH /admin/stripe/risk-events/{event_id}/reviewed`. Esses eventos não bloqueiam nem cancelam uma assinatura automaticamente.

Para vincular disputas e alertas Radar à empresa, a chave restrita precisa ter permissão de leitura de cobranças (`Charges: Read`). Sem essa permissão, o evento continua salvo com o ID da cobrança, mas pode aparecer sem empresa associada. Reembolsos normalmente já trazem o Customer no próprio evento.

## Fluxo no produto

- Depois do trial, o `company_admin` escolhe um dos quatro planos mensais. A API deriva a empresa da sessão autenticada; não aceita `company_id` do navegador.
- Checkout envia ao Stripe o Price ID configurado para o plano e metadados mínimos de empresa e plano. Nenhum valor monetário vem do navegador.
- O Stripe confirma ou atualiza a assinatura por webhook. `checkout.session.completed` sozinho só vincula os IDs; o acesso depende do estado `active` confirmado pelo ciclo de eventos.
- Falha de pagamento move a empresa para `pending_payment`. Cancelamento move para `canceled`. O bloqueio administrativo `blocked` não pode ser removido por eventos Stripe.
- O portal de cobrança do Stripe fica disponível para administradores de empresa vinculadas a um Customer e retorna ao Gestivo.
- A renovação manual por `platform_admin` continua disponível para exceções operacionais.

## Antes de uso em produção

Esta implementação não configura Stripe Tax nem `automatic_tax`; confirme a forma de apurar e recolher tributos aplicáveis antes de cobrar clientes. Revise também as responsabilidades fiscais junto ao contador da empresa.

Antes de considerar a integração pronta para produção, adicione os três eventos de risco ao destino live e defina quem acompanha a fila de revisão. O código registra os sinais e permite marcá-los como revisados, mas não prepara evidências nem executa reembolsos ou outras decisões automáticas de risco.

Faça primeiro a configuração e validação no ambiente de teste. Este trabalho não publica alterações nem grava credenciais Stripe na conta.
