import { type FormEvent, type KeyboardEvent, useEffect, useRef, useState } from "react";
import { Bot, Loader2, MessageSquareText, Plus, Send, ShieldCheck, Sparkles, UserRound } from "lucide-react";
import { useQuery, useQueryClient } from "@tanstack/react-query";

import { Button } from "@/components/ui/button";
import { apiFetch } from "../api";
import type { Subscription } from "../types";

type Message = {
  role: "user" | "assistant";
  content: string;
};

type FinancialAssistantResponse = {
  answer: string;
};

const suggestions = [
  "Como foi o resultado financeiro deste mês?",
  "Quais foram as maiores despesas do mês?",
  "O que está pendente para pagar ou receber?",
];

function formatAssistantMessage(content: string) {
  return content.split(/(\*\*[\s\S]+?\*\*)/g).map((part, index) => {
    if (!part.startsWith("**") || !part.endsWith("**")) return part;

    return (
      <strong className="font-semibold text-ink" key={index}>
        {part.slice(2, -2)}
      </strong>
    );
  });
}

export function FinancialAssistantPage() {
  const queryClient = useQueryClient();
  const subscription = useQuery({
    queryKey: ["subscription-status"],
    queryFn: () => apiFetch<Subscription>("/subscription/status"),
  });
  const [messages, setMessages] = useState<Message[]>([]);
  const [draft, setDraft] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement | null>(null);
  const endOfMessagesRef = useRef<HTMLDivElement | null>(null);
  const dailyLimit = subscription.data?.ai_daily_limit ?? null;
  const usedToday = subscription.data?.ai_interactions_used_today ?? 0;
  const assistantIncluded = subscription.data?.feature_codes?.includes("assistant") ?? true;
  const limitReached = dailyLimit !== null && usedToday >= dailyLimit;

  useEffect(() => {
    endOfMessagesRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages, isSending]);

  async function sendMessage(content: string) {
    const normalizedContent = content.trim();
    if (!normalizedContent || isSending || limitReached || !assistantIncluded) return;

    const nextMessages = [...messages, { role: "user" as const, content: normalizedContent }];
    setMessages(nextMessages);
    setDraft("");
    setError(null);
    setIsSending(true);

    try {
      const response = await apiFetch<FinancialAssistantResponse>("/assistant/chat", {
        method: "POST",
        body: JSON.stringify({ messages: nextMessages.slice(-12) }),
      });
      setMessages([...nextMessages, { role: "assistant", content: response.answer }]);
      await queryClient.invalidateQueries({ queryKey: ["subscription-status"] });
    } catch (requestError) {
      setError(
        requestError instanceof Error
          ? requestError.message
          : "Não foi possível obter uma resposta. Tente novamente.",
      );
      await queryClient.invalidateQueries({ queryKey: ["subscription-status"] });
    } finally {
      setIsSending(false);
      inputRef.current?.focus();
    }
  }

  function handleSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    void sendMessage(draft);
  }

  function handleInputKeyDown(event: KeyboardEvent<HTMLTextAreaElement>) {
    if (event.key === "Enter" && !event.shiftKey && !event.nativeEvent.isComposing) {
      event.preventDefault();
      void sendMessage(draft);
    }
  }

  return (
    <section className="space-y-5">
      <div className="panel space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div className="flex min-w-0 items-start gap-3">
            <div className="rounded-md bg-mint p-3 text-accent">
              <Sparkles className="h-5 w-5" aria-hidden="true" />
            </div>
            <div className="min-w-0">
              <h2 className="text-xl font-bold text-ink">Assistente financeiro</h2>
              <p className="mt-1 max-w-2xl text-sm leading-6 text-muted">
                Pergunte sobre entradas, saídas, vencimentos e resultados. Você também pode pedir um resumo textual de um período.
              </p>
            </div>
          </div>
          <Button
            className="shrink-0"
            disabled={messages.length === 0 || isSending}
            onClick={() => {
              setMessages([]);
              setError(null);
              setDraft("");
              inputRef.current?.focus();
            }}
            type="button"
            variant="secondary"
          >
            <Plus className="h-4 w-4" aria-hidden="true" />
            Nova conversa
          </Button>
        </div>

        {subscription.data && assistantIncluded && (
          <div className="flex flex-wrap items-center justify-between gap-2 rounded-md border border-line bg-panel px-3 py-2 text-sm">
            <span className="font-medium text-ink">Uso da IA hoje</span>
            <span className="text-muted">
              {dailyLimit === null
                ? `${usedToday} interações · sem limite diário`
                : `${Math.min(usedToday, dailyLimit)} de ${dailyLimit} interações`}
            </span>
          </div>
        )}

        {subscription.data && !assistantIncluded && (
          <div className="alert-error" role="status">
            O plano atual não inclui o assistente financeiro. Escolha um plano com acesso à IA para continuar.
          </div>
        )}
        {assistantIncluded && limitReached && dailyLimit !== null && dailyLimit > 0 && (
          <div className="rounded-md border border-amber-200 bg-amber-50 px-3 py-2 text-sm text-amber-900" role="status">
            Você atingiu o limite diário de {dailyLimit} interações. O limite será renovado amanhã.
          </div>
        )}

        <div className="rounded-md border border-accent/25 bg-mint/30 px-3.5 py-3">
          <div className="flex items-center gap-2">
            <ShieldCheck className="h-5 w-5 shrink-0 text-accent" aria-hidden="true" />
            <p className="text-sm font-semibold text-ink">Privacidade e segurança dos dados</p>
          </div>
          <div className="mt-1.5 space-y-2 pl-7 text-sm leading-6 text-muted">
            <p>
              Os lançamentos continuam armazenados no Gestivo para o funcionamento do sistema.{" "}
              <strong className="font-semibold text-ink">
                O conteúdo das perguntas, respostas e do histórico não é gravado no banco. Registramos apenas a quantidade de interações diárias para aplicar o limite do plano.
              </strong>{" "}
              O histórico fica apenas na memória desta tela e desaparece quando você atualiza a página ou sai dela.
            </p>
            <p>
              Para responder, enviamos à OpenAI sua pergunta, o contexto recente do chat e os dados financeiros consultados. A solicitação não é mantida como histórico persistente na API.{" "}
              <strong className="font-semibold text-ink">
                Ainda assim, por padrão, a OpenAI pode reter conteúdo em logs de segurança por até 30 dias.
              </strong>{" "}
              Os dados enviados pela API não são usados para treinar modelos por padrão.
            </p>
            <a
              className="inline-block font-medium text-accent underline underline-offset-2"
              href="https://developers.openai.com/api/docs/guides/your-data"
              rel="noopener noreferrer"
              target="_blank"
            >
              Consulte os controles de dados da API da OpenAI
            </a>
          </div>
        </div>
      </div>

      <div className="panel flex min-h-[32rem] flex-col overflow-hidden p-0 sm:min-h-[38rem]">
        <div className="min-h-0 flex-1 space-y-5 overflow-y-auto p-4 sm:p-6" aria-live="polite" role="log" aria-label="Conversa com o assistente financeiro">
          {messages.length === 0 ? (
            <div className="mx-auto flex min-h-[25rem] max-w-3xl flex-col justify-center">
              <div className="mb-6 text-center">
                <div className="mx-auto mb-3 flex h-12 w-12 items-center justify-center rounded-full bg-mint text-accent">
                  <MessageSquareText className="h-6 w-6" aria-hidden="true" />
                </div>
                <h3 className="text-lg font-bold text-ink">O que você quer entender sobre o seu financeiro?</h3>
                <p className="mt-2 text-sm text-muted">Escolha uma pergunta para começar ou escreva a sua.</p>
              </div>
              <div className="grid gap-2 sm:grid-cols-3">
                {suggestions.map((suggestion) => (
                  <button
                    key={suggestion}
                    className="rounded-md border border-line bg-white p-3 text-left text-sm font-medium text-ink transition hover:border-accent/40 hover:bg-panel focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30 disabled:opacity-60"
                    disabled={isSending || limitReached || !assistantIncluded}
                    onClick={() => void sendMessage(suggestion)}
                    type="button"
                  >
                    {suggestion}
                  </button>
                ))}
              </div>
            </div>
          ) : (
            messages.map((message, index) => (
              <div
                key={`${message.role}-${index}`}
                className={`flex gap-3 ${message.role === "user" ? "justify-end" : "justify-start"}`}
              >
                {message.role === "assistant" && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mint text-accent">
                    <Bot className="h-4 w-4" aria-hidden="true" />
                  </div>
                )}
                <div
                  className={`max-w-[90%] rounded-lg px-4 py-3 text-sm leading-6 sm:max-w-[48rem] ${
                    message.role === "user"
                      ? "bg-brand text-white"
                      : "border border-line bg-panel/60 text-ink"
                  }`}
                >
                  <p className="whitespace-pre-wrap break-words">
                    {message.role === "assistant"
                      ? formatAssistantMessage(message.content)
                      : message.content}
                  </p>
                </div>
                {message.role === "user" && (
                  <div className="mt-1 flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-brand/10 text-brand">
                    <UserRound className="h-4 w-4" aria-hidden="true" />
                  </div>
                )}
              </div>
            ))
          )}

          {isSending && (
            <div className="flex items-center gap-3 text-sm text-muted" role="status">
              <div className="flex h-8 w-8 shrink-0 items-center justify-center rounded-full bg-mint text-accent">
                <Bot className="h-4 w-4" aria-hidden="true" />
              </div>
              <div className="flex items-center gap-2 rounded-lg border border-line bg-panel/60 px-4 py-3">
                <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" />
                Consultando os dados financeiros…
              </div>
            </div>
          )}

          {error && <div className="alert-error ml-11 max-w-2xl" role="alert">{error}</div>}
          <div ref={endOfMessagesRef} />
        </div>

        <form className="border-t border-line bg-white p-3 sm:p-4" onSubmit={handleSubmit}>
          <div className="flex items-end gap-2">
            <label className="sr-only" htmlFor="financial-assistant-message">Sua pergunta</label>
            <textarea
              ref={inputRef}
              id="financial-assistant-message"
              className="min-h-11 max-h-36 min-w-0 flex-1 resize-y rounded-md border border-line bg-white px-3 py-2.5 text-sm text-ink outline-none transition placeholder:text-muted/70 focus:border-accent focus:ring-2 focus:ring-accent/15"
              disabled={isSending || limitReached || !assistantIncluded}
              maxLength={3000}
              onChange={(event) => setDraft(event.target.value)}
              onKeyDown={handleInputKeyDown}
              placeholder="Ex.: Como ficaram minhas entradas e saídas no último mês?"
              rows={1}
              value={draft}
            />
            <Button aria-label="Enviar pergunta" disabled={!draft.trim() || isSending || limitReached || !assistantIncluded} size="icon" type="submit">
              {isSending ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
            </Button>
          </div>
          <p className="mt-2 text-right text-[11px] text-muted">Enter envia · Shift+Enter quebra a linha</p>
        </form>
      </div>
    </section>
  );
}
