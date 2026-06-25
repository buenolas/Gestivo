# Gestivo

Uma plataforma simples, segura e visual para pequenas e medias empresas que querem sair das planilhas e organizar o controle financeiro do dia a dia.

Este documento apresenta o produto como ele deve ser entendido por clientes, operadores e decisores: qual problema resolve, para quem foi criado, como usar, quais fluxos entrega e quais limites foram definidos para manter o MVP enxuto.

---

## 1. Apresentacao do produto

O Gestivo e um sistema web para empresas que ainda controlam entradas, saidas, contas a pagar, contas a receber e fluxo de caixa em planilhas, cadernos, mensagens ou processos pouco padronizados.

A proposta nao e substituir um ERP completo. O objetivo do MVP e muito mais direto: permitir que uma empresa cadastre seus lancamentos financeiros, acompanhe o mes atual, organize categorias, visualize pendencias, importe uma planilha existente e mantenha seus dados separados com seguranca por empresa.

Em outras palavras, o produto foi desenhado para responder perguntas simples e importantes:

- Quanto entrou neste mes?
- Quanto saiu?
- Quais contas ainda preciso pagar?
- Quais recebimentos ainda estao pendentes?
- Meu caixa esta melhorando ou piorando?
- Quais categorias concentram mais despesas?
- Como migrar meu controle atual sem comecar tudo do zero?

## 2. Publico-alvo

O produto foi pensado para pequenas empresas, prestadores de servico e negocios locais que ja possuem alguma rotina financeira, mas ainda dependem de planilhas ou controles manuais.

Exemplos de perfis atendidos:

- pequenas lojas;
- clinicas;
- escritorios;
- prestadores de servico;
- restaurantes e lanchonetes em fase inicial;
- negocios familiares;
- empresas que usam Excel ou Google Sheets para controlar entradas e saidas.

O MVP evita deliberadamente nichos que exigem fiscal complexo, estoque avancado, emissao de nota fiscal, conciliacao bancaria ou integracoes financeiras automaticas.

## 3. Proposta de valor

### Clareza financeira sem complexidade de ERP

A empresa ganha uma visao centralizada do financeiro sem precisar implantar um sistema grande, caro e cheio de modulos que nao fazem parte da rotina inicial.

### Migracao a partir de planilhas

O sistema permite importar arquivos CSV ou XLSX de ate 5 MB, ajudando o cliente a aproveitar dados que ja possui. O fluxo de importacao foi pensado para reduzir atrito: enviar arquivo, revisar, mapear campos, validar e confirmar a criacao dos lancamentos.

### Controle por assinatura simples

Cada empresa inicia com trial gratuito de 30 dias. Quando o trial ou a assinatura vence, o login continua funcionando, mas as rotas financeiras sao bloqueadas ate a renovacao manual por um administrador da plataforma.

### Dados isolados por empresa

Os dados financeiros pertencem sempre a uma empresa. O usuario comum nao informa `company_id`; o backend identifica a empresa a partir da sessao autenticada. Isso reduz risco operacional e preserva isolamento entre clientes.

### Precisao para dinheiro

Valores monetarios sao tratados com `Decimal` no backend e com campos `NUMERIC`/`DECIMAL` no banco de dados. O produto evita calculos financeiros com `float`.

## 4. O que o MVP entrega

O MVP foi definido para provar um ponto muito especifico: uma empresa que controla o financeiro em planilhas consegue migrar para uma experiencia mais organizada, segura e visual.

Funcionalidades principais:

