import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, ArrowDownRight, ArrowUpRight, CalendarDays, TrendingUp, Wallet, X } from "lucide-react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { apiFetch } from "../api";
import { dateText, money, paymentMethodText } from "../format";
import type { Dashboard } from "../types";

function toNumber(value: string | number | null | undefined) {
  if (value === null || value === undefined) return 0;
  return Number(value);
}

function compactMoney(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function Metric({
  icon: Icon,
  label,
  value,
  detail,
  tone = "neutral",
}: {
  icon: typeof Wallet;
  label: string;
  value: string;
  detail?: string;
  tone?: "neutral" | "good" | "bad";
}) {
  const toneClass =
    tone === "good"
      ?"bg-emerald-50 text-emerald-700"
      : tone === "bad"
        ?"bg-rose-50 text-rose-700"
        : "bg-mint text-brand";

  return (
    <div className="metric group">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <strong className="mt-3 block text-2xl font-bold tracking-tight text-ink">{value}</strong>
          {detail && <span className="mt-2 block text-xs font-medium text-muted">{detail}</span>}
        </div>
        <span className={`rounded-md p-2 transition group-hover:scale-105 ${toneClass}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
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
    yellow: "border-amber-200 bg-amber-50 text-amber-950",
    orange: "border-orange-200 bg-orange-50 text-orange-950",
    red: "border-rose-200 bg-rose-50 text-rose-950",
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

  const chartData = useMemo(() => {
    if (!dashboard.data) return [];
    const data = dashboard.data;
    const startBalance = toNumber(data.current_balance) - toNumber(data.month_result);
    return [
      { label: "Início", saldo: startBalance },
      { label: "Entradas", saldo: startBalance + toNumber(data.month_income) },
      { label: "Saídas", saldo: startBalance + toNumber(data.month_result) },
      { label: "Previsto", saldo: toNumber(data.month_end_balance_forecast) },
    ];
  }, [dashboard.data]);

  if (dashboard.isLoading) return <div className="screen-state">Carregando dashboard...</div>;
  if (dashboard.isError) return <div className="alert-error">{dashboard.error.message}</div>;

  const data = dashboard.data!;
  const visibleAlerts = data.due_alerts.filter((alert) => !dismissedAlertIds.has(alert.transaction_id));

  return (
    <section className="space-y-6">
      <div className="flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Resumo executivo</p>
          <h2 className="section-title">Visão financeira do mês</h2>
          <p className="section-subtitle">
            Período {dateText(data.period_start)} até {dateText(data.period_end)}
          </p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-muted shadow-sm">
          <CalendarDays className="h-4 w-4 text-accent" />
          Atualizado automaticamente
        </div>
      </div>

      <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-5">
        <Metric icon={Wallet} label="Caixa realizado" value={money(data.current_balance)} detail="Saldo com liquidados" />
        <Metric icon={ArrowUpRight} label="Entradas realizadas" value={money(data.month_income)} detail="Liquidadas no mês" tone="good" />
        <Metric icon={ArrowDownRight} label="Saídas realizadas" value={money(data.month_expense)} detail="Liquidadas no mês" tone="bad" />
        <Metric icon={TrendingUp} label="Resultado realizado" value={money(data.month_result)} detail="Entradas menos saídas" />
        <Metric icon={Wallet} label="Previsão" value={money(data.month_end_balance_forecast)} detail="Fim do mês" />
      </div>

      <div className="grid gap-4 xl:grid-cols-[1.45fr_0.9fr]">
        <div className="panel min-h-[360px]">
          <div className="mb-6 flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
            <div>
              <h3 className="panel-title">Evolução de caixa</h3>
              <p className="mt-1 text-sm text-muted">Leitura visual baseada nos totais consolidados do mês.</p>
            </div>
            <span className="rounded-md bg-mint px-3 py-1 text-xs font-semibold text-brand">
              {money(data.month_end_balance_forecast)}
            </span>
          </div>
          <div className="h-64">
            <ResponsiveContainer height="100%" width="100%">
              <AreaChart data={chartData} margin={{ left: 0, right: 12, top: 12, bottom: 0 }}>
                <CartesianGrid stroke="#E2E8F0" strokeDasharray="4 4" vertical={false} />
                <XAxis axisLine={false} dataKey="label" tickLine={false} tick={{ fill: "#64748B", fontSize: 12 }} />
                <YAxis
                  axisLine={false}
                  tickFormatter={(value) => compactMoney(Number(value))}
                  tickLine={false}
                  tick={{ fill: "#64748B", fontSize: 12 }}
                  width={72}
                />
                <Tooltip
                  formatter={(value) => compactMoney(Number(value))}
                  contentStyle={{ borderRadius: 8, border: "1px solid #E2E8F0", boxShadow: "0 16px 40px rgba(15, 23, 42, 0.12)" }}
                />
                <Area dataKey="saldo" fill="#DDF7EC" stroke="#10B981" strokeWidth={3} type="monotone" />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="panel">
          <h3 className="panel-title">Operação em aberto</h3>
          <p className="mt-1 text-sm text-muted">Compromissos e recebimentos ainda pendentes.</p>
          <div className="mt-5 space-y-3">
            <Metric icon={ArrowDownRight} label={`${data.open_payables.count} a pagar`} value={money(data.open_payables.total)} tone="bad" />
            <Metric icon={ArrowUpRight} label={`${data.open_receivables.count} a receber`} value={money(data.open_receivables.total)} tone="good" />
            <Metric icon={AlertTriangle} label={`${data.overdue_payables.count + data.overdue_receivables.count} atrasos`} value={money(toNumber(data.overdue_payables.total) + toNumber(data.overdue_receivables.total))} tone="bad" />
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="mb-5">
          <h3 className="panel-title">Movimentações por forma</h3>
          <p className="mt-1 text-sm text-muted">Entradas e saídas liquidadas no mês atual.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.payment_methods.map((item) => (
            <div className="metric" key={item.payment_method}>
              <div className="flex items-start justify-between gap-3">
                <div>
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">{item.label || paymentMethodText(item.payment_method)}</p>
                  <strong className="mt-3 block text-xl font-bold tracking-tight text-ink">{money(item.net_total)}</strong>
                  <span className="mt-2 block text-xs font-medium text-muted">{item.count} movimentação(ões)</span>
                </div>
                <span className="rounded-md bg-mint px-2 py-1 text-xs font-semibold text-brand">
                  {paymentMethodText(item.payment_method)}
                </span>
              </div>
              <div className="mt-4 grid grid-cols-2 gap-2 text-xs font-semibold text-muted">
                <span>Entradas: {money(item.income_total)}</span>
                <span>Saídas: {money(item.expense_total)}</span>
              </div>
            </div>
          ))}
        </div>
      </div>

      {visibleAlerts.length > 0 && (
        <div className="panel space-y-3">
          <div>
            <h3 className="panel-title">Alertas de vencimento</h3>
            <p className="mt-1 text-sm text-muted">Itens críticos para acompanhar nos próximos dias.</p>
          </div>
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
    </section>
  );
}
