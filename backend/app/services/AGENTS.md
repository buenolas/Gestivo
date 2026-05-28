# AGENTS.md - Regras Financeiras, Saldo E Dashboard

Este diretorio contem regras financeiras sensiveis do sistema.

Regras obrigatorias:

1. Nunca usar float para dinheiro.
2. Usar Decimal no backend e numeric/decimal no banco.
3. Todo calculo financeiro deve respeitar company_id.
4. O saldo atual deve considerar:
   opening_balance + entradas liquidadas - saidas liquidadas.
5. O saldo inicial deve ser armazenado em Company como opening_balance e opening_balance_date.
6. Lancamentos so impactam saldo quando status = settled.
7. Lancamentos cancelados nao entram nos totais principais.
8. Quando opening_balance_date existir, considerar apenas lancamentos liquidados a partir dessa data para compor saldo atual.
9. Relatorios gerenciais usam competence_date.
10. Fluxo de contas a pagar/receber usa due_date.
11. Datas de liquidacao usam settled_at.
12. Nao criar BI avancado nesta fase.
13. Nao duplicar calculo financeiro no frontend.
14. O frontend apenas exibe dados calculados pelo backend.
15. Criar ou atualizar testes para qualquer alteracao em calculo financeiro.