- cadastro self-service de empresa e usuario administrador;
- trial gratuito de 30 dias;
- login com e-mail e senha;
- confirmacao de e-mail;
- recuperacao de senha por codigo enviado por e-mail;
- onboarding com dados iniciais da empresa;
- bloqueio das funcionalidades financeiras quando a assinatura nao esta valida;
- renovacao manual de acesso por `platform_admin`;
- categorias financeiras;
- lancamentos financeiros de entrada e saida;
- contas a pagar como visao filtrada dos lancamentos;
- contas a receber como visao filtrada dos lancamentos;
- dashboard simples do mes atual;
- saldo atual com base em saldo inicial e lancamentos liquidados;
- importacao CSV/XLSX de ate 5 MB;
- exportacao CSV de lancamentos financeiros;
- area administrativa para acompanhamento de clientes, planos e renovacoes.

## 5. O que nao faz parte do MVP

Para manter o produto focado, os itens abaixo nao fazem parte da proposta inicial e nao devem ser apresentados como promessa comercial:

- ERP completo;
- CRM;
- emissao de nota fiscal;
- integracao bancaria;
- conciliacao bancaria;
- gateway de pagamento;
- Stripe, Mercado Pago, Pix automatico, boleto ou cartao de credito;
- webhook de pagamento;
- folha de pagamento;
- estoque avancado;
- integracao contabil;
- aplicativo mobile nativo;
- inteligencia artificial;
- WhatsApp automatico;
- e-mail automatico de cobranca ou comunicacao;
- recorrencia avancada;
- permissoes complexas;
- relatorios avancados;
- exportacao PDF;
- exportacao Excel formatada.

Essas limitacoes sao parte da estrategia: entregar um financeiro operacional, compreensivel e pronto para validacao com clientes iniciais.

---

## 6. Experiencia do cliente

### Primeiro acesso

O cliente entra no sistema, cria sua conta, confirma o e-mail e conclui a configuracao inicial da empresa. A partir dai, recebe 30 dias de trial gratuito para usar as funcionalidades financeiras.

### Recuperacao de senha

Na tela de login, o usuario pode solicitar um codigo de verificacao por e-mail para redefinir a senha. O envio usa o mesmo `EMAIL_DELIVERY_MODE` configurado para confirmacao de e-mail (`mock`, SMTP ou Brevo) e nao revela se o e-mail informado existe.

### Rotina diaria

No uso cotidiano, a empresa registra entradas e saidas, acompanha contas a pagar e a receber, revisa o dashboard do mes e mantem categorias financeiras organizadas.

### Migracao de planilhas

Empresas que ja possuem uma planilha podem importar os dados para reduzir trabalho manual. A importacao cria lancamentos financeiros e respeita as categorias ja cadastradas.

### Renovacao

Ao fim do trial ou da assinatura, o usuario continua conseguindo entrar no sistema, mas o acesso financeiro fica bloqueado. A liberacao acontece manualmente pela area administrativa da plataforma apos confirmacao externa do pagamento.

---

## 7. Tutorial: criar conta e configurar empresa

Este fluxo e destinado ao primeiro usuario da empresa. Ele sera o administrador da conta.

1. Acesse a tela inicial do sistema.
2. Clique em criar conta.
3. Informe e-mail e senha.
4. Confirme o e-mail pelo link ou token de verificacao.
5. Preencha a configuracao inicial:
   - nome da empresa;
   - nome completo do usuario;
   - saldo inicial da empresa.
6. Salve para acessar o painel financeiro.

Resultado esperado: a empresa e criada, o usuario se torna `company_admin` e o trial gratuito de 30 dias e iniciado.

## 8. Tutorial: entender o dashboard

O dashboard e a primeira visao gerencial do sistema. Ele resume o mes atual e ajuda o usuario a tomar decisoes rapidas.

Use esta tela para acompanhar:

- entradas do mes;
- saidas do mes;
- saldo atual;
- contas vencendo;
- recebimentos pendentes;
- distribuicao por categorias;
- comportamento geral do caixa.

Boas praticas:

- revise o dashboard no inicio e no fim do dia;
- mantenha lancamentos liquidados atualizados;
- use categorias consistentes para facilitar leitura;
- acompanhe pendencias antes de tomar decisoes de pagamento.

