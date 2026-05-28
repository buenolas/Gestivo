# AGENTS.md - Autenticacao, Seguranca De E-mail E Login

Este modulo lida com autenticacao e identidade do usuario.

Regras obrigatorias:

1. Nunca salvar senha em texto puro.
2. Nunca hardcodar secrets, tokens ou senhas.
3. JWT secret deve vir de variavel de ambiente.
4. Validacao de e-mail nao deve depender apenas de regex.
5. Para confirmar e-mail, usar token seguro, com expiracao e armazenamento em hash quando possivel.
6. Usuario nao verificado nao deve acessar rotas financeiras de cliente.
7. platform_admin criado por script pode nascer verificado.
8. Mensagens de erro nao devem vazar informacoes sensiveis.
9. Login com Google deve validar o token no backend.
10. E-mail vindo do Google so deve ser aceito se email_verified for verdadeiro.
11. Criar testes para cadastro, login, e-mail nao verificado, confirmacao e acesso bloqueado.
12. Nao implementar permissoes complexas fora do escopo.
