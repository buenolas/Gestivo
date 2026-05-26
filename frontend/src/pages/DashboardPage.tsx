import { useQuery } from "@tanstack/react-query";
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

export function DashboardPage() {
  const dashboard = useQuery({
    queryKey: ["dashboard"],
    queryFn: () => apiFetch<Dashboard>("/reports/dashboard"),
  });

  if (dashboard.isLoading) return <div className="screen-state">Carregando dashboard...</div>;
  if (dashboard.isError) return <div className="alert-error">{dashboard.error.message}</div>;

  const data = dashboard.data!;

  return (
    <section className="space-y-6">
      <div>
        <h2 className="section-title">Resumo do mês atual</h2>
        <p className="section-subtitle">
          Período {dateText(data.period_start)} até {dateText(data.period_end)}
        </p>
      </div>

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