## 9. Tutorial: cadastrar categorias financeiras

Categorias ajudam a organizar receitas e despesas. Elas permitem entender para onde o dinheiro esta indo e quais entradas sustentam o caixa.

Exemplos de categorias:

- vendas;
- mensalidades;
- servicos prestados;
- aluguel;
- fornecedores;
- impostos;
- marketing;
- energia;
- internet;
- manutencao.

Passo a passo:

1. Acesse o menu Categorias.
2. Crie uma nova categoria.
3. Informe um nome claro.
4. Defina se ela sera usada para entrada, saida ou ambos, conforme o modelo disponivel.
5. Salve.

Recomendacao: comece com poucas categorias. Uma categorizacao simples e consistente costuma ser mais util do que uma lista enorme dificil de manter.

## 10. Tutorial: cadastrar lancamentos

Lancamentos sao o centro do sistema. Cada entrada ou saida relevante deve ser registrada como um lancamento financeiro.

Campos importantes:

- tipo: entrada ou saida;
- descricao;
- valor;
- categoria;
- data de competencia;
- data de vencimento;
- data de liquidacao, quando pago ou recebido;
- status;
- contraparte ou observacao relacionada, quando aplicavel.

Passo a passo:

1. Acesse Lancamentos.
2. Clique para criar um novo lancamento.
3. Escolha se e entrada ou saida.
4. Informe descricao, valor e categoria.
5. Preencha as datas financeiras.
6. Defina o status correto.
7. Salve.

Como usar os status:

- pendente: valor previsto, ainda nao pago ou recebido;
- liquidado: valor ja pago ou recebido;
- cancelado: valor desconsiderado da rotina financeira.

Boas praticas:

- use `competence_date` para analise gerencial;
- use `due_date` para previsao de pagamentos e recebimentos;
- use `settled_at` apenas quando o dinheiro realmente entrou ou saiu;
- evite apagar historico financeiro; prefira cancelamento quando fizer sentido.

## 11. Tutorial: acompanhar contas a pagar

Contas a pagar sao uma visao filtrada dos lancamentos de saida. Elas ajudam a empresa a saber o que precisa pagar, o que esta vencendo e o que ja foi liquidado.

Passo a passo:

1. Acesse A pagar.
2. Revise lancamentos pendentes.
3. Verifique datas de vencimento.
4. Abra o lancamento quando precisar corrigir informacoes.
5. Marque como liquidado quando o pagamento for concluido.

Rotina recomendada:

- olhar vencimentos da semana;
- priorizar contas vencidas ou proximas do vencimento;
- conferir se pagamentos liquidados aparecem corretamente no saldo;
- manter despesas recorrentes simples registradas manualmente no MVP.

## 12. Tutorial: acompanhar contas a receber

Contas a receber sao uma visao filtrada dos lancamentos de entrada. Elas mostram valores que a empresa espera receber e ajudam a acompanhar atrasos.

Passo a passo:

1. Acesse A receber.
2. Revise recebimentos pendentes.
3. Confira vencimentos.
4. Atualize o lancamento quando o pagamento for recebido.
5. Marque como liquidado para refletir o valor no caixa realizado.

Rotina recomendada:

- revisar recebimentos pendentes diariamente;
- separar o que esta previsto do que ja foi recebido;
- manter descricoes claras para facilitar busca;
- registrar o recebimento somente quando o dinheiro estiver confirmado.

## 13. Tutorial: importar planilhas CSV/XLSX

A importacao e o principal caminho para migrar empresas que ja possuem controles em Excel, Google Sheets ou arquivos CSV.

Antes de importar:

- o arquivo deve ter no maximo 5 MB;
- as categorias usadas na planilha devem existir no sistema;
- valores monetarios devem estar em formato claro;
- a planilha deve representar lancamentos financeiros;
- contatos, clientes ou fornecedores devem ser mapeados como nome da contraparte, nao como cadastro separado.

