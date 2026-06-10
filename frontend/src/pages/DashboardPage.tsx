import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, X } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import type { Dashboard } from "../types";

function Metric({ label, value, tone = "neutral" }: { label: string; value: string; tone?: "neutral" | "good" | "bad" }) {
  const toneClass = tone === "good" ? "text-emerald-700" : tone === "bad" ? "text-rose-700" : "text-ink";
  return (
    <div className="metric">
      <p className="text-sm text-muted">{label}</p>
      <strong className={`mt-2 block text-2xl ${toneClass}`}>{value}</strong>
    </div>
  );
}

function alertText(daysUntilDue: number) {
  if (daysUntilDue < 0) return `${Math.abs(daysUntilDue)} dia(s) em atraso`;
  if (daysUntilDue === 0) return "Vence hoje";
  return `Vence em ${daysUntilDue} dia(s)`;
}

function DueAlertCard({
  alert,
  onDismiss,
}: {
  alert: Dashboard["due_alerts"][number];
  onDismiss: () => void;
}) {
  const toneClass = {
    yellow: "border-amber-300 bg-amber-50 text-amber-950",
    orange: "border-orange-300 bg-orange-50 text-orange-950",
    red: "border-rose-300 bg-rose-50 text-rose-950",
  }[alert.severity];
  const iconClass = {
    yellow: "text-amber-600",
    orange: "text-orange-600",
    red: "text-rose-600",
  }[alert.severity];

  return (
    <div className={`rounded-lg border p-4 shadow-sm ${toneClass}`}>
      <div className="flex items-start gap-3">
        <AlertTriangle className={`mt-0.5 h-5 w-5 shrink-0 ${iconClass}`} aria-hidden="true" />
        <div className="min-w-0 flex-1">
          <div className="flex flex-col gap-1 sm:flex-row sm:items-start sm:justify-between">
            <div>
              <p className="text-sm font-semibold">
                {alert.title}: {alert.description}
              </p>
              <p className="mt-1 text-xs font-medium">{alertText(alert.days_until_due)}</p>
            </div>
            <strong className="text-base font-semibold">{money(alert.amount)}</strong>
          </div>
          <div className="mt-3 grid gap-2 text-xs sm:grid-cols-3">
            <span>Data: {dateText(alert.due_date)}</span>
            <span>Contato: {alert.contact_name ?? "-"}</span>
            <span>Categoria: {alert.category_name ?? "-"}</span>
          </div>
        </div>
        <button className="icon-btn h-8 w-8 shrink-0" type="button" onClick={onDismiss} aria-label="Retirar alerta">
          <X className="h-4 w-4" aria-hidden="true" />
        </button>
      </div>
    </div>
  );
}

export function DashboardPage() {
  const [dismissedAlertIds, setDismissedAlertIds] = useState<Set<string>>(new Set());
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<Dashboard>("/reports/dashboard"),
    refetchInterval: 60_000,
  });

  if (dashboard.isLoading) return <div className="screen-state">Carregando dashboard...</div>;
  if (dashboard.isError) return <div className="alert-error">{dashboard.error.message}</div>;

  const data = dashboard.data!;
  const visibleAlerts = data.due_alerts.filter((alert) => !dismissedAlertIds.has(alert.transaction_id));

  return (
    <section className="space-y-6">
      <div>
        <h2 className="section-title">Resumo do mês atual</h2>
        <p className="section-subtitle">
          Período {dateText(data.period_start)} até {dateText(data.period_end)}
        </p>
      </div>

      {visibleAlerts.length > 0 && (
        <div className="space-y-3">
          {visibleAlerts.map((alert) => (
            <DueAlertCard
              key={alert.transaction_id}
              alert={alert}
              onDismiss={() => {
                setDismissedAlertIds((current) => {
                  const next = new Set(current);
                  next.add(alert.transaction_id);
                  return next;
                });
              }}
            />
          ))}
        </div>
      )}

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Metric label="Saldo atual" value={money(data.current_balance)} />
        <Metric label="Entradas do mês" value={money(data.month_income)} tone="good" />
        <Metric label="Saídas do mês" value={money(data.month_expense)} tone="bad" />
        <Metric label="Resultado do mês" value={money(data.month_result)} />
        <Metric label="Previsão fim do mês" value={money(data.month_end_balance_forecast)} />
      </div>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="panel">
          <h3 className="panel-title">Contas em aberto</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Metric label={`${data.open_payables.count} a pagar`} value={money(data.open_payables.total)} tone="bad" />
            <Metric label={`${data.open_receivables.count} a receber`} value={money(data.open_receivables.total)} tone="good" />
          </div>
        </div>
        <div className="panel">
          <h3 className="panel-title">Atrasos</h3>
          <div className="mt-4 grid gap-3 sm:grid-cols-2">
            <Metric label={`${data.overdue_payables.count} pagamentos`} value={money(data.overdue_payables.total)} tone="bad" />
            <Metric label={`${data.overdue_receivables.count} recebimentos`} value={money(data.overdue_receivables.total)} tone="good" />
          </div>
        </div>
      </div>
    </section>
  );
}
