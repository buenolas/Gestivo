# AGENTS.md - Funcionarios E Despesas Salariais

Este modulo controla funcionarios apenas para fins financeiros simples do MVP.

Regras obrigatorias:

1. Este modulo nao e folha de pagamento completa.
2. Nao calcular INSS, FGTS, ferias, 13o, horas extras ou encargos trabalhistas nesta fase.
3. Todo funcionario deve ter company_id.
4. Usuario so pode acessar funcionarios da propria empresa.
5. Salario deve usar Decimal no backend e numeric/decimal no banco.
6. Funcionario deve ter status active, inactive ou ended.
7. Funcionario deve ter contract_start_date e pode ter contract_end_date.
8. Salario mensal deve gerar FinancialTransaction do tipo expense.
9. Despesa salarial deve ter source = employee_salary.
10. Evitar duplicidade de despesa salarial para o mesmo funcionario e mes.
11. A despesa salarial deve aparecer em contas a pagar.
12. O salario so impacta saldo atual quando o lancamento estiver settled.
13. O salario pendente deve impactar previsoes/contas a pagar, nao saldo realizado.
14. Preferir geracao manual por botao no MVP, nao job automatico obrigatorio.
15. Criar testes de multiempresa, geracao de salario e duplicidade.