Fluxo recomendado:

1. Acesse Importacao.
2. Envie o arquivo CSV ou XLSX.
3. Revise a pre-visualizacao.
4. Mapeie colunas da planilha para campos do sistema.
5. Corrija erros apontados pela validacao.
6. Confirme a importacao.
7. Revise os lancamentos criados.

Exemplo de colunas uteis em uma planilha:

```text
descricao,tipo,valor,categoria,vencimento,competencia,status,contraparte
Venda balcao,entrada,250.00,Vendas,2026-06-10,2026-06-01,settled,Cliente avulso
Aluguel,saida,1800.00,Aluguel,2026-06-05,2026-06-01,pending,Imobiliaria
```

Observacao: a importacao nao cria categorias automaticamente. Isso evita bagunca no plano de categorias e preserva controle da empresa sobre sua organizacao financeira.

## 14. Tutorial: exportar lancamentos em CSV

A exportacao CSV permite retirar os lancamentos do sistema para analise externa, backup operacional ou conferencia.

Passo a passo:

1. Acesse Lancamentos.
2. Aplique filtros, se necessario.
3. Use a opcao de exportacao CSV.
4. Baixe o arquivo `lancamentos-financeiros.csv`.
5. Abra em uma planilha apenas para conferencia ou analise complementar.

A exportacao deve respeitar os filtros da empresa autenticada e nao deve incluir dados de outras empresas.

## 15. Tutorial: renovar acesso de uma empresa

Este fluxo e exclusivo para `platform_admin`.

Quando uma assinatura vence:

- o cliente continua conseguindo fazer login;
- o acesso financeiro fica bloqueado;
- o status pode ir para `pending_payment`;
- a renovacao acontece manualmente apos pagamento confirmado fora da plataforma.

Passo a passo do administrador:

1. Acesse a area de administracao da plataforma.
2. Abra a visao de clientes ou assinaturas.
3. Localize a empresa.
4. Registre o pagamento manual.
5. Confirme a renovacao.
6. Verifique a nova data de acesso.

Regra de negocio:

- se a assinatura ainda estiver ativa, a renovacao soma novo periodo ao vencimento atual;
- se a assinatura estiver vencida, o novo periodo conta a partir da data de pagamento ou confirmacao;
- toda renovacao manual deve gerar historico em `manual_payments`.

---

## 16. Perfis de usuario

### Administrador da empresa

O primeiro usuario criado no cadastro self-service se torna administrador da empresa. Ele pode configurar a empresa, cadastrar categorias, gerenciar lancamentos, importar planilhas, acompanhar o dashboard e acessar as visoes financeiras.

### Usuario comum da empresa

Usuario voltado para operacao financeira limitada conforme regras atuais do produto. Ele acessa somente as funcionalidades permitidas para sua rotina, sempre dentro da empresa autenticada.

### Administrador da plataforma

Perfil interno usado para operar planos, clientes, assinaturas e pagamentos manuais. Esse usuario nao e criado por cadastro publico.

## 17. Regras importantes de seguranca e negocio

### Isolamento por empresa

Toda operacao financeira deve usar a empresa da sessao autenticada. O usuario comum nunca e fonte confiavel para informar `company_id`.

### Assinatura

Status usados no MVP:

- `trialing`: periodo gratuito ativo;
- `active`: assinatura paga ativa;
- `pending_payment`: trial ou assinatura vencida aguardando pagamento;
- `canceled`: cancelamento manual;
- `blocked`: bloqueio administrativo.

Nao existe status `expired` no MVP.

### Dinheiro

Valores monetarios devem usar `Decimal` no backend e `NUMERIC(14,2)` ou `DECIMAL(14,2)` no banco de dados. A API deve preferir dinheiro como string no JSON.

### Historico financeiro

O produto deve evitar exclusao fisica de lancamentos. Quando houver necessidade de remover impacto financeiro, a preferencia e usar cancelamento ou soft delete, mantendo rastreabilidade.

