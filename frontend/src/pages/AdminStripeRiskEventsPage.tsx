import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { AlertCircle, Check, RefreshCw, ShieldAlert } from "lucide-react";
import { apiFetch } from "../api";
import type { StripeRiskEvent } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

type ReviewStatus = StripeRiskEvent["review_status"];

const statusLabels: Record<ReviewStatus, string> = {
  open: "Pendentes",
  reviewed: "Revisados",
};

const eventLabels: Record<StripeRiskEvent["event_type"], string> = {
  "charge.refunded": "Reembolso registrado",
  "charge.dispute.created": "Disputa aberta pelo cliente",
  "radar.early_fraud_warning.created": "Alerta antecipado de fraude",
};

function dateTimeText(value: string) {
  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return value;
  return new Intl.DateTimeFormat("pt-BR", {
    dateStyle: "short",
    timeStyle: "short",
  }).format(date);
}

export function AdminStripeRiskEventsPage() {
  const queryClient = useQueryClient();
  const [reviewStatus, setReviewStatus] = useState<ReviewStatus>("open");
  const events = useQuery({
    queryKey: ["admin-stripe-risk-events", reviewStatus],
    queryFn: () =>
      apiFetch<StripeRiskEvent[]>(`/admin/stripe/risk-events?review_status=${reviewStatus}`),
  });
  const markReviewed = useMutation({
    mutationFn: (eventId: string) =>
      apiFetch<StripeRiskEvent>(`/admin/stripe/risk-events/${eventId}/reviewed`, {
        method: "PATCH",
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["admin-stripe-risk-events"] });
    },
  });

  return (
    <section className="space-y-5">
      <div className="flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="section-title">Alertas Stripe</h2>
          <p className="section-subtitle">
            Revise reembolsos, disputas e alertas de fraude recebidos pelo webhook.
          </p>
        </div>
        <Button
          className="w-full sm:w-auto"
          disabled={events.isFetching}
          onClick={() => void events.refetch()}
          variant="secondary"
        >
          <RefreshCw className={`h-4 w-4 ${events.isFetching ? "animate-spin" : ""}`} />
          Atualizar
        </Button>
      </div>

      <div className="panel flex flex-col gap-3 sm:flex-row sm:items-start">
        <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-amber-50 text-amber-700">
          <ShieldAlert className="h-5 w-5" aria-hidden="true" />
        </span>
        <div className="space-y-1">
          <h3 className="font-semibold text-ink">Revisão manual</h3>
          <p className="text-sm leading-6 text-muted">
            Os alertas ficam registrados para análise. O recebimento não bloqueia a empresa nem
            executa reembolsos automaticamente.
          </p>
        </div>
      </div>

      <div className="flex flex-wrap gap-2" aria-label="Status dos alertas" role="group">
        {(["open", "reviewed"] as const).map((status) => (
          <Button
            key={status}
            aria-pressed={reviewStatus === status}
            onClick={() => setReviewStatus(status)}
            type="button"
            variant={reviewStatus === status ? "default" : "secondary"}
          >
            {statusLabels[status]}
          </Button>
        ))}
      </div>

      {events.isError && (
        <div className="alert-error" role="alert">
          <p>{events.error.message}</p>
          <button className="mt-2 font-semibold underline" onClick={() => void events.refetch()}>
            Tentar novamente
          </button>
        </div>
      )}

      {events.isLoading ? (
        <div className="screen-state" role="status">Carregando alertas...</div>
      ) : events.isError && !events.data ? (
        null
      ) : events.data?.length === 0 ? (
        <div className="panel flex flex-col items-center gap-2 py-12 text-center">
          <span className="flex h-11 w-11 items-center justify-center rounded-full bg-mint text-accent">
            {reviewStatus === "open" ? (
              <Check className="h-5 w-5" aria-hidden="true" />
            ) : (
              <AlertCircle className="h-5 w-5" aria-hidden="true" />
            )}
          </span>
          <h3 className="font-semibold text-ink">
            {reviewStatus === "open" ? "Nenhum alerta pendente" : "Nenhum alerta revisado"}
          </h3>
          <p className="text-sm text-muted">
            {reviewStatus === "open"
              ? "Quando a Stripe enviar um reembolso, disputa ou alerta de fraude, ele aparecerá aqui."
              : "Os alertas marcados como revisados aparecerão aqui."}
          </p>
        </div>
      ) : (
        <div className="space-y-3" aria-live="polite">
          {events.data?.map((event) => (
            <article className="panel space-y-4" key={event.event_id}>
              <div className="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                <div className="min-w-0 space-y-2">
                  <div className="flex flex-wrap items-center gap-2">
                    <h3 className="font-semibold text-ink">{eventLabels[event.event_type]}</h3>
                    <Badge variant={event.review_status === "open" ? "warning" : "success"}>
                      {event.review_status === "open" ? "Pendente" : "Revisado"}
                    </Badge>
                  </div>
                  <p className="text-sm text-muted">
                    Evento em {dateTimeText(event.event_created_at)} · recebido no Gestivo em{" "}
                    {dateTimeText(event.received_at)}
                  </p>
                </div>
                {event.review_status === "open" && (
                  <Button
                    className="w-full shrink-0 sm:w-auto"
                    disabled={markReviewed.isPending}
                    onClick={() => markReviewed.mutate(event.event_id)}
                    variant="secondary"
                  >
                    <Check className="h-4 w-4" aria-hidden="true" />
                    {markReviewed.isPending ? "Salvando..." : "Marcar como revisado"}
                  </Button>
                )}
              </div>

              <dl className="grid gap-3 rounded-lg border border-line bg-panel p-3 text-sm sm:grid-cols-2">
                <div className="min-w-0 space-y-1">
                  <dt className="text-muted">Empresa</dt>
                  <dd className="break-words font-medium text-ink">
                    {event.company_name ?? "Empresa não identificada"}
                  </dd>
                </div>
                <div className="min-w-0 space-y-1">
                  <dt className="text-muted">Cobrança Stripe</dt>
                  <dd className="break-all font-mono text-xs text-ink">
                    {event.stripe_charge_id ?? "ID indisponível"}
                  </dd>
                </div>
                <div className="min-w-0 space-y-1 sm:col-span-2">
                  <dt className="text-muted">ID do evento</dt>
                  <dd className="break-all font-mono text-xs text-ink">{event.event_id}</dd>
                </div>
              </dl>

              {markReviewed.isError && markReviewed.variables === event.event_id && (
                <div className="alert-error" role="alert">{markReviewed.error.message}</div>
              )}
            </article>
          ))}
        </div>
      )}
    </section>
  );
}
