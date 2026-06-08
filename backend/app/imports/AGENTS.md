# AGENTS.md - Importacao De Planilhas

Este modulo e estrategico para o produto.

Regras obrigatorias:

1. Nunca gravar lancamentos definitivos antes da confirmacao do usuario.
2. Sempre mostrar preview antes de gravar.
3. Validar data, descricao, valor e tipo.
4. Respeitar company_id em import_batch e transacoes geradas.
5. Registrar origem como importacao.
6. Erros devem ser claros para usuario nao tecnico.
7. Mostrar formato esperado da planilha.
8. Disponibilizar modelo de importacao quando possivel.
9. Nao confiar nos dados da planilha.
10. Usar Decimal para valores.
11. Limite de arquivo deve ser respeitado.
12. Criar testes com CSV e XLSX.
13. Nao transformar importacao em ETL complexo no MVP.