---

## 18. Roteiro de demonstracao para cliente

Use este roteiro em apresentacoes comerciais ou validacoes com usuarios iniciais.

1. Apresente o problema: planilhas dispersas, pouca visibilidade e dificuldade de acompanhar vencimentos.
2. Mostre o cadastro self-service e explique o trial de 30 dias.
3. Conclua o onboarding com nome da empresa e saldo inicial.
4. Cadastre tres categorias simples: Vendas, Aluguel e Fornecedores.
5. Crie uma entrada liquidada.
6. Crie uma saida pendente com vencimento proximo.
7. Abra o dashboard e mostre o impacto nos indicadores.
8. Abra A pagar e destaque a conta pendente.
9. Abra A receber e mostre a visao de entradas previstas.
10. Importe uma planilha pequena de exemplo.
11. Exporte os lancamentos em CSV.
12. Simule o bloqueio por assinatura vencida e explique que o login permanece disponivel.
13. Mostre a renovacao manual pelo `platform_admin`.

Mensagem central da demonstracao: o produto organiza a rotina financeira essencial sem exigir implantacao pesada.

## 19. Criterios de sucesso do MVP

O MVP sera considerado bem-sucedido se clientes iniciais conseguirem:

- criar conta sem suporte tecnico;
- entender o painel inicial em poucos minutos;
- cadastrar categorias e lancamentos sem treinamento longo;
- acompanhar contas a pagar e receber;
- importar uma planilha simples com seguranca;
- exportar seus dados em CSV;
- perceber mais clareza do caixa em comparacao com a planilha anterior;
- renovar acesso manualmente com apoio do operador da plataforma.

## 20. Status atual do produto

O projeto ja possui base funcional com:

- backend FastAPI;
- frontend React/Vite;
- PostgreSQL via Docker Compose;
- migrations Alembic;
- autenticacao JWT;
- cadastro self-service;
- confirmacao de e-mail;
- trial e bloqueio por assinatura;
- renovacao manual por administrador;
- categorias;
- lancamentos;
- contas a pagar e receber;
- dashboard;
- importacao CSV/XLSX;
- exportacao CSV;
- area administrativa inicial.

Pontos que ainda merecem revisao antes de uso comercial amplo:

- revisao completa de UX com usuarios nao tecnicos;
- validacao de fluxos criticos em ambiente de producao;
- endurecimento de seguranca do frontend;
- revisao de textos e encoding da interface;
- acompanhamento de logs sem exposicao de dados sensiveis;
- politica operacional de backup e restore do banco;
- revisao final de isolamento multiempresa.

---

## 21. Ambientes de demonstracao

Ambiente publicado para demonstracao e testes:

- Frontend: https://gestao-financeira-web-bubas-software.vercel.app
- API: https://gestao-financeira-api-six.vercel.app
- Health check: https://gestao-financeira-api-six.vercel.app/health

Esse ambiente e destinado a demonstracao e validacao inicial. Nao deve receber clientes pagantes ou dados financeiros reais sem revisao operacional, seguranca, backup e monitoramento.

## 22. Anexo operacional para equipe tecnica

Embora este README seja uma apresentacao do produto, os comandos abaixo ajudam a equipe interna a subir o ambiente local.

Requisitos:

- Docker;
- Docker Compose;
- Git.

Preparar ambiente:

```bash
cp .env.example .env
```

Variaveis locais essenciais:

- `POSTGRES_PASSWORD`
- `DATABASE_URL`
- `JWT_SECRET_KEY`

Subir containers:

```bash
docker compose up --build
```

Aplicar migrations:

```bash
docker compose exec backend alembic upgrade head
```

Criar `platform_admin`:

```bash
docker compose exec backend python -m app.scripts.create_platform_admin --name "Nome Admin" --email admin@exemplo.com
```

