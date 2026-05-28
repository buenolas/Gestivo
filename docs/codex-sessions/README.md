# Registro de Sessoes do Codex

Esta pasta deve guardar resumos operacionais das sessoes de trabalho com agentes de IA.

O objetivo e permitir que uma nova conversa consiga entender rapidamente:

- qual era o objetivo da sessao;
- quais arquivos foram alterados;
- quais decisoes foram tomadas;
- quais comandos foram executados;
- quais problemas ficaram pendentes;
- qual deve ser a proxima tarefa.

## Quando Criar Um Resumo

Crie um resumo ao final de toda sessao relevante, especialmente quando houver:

- mudanca de arquitetura;
- mudanca de regra de negocio;
- implementacao de funcionalidade;
- migracao de banco;
- alteracao de fluxo financeiro;
- ajuste de autenticacao, assinatura ou multiempresa;
- preparacao para deploy;
- decisoes de escopo.

## Nome Sugerido Dos Arquivos

Use nomes ordenaveis por data e numero de sessao:

```text
YYYY-MM-DD-sessao-N-titulo-curto.md
```

Exemplos:

```text
2026-05-27-sessao-1-auditoria-contexto.md
2026-05-28-sessao-2-higiene-deploy.md
2026-05-29-sessao-3-saldo-inicial.md
```

## Modelo De Resumo

Use este modelo como base:

````markdown
# Sessao N - Titulo Curto

Data: YYYY-MM-DD

## Objetivo

Descrever o objetivo principal da sessao.

## Escopo Executado

- Item executado 1.
- Item executado 2.
- Item executado 3.

## Arquivos Criados Ou Alterados

- `caminho/do/arquivo`: resumo da alteracao.

## Decisoes Tomadas

- Decisao 1.
- Decisao 2.

## Comandos Executados

```bash
comando executado
```

## Validacoes

- Teste, build ou verificacao realizada.

## Problemas Encontrados

- Problema 1.
- Problema 2.

## Pendencias

- Pendencia 1.
- Pendencia 2.

## Proxima Sessao Recomendada

Descrever a proxima tarefa recomendada.

## Cuidados Para A Proxima Sessao

- Ler `PROJECT_CONTEXT.md`.
- Ler `AGENTS.md`.
- Preservar escopo do MVP.
- Nao implementar funcionalidades futuras sem autorizacao.
````

## Regras Para Agentes

Antes de iniciar uma nova sessao, leia:

1. `PROJECT_CONTEXT.md`;
2. `AGENTS.md`;
3. `docs/ROADMAP_MVP_FINAL.md`;
4. o resumo de sessao mais recente nesta pasta, se existir.

O resumo de sessao nao substitui `PROJECT_CONTEXT.md` nem `AGENTS.md`; ele apenas registra o que
aconteceu em uma rodada especifica de trabalho.
