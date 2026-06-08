# AGENTS.md - Assinatura, Trial E Bloqueio Comercial

Regras obrigatorias:

1. Trial gratuito dura 30 dias.
2. Usuario vencido pode fazer login.
3. Usuario vencido nao pode acessar rotas financeiras.
4. Rotas financeiras devem bloquear com HTTP 402 quando assinatura estiver vencida.
5. Nao usar status expired.
6. Status permitidos: trialing, active, pending_payment, canceled, blocked.
7. Renovacao antecipada soma 30 dias ao vencimento atual.
8. Renovacao vencida conta a partir da data de pagamento.
9. Pagamento e manual fora da plataforma.
10. Apenas platform_admin pode confirmar renovacao.
11. Criar job/script de expiracao idempotente.
12. Criar testes para trial, vencimento, bloqueio e renovacao.