O comando solicita a senha no terminal. Evite passar senha por argumento de linha de comando.

Servicos locais:

- Frontend: http://localhost:5173
- Backend: http://localhost:8000
- Health check: http://localhost:8000/health

Verificacoes uteis:

```bash
docker compose exec backend pytest
docker compose exec frontend npm test
docker compose exec frontend npm run build
```

## 23. Deploy de producao da API

O deploy de producao da API deve ser feito pelo GitHub Actions em
`.github/workflows/api-production-deploy.yml`. O objetivo do fluxo e impedir que
codigo novo chegue na Vercel antes de o banco receber as migrations Alembic.

Fluxo esperado ao fazer merge em `main`:

1. Rodar testes criticos do backend.
2. Puxar variaveis de producao do projeto Vercel da API.
3. Executar `alembic upgrade head` contra `MIGRATION_DATABASE_URL`.
4. Confirmar que o banco esta no head com `python -m app.scripts.check_alembic_head`.
5. Publicar a API com `vercel deploy --prod`, deixando o build Python rodar no ambiente da Vercel.

Secrets obrigatorios no GitHub:

- `VERCEL_TOKEN`
- `VERCEL_ORG_ID`
- `VERCEL_API_PROJECT_ID`
- `VERCEL_WEB_PROJECT_ID`

Variaveis obrigatorias no ambiente Production do projeto Vercel da API:

- `APP_ENV=production`
- `APP_DEBUG=false`
- `DATABASE_URL`
- `MIGRATION_DATABASE_URL`
- `JWT_SECRET_KEY`
- `CRON_SECRET`
- `BACKEND_CORS_ORIGINS=https://gestao-financeira-web-bubas-software.vercel.app`
- `FRONTEND_URL=https://gestao-financeira-web-bubas-software.vercel.app`

Regras operacionais:

- O arquivo `.env` continua sendo apenas para ambiente local.
- Nunca versionar segredos reais de producao.
- Nao fazer deploy manual da API sem antes executar `alembic upgrade head`.
- Desativar o auto-deploy Git da Vercel para o projeto da API em `main`; a API
  deve ser publicada apenas pelo workflow, para evitar corrida entre deploy e
  migration.
- Se uma migration falhar, o workflow deve parar antes de publicar a nova API.

O frontend de producao deve ser publicado pelo GitHub Actions em
`.github/workflows/frontend-production-deploy.yml`. O workflow valida os secrets
da Vercel, roda `npm test`, puxa as variaveis Production do projeto Vercel da
web, publica com `vercel deploy --prod` e entao aponta explicitamente o dominio
`gestao-financeira-web-bubas-software.vercel.app` para o deployment gerado.

Mudancas em `frontend/**` na `main` disparam o deploy da web. O workflow tambem
pode ser executado manualmente pelo GitHub Actions quando for necessario
republicar a interface sem alterar codigo.

Os comandos da Vercel no workflow da web devem rodar da raiz do repositorio,
pois o projeto Vercel `gestao-financeira-web` ja usa `frontend` como Root
Directory. Rodar a CLI dentro de `frontend` faz a Vercel procurar
`frontend/frontend`.

Depois do deploy da API, o workflow tambem aponta explicitamente os dominios
`gestao-financeira-api-six.vercel.app` e
`gestao-financeira-api-bubas-software.vercel.app` para o deployment recem-criado.
Isso evita pipeline verde publicando em um alias diferente do dominio usado pelo
frontend ou pelos usuarios.

## 24. Documentos de referencia

- `PROJECT_CONTEXT.md`: fonte de verdade do produto, escopo do MVP, regras de negocio e ordem geral de implementacao.
- `AGENTS.md`: instrucoes obrigatorias para agentes de IA e colaboradores automatizados.

Antes de qualquer mudanca relevante, consulte esses documentos para preservar foco, seguranca, isolamento por empresa e precisao monetaria.
