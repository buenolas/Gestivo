import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import {
  AlertTriangle,
  ArrowDownRight,
  ArrowUpRight,
  BarChart3,
  CalendarDays,
  Check,
  ChevronDown,
  TrendingUp,
  Wallet,
  X,
} from "lucide-react";
import {
  Bar,
  BarChart,
  CartesianGrid,
  ComposedChart,
  Legend,
  Line,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { apiFetch } from "../api";
import { dateText, money, paymentMethodText } from "../format";
import type { Dashboard } from "../types";

const periods = [
  { value: "month", label: "1 mês", months: 1 },
  { value: "3m", label: "3 meses", months: 3 },
  { value: "6m", label: "6 meses", months: 6 },
  { value: "12m", label: "1 ano", months: 12 },
  { value: "all", label: "Todo o histórico", months: null },
] as const;

type Period = (typeof periods)[number]["value"];

function currentMonthValue() {
  const now = new Date();
  return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}`;
}

function todayValue() {
  return dateInputValue(new Date());
}

function dateInputValue(value: Date) {
  return `${value.getFullYear()}-${String(value.getMonth() + 1).padStart(2, "0")}-${String(value.getDate()).padStart(2, "0")}`;
}

function defaultComparisonRange(period: Period, month: string) {
  const months = periods.find((item) => item.value === period)?.months;
  if (!months) return { start: "", end: "" };

  const [year, monthNumber] = month.split("-").map(Number);
  if (!year || !monthNumber) return { start: "", end: "" };

  const selectedStart = new Date(year, monthNumber - months, 1);
  const previousEnd = new Date(selectedStart.getFullYear(), selectedStart.getMonth(), 0);
  const previousStart = new Date(
    previousEnd.getFullYear(),
    previousEnd.getMonth() - months + 1,
    1,
  );
  return { start: dateInputValue(previousStart), end: dateInputValue(previousEnd) };
}

function chartDateLabel(value: string, granularity: Dashboard["trend_granularity"]) {
  const date = new Date(`${value}T12:00:00`);
  return new Intl.DateTimeFormat("pt-BR", {
    day: granularity === "day" ? "2-digit" : undefined,
    month: granularity === "day" ? undefined : "short",
    year: granularity === "month" ? "2-digit" : undefined,
  }).format(date);
}

function compactMoney(value: number) {
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
    maximumFractionDigits: 0,
  }).format(value);
}

function chartMoney(value: unknown) {
  return money(typeof value === "number" || typeof value === "string" ? value : 0);
}

function changeLabel(amount: string, percent: string | null) {
  const amountValue = Number(amount);
  const amountText = `${amountValue > 0 ? "+" : ""}${money(amount)}`;
  const percentText = percent === null
    ? "sem base no período comparado"
    : `${Number(percent) > 0 ? "+" : ""}${new Intl.NumberFormat("pt-BR", {
        maximumFractionDigits: 1,
      }).format(Number(percent))}%`;
  return `${amountText} · ${percentText}`;
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
      ? "bg-emerald-50 text-emerald-700"
      : tone === "bad"
        ? "bg-rose-50 text-rose-700"
        : "bg-mint text-brand";

  return (
    <div className="metric group min-w-0">
      <div className="flex items-start justify-between gap-3">
        <div className="min-w-0">
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <strong className="mt-3 block break-words text-2xl font-bold tracking-tight text-ink">{value}</strong>
          {detail && <span className="mt-2 block text-xs font-medium text-muted">{detail}</span>}
        </div>
        <span className={`rounded-md p-2 transition-transform duration-150 group-hover:scale-105 ${toneClass}`}>
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

function CategoryChart({
  title,
  data,
  color,
}: {
  title: string;
  data: Dashboard["category_totals"];
  color: string;
}) {
  const chartData = data.slice(0, 6).map((item) => ({
    ...item,
    chartTotal: Number(item.total),
  }));

  return (
    <div className="panel min-w-0">
      <div className="mb-4">
        <h3 className="panel-title">{title}</h3>
        <p className="mt-1 text-sm text-muted">Categorias com maior valor liquidado no período.</p>
      </div>
      {chartData.length === 0 ? (
        <div className="grid h-56 place-items-center rounded-md border border-dashed border-line text-sm text-muted">
          Sem movimentações categorizadas no período.
        </div>
      ) : (
        <div className="h-64">
          <ResponsiveContainer height="100%" width="100%">
            <BarChart data={chartData} layout="vertical" margin={{ top: 4, right: 12, bottom: 0, left: 4 }}>
              <CartesianGrid stroke="#E2E8F0" strokeDasharray="4 4" horizontal={false} />
              <XAxis
                axisLine={false}
                tickFormatter={(value) => compactMoney(Number(value))}
                tickLine={false}
                tick={{ fill: "#64748B", fontSize: 11 }}
                type="number"
              />
              <YAxis
                axisLine={false}
                dataKey="name"
                tickLine={false}
                tick={{ fill: "#64748B", fontSize: 11 }}
                type="category"
                width={104}
              />
              <Tooltip
                formatter={(value) => chartMoney(value)}
                labelFormatter={(label) => String(label)}
                contentStyle={{ borderRadius: 8, border: "1px solid #E2E8F0", boxShadow: "0 16px 40px rgba(15, 23, 42, 0.12)" }}
              />
              <Bar dataKey="chartTotal" fill={color} name="Total" radius={[0, 5, 5, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      )}
    </div>
  );
}

export function DashboardPage() {
  const [dismissedAlertIds, setDismissedAlertIds] = useState<Set<string>>(new Set());
  const [periodControlsOpen, setPeriodControlsOpen] = useState(false);
  const [period, setPeriod] = useState<Period>("month");
  const [selectedMonth, setSelectedMonth] = useState(currentMonthValue);
  const [compareEnabled, setCompareEnabled] = useState(false);
  const [comparisonStartOverride, setComparisonStartOverride] = useState<string | null>(null);
  const [comparisonEndOverride, setComparisonEndOverride] = useState<string | null>(null);

  const suggestedComparison = useMemo(
    () => defaultComparisonRange(period, selectedMonth),
    [period, selectedMonth],
  );
  const comparisonStart = comparisonStartOverride ?? suggestedComparison.start;
  const comparisonEnd = comparisonEndOverride ?? suggestedComparison.end;
  const comparisonDatesComplete = Boolean(comparisonStart && comparisonEnd);
  const comparisonDatesValid =
    !comparisonDatesComplete || comparisonStart <= comparisonEnd;

  const query = useQuery({
    queryKey: ["dashboard", period, selectedMonth, compareEnabled, comparisonStart, comparisonEnd],
    queryFn: () => {
      const params = new URLSearchParams({ period });
      if (period !== "all") params.set("month", `${selectedMonth}-01`);
      if (compareEnabled && comparisonDatesComplete && comparisonDatesValid) {
        params.set("comparison_start", comparisonStart);
        params.set("comparison_end", comparisonEnd);
      }
      return apiFetch<Dashboard>(`/reports/dashboard?${params.toString()}`);
    },
    refetchInterval: 60_000,
  });

  const trendData = useMemo(() => {
    if (!query.data) return [];
    return query.data.trend_series.map((point) => ({
      ...point,
      incomeValue: Number(point.income),
      expenseValue: Number(point.expense),
      resultValue: Number(point.result),
    }));
  }, [query.data]);

  const comparisonChartData = useMemo(() => {
    if (!query.data?.comparison) return [];
    const comparison = query.data.comparison;
    return [
      { label: "Entradas", período: Number(query.data.month_income), comparação: Number(comparison.income) },
      { label: "Saídas", período: Number(query.data.month_expense), comparação: Number(comparison.expense) },
      { label: "Resultado", período: Number(query.data.month_result), comparação: Number(comparison.result) },
    ];
  }, [query.data]);

  if (query.isLoading) return <div className="screen-state">Carregando dashboard...</div>;
  if (query.isError) return <div className="alert-error">{query.error.message}</div>;

  const data = query.data!;
  const comparison = data.comparison;
  const visibleAlerts = data.due_alerts.filter((alert) => !dismissedAlertIds.has(alert.transaction_id));
  const periodLabel = periods.find((item) => item.value === period)?.label.toLowerCase() ?? "1 mês";
  const incomeCategories = data.category_totals.filter((item) => item.type === "income");
  const expenseCategories = data.category_totals.filter((item) => item.type === "expense");

  return (
    <section className="min-w-0 space-y-6">
      <div className="flex min-w-0 flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Resumo executivo</p>
          <h2 className="section-title">Visão financeira</h2>
          <p className="section-subtitle">
            Liquidações de {dateText(data.period_start)} até {dateText(data.period_end)}.
          </p>
        </div>
        <div className="inline-flex w-fit items-center gap-2 rounded-md border border-line bg-white px-3 py-2 text-sm font-semibold text-muted shadow-sm">
          <CalendarDays className="h-4 w-4 text-accent" />
          {query.isFetching ? "Atualizando dados" : "Atualizado automaticamente"}
        </div>
      </div>

      <div className="panel min-w-0">
        <button
          type="button"
          className="flex w-full items-center gap-3 rounded-md text-left focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-accent/30"
          aria-expanded={periodControlsOpen}
          aria-controls="dashboard-period-controls"
          onClick={() => setPeriodControlsOpen((open) => !open)}
        >
          <span className="shrink-0 rounded-md bg-mint p-2 text-brand"><BarChart3 className="h-5 w-5" /></span>
          <span className="min-w-0 flex-1">
            <span className="panel-title block">Período de análise</span>
            <span className="mt-1 block text-sm text-muted">
              {period === "all" ? "Todo o histórico" : periodLabel} · {dateText(data.period_start)} até {dateText(data.period_end)}
            </span>
          </span>
          <ChevronDown className={`h-5 w-5 shrink-0 text-muted transition-transform duration-150 ${periodControlsOpen ? "rotate-180" : ""}`} aria-hidden="true" />
        </button>

        <div
          id="dashboard-period-controls"
          className="mt-5 space-y-5 border-t border-line pt-5"
          hidden={!periodControlsOpen}
        >
            <p className="text-sm text-muted">Escolha o intervalo das entradas, saídas e gráficos realizados.</p>

            <div className="flex flex-wrap gap-2" aria-label="Duração do período">
              {periods.map((item) => (
                <button
                  key={item.value}
                  type="button"
                  aria-pressed={period === item.value}
                  className={period === item.value ? "btn-primary" : "btn-secondary"}
                  onClick={() => {
                    setPeriod(item.value);
                    setComparisonStartOverride(null);
                    setComparisonEndOverride(null);
                  }}
                >
                  {period === item.value && <Check className="h-4 w-4" aria-hidden="true" />}
                  {item.label}
                </button>
              ))}
            </div>

            {period !== "all" && (
              <label className="field block max-w-xs">
                <span>{period === "month" ? "Mês selecionado" : "Mês final do período"}</span>
                <input
                  type="month"
                  value={selectedMonth}
                  max={currentMonthValue()}
                  onChange={(event) => {
                    setSelectedMonth(event.target.value);
                    setComparisonStartOverride(null);
                    setComparisonEndOverride(null);
                  }}
                />
              </label>
            )}

            <div className="border-t border-line pt-4">
              <label className="flex cursor-pointer items-start gap-3">
                <input
                  className="mt-0.5 h-4 min-h-0 w-4 accent-emerald-600"
                  type="checkbox"
                  checked={compareEnabled}
                  onChange={(event) => setCompareEnabled(event.target.checked)}
                />
                <span>
                  <span className="block text-sm font-semibold text-ink">Comparar com outro período</span>
                  <span className="mt-1 block text-xs text-muted">
                    {period === "all"
                      ? "Informe as datas do intervalo que deseja usar como referência."
                      : `Sugestão: o período equivalente anterior a ${periodLabel}.`}
                  </span>
                </span>
                <ChevronDown className={`ml-auto mt-0.5 h-4 w-4 text-muted transition-transform duration-150 ${compareEnabled ? "rotate-180" : ""}`} />
              </label>

              {compareEnabled && (
                <div className="mt-4 grid gap-3 sm:grid-cols-2">
                  <label className="field">
                    <span>Início da comparação</span>
                    <input
                      type="date"
                      value={comparisonStart}
                      max={todayValue()}
                      onChange={(event) => setComparisonStartOverride(event.target.value)}
                    />
                  </label>
                  <label className="field">
                    <span>Fim da comparação</span>
                    <input
                      type="date"
                      value={comparisonEnd}
                      max={todayValue()}
                      onChange={(event) => setComparisonEndOverride(event.target.value)}
                    />
                  </label>
                  {!comparisonDatesComplete && (
                    <p className="text-sm text-muted sm:col-span-2">Preencha as duas datas para carregar a comparação.</p>
                  )}
                  {!comparisonDatesValid && (
                    <p className="alert-warning sm:col-span-2">A data inicial precisa ser anterior à data final.</p>
                  )}
                </div>
              )}
            </div>
        </div>
      </div>

      <div className="grid min-w-0 gap-4 sm:grid-cols-2 xl:grid-cols-3">
        <Metric icon={Wallet} label="Caixa realizado" value={money(data.current_balance)} detail="Saldo atual da empresa" />
        <Metric icon={ArrowUpRight} label="Entradas realizadas" value={money(data.month_income)} detail={`${data.transaction_count} liquidação(ões) no período`} tone="good" />
        <Metric icon={ArrowDownRight} label="Saídas realizadas" value={money(data.month_expense)} detail={`Período de ${dateText(data.period_start)} a ${dateText(data.period_end)}`} tone="bad" />
        <Metric icon={TrendingUp} label="Resultado realizado" value={money(data.month_result)} detail="Entradas menos saídas no período" />
        <Metric icon={Wallet} label="Previsão do mês atual" value={money(data.month_end_balance_forecast)} detail="Saldo projetado até o fim deste mês" />
        <Metric icon={BarChart3} label="Movimentações liquidadas" value={String(data.transaction_count)} detail="Quantidade no período analisado" />
      </div>

      <div className="grid min-w-0 gap-4 xl:grid-cols-[1.45fr_0.9fr]">
        <div className="panel min-w-0">
          <div className="mb-5 flex flex-col justify-between gap-2 sm:flex-row sm:items-start">
            <div>
              <h3 className="panel-title">Entradas, saídas e resultado</h3>
              <p className="mt-1 text-sm text-muted">
                {data.trend_granularity === "day" ? "Visão diária" : "Visão mensal"} das liquidações no período.
              </p>
            </div>
            <span className="rounded-md bg-mint px-3 py-1 text-xs font-semibold text-brand">
              {data.trend_granularity === "day" ? "Por dia" : "Por mês"}
            </span>
          </div>
          {trendData.length === 0 ? (
            <div className="grid h-72 place-items-center rounded-md border border-dashed border-line text-sm text-muted">
              Não há liquidações no período selecionado.
            </div>
          ) : (
            <div className="h-72 min-w-0">
              <ResponsiveContainer height="100%" width="100%">
                <ComposedChart data={trendData} margin={{ left: 2, right: 12, top: 8, bottom: 0 }}>
                  <CartesianGrid stroke="#E2E8F0" strokeDasharray="4 4" vertical={false} />
                  <XAxis
                    axisLine={false}
                    dataKey="date"
                    interval="preserveStartEnd"
                    tickFormatter={(value) => chartDateLabel(String(value), data.trend_granularity)}
                    tickLine={false}
                    tick={{ fill: "#64748B", fontSize: 11 }}
                  />
                  <YAxis
                    axisLine={false}
                    tickFormatter={(value) => compactMoney(Number(value))}
                    tickLine={false}
                    tick={{ fill: "#64748B", fontSize: 11 }}
                    width={76}
                  />
                  <Tooltip
                    labelFormatter={(value) => dateText(String(value))}
                    formatter={(value) => chartMoney(value)}
                    contentStyle={{ borderRadius: 8, border: "1px solid #E2E8F0", boxShadow: "0 16px 40px rgba(15, 23, 42, 0.12)" }}
                  />
                  <Legend verticalAlign="top" height={36} />
                  <Bar dataKey="incomeValue" fill="#10B981" name="Entradas" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="expenseValue" fill="#F87171" name="Saídas" radius={[4, 4, 0, 0]} />
                  <Line dataKey="resultValue" dot={false} name="Resultado" stroke="#0F4C5C" strokeWidth={3} type="monotone" />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
          )}
        </div>

        <div className="panel min-w-0">
          <h3 className="panel-title">Operação em aberto</h3>
          <p className="mt-1 text-sm text-muted">Pendências atuais da empresa, independente do período analisado.</p>
          <div className="mt-5 space-y-3">
            <Metric icon={ArrowDownRight} label={`${data.open_payables.count} a pagar`} value={money(data.open_payables.total)} tone="bad" />
            <Metric icon={ArrowUpRight} label={`${data.open_receivables.count} a receber`} value={money(data.open_receivables.total)} tone="good" />
            <Metric icon={AlertTriangle} label={`${data.overdue_payables.count + data.overdue_receivables.count} atrasos`} value={money(Number(data.overdue_payables.total) + Number(data.overdue_receivables.total))} tone="bad" />
          </div>
        </div>
      </div>

      {compareEnabled && comparisonDatesComplete && comparisonDatesValid && comparison && (
        <div className="panel min-w-0">
          <div className="mb-5">
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">Comparativo</p>
            <h3 className="panel-title">{dateText(data.period_start)}–{dateText(data.period_end)} × {dateText(comparison.period_start)}–{dateText(comparison.period_end)}</h3>
            <p className="mt-1 text-sm text-muted">{data.transaction_count} liquidação(ões) no período analisado · {comparison.transaction_count} no período comparado.</p>
          </div>
          <div className="grid min-w-0 gap-5 lg:grid-cols-[1.1fr_1fr]">
            <div className="h-64 min-w-0">
              <ResponsiveContainer height="100%" width="100%">
                <BarChart data={comparisonChartData} margin={{ top: 8, right: 12, left: 4, bottom: 0 }}>
                  <CartesianGrid stroke="#E2E8F0" strokeDasharray="4 4" vertical={false} />
                  <XAxis axisLine={false} dataKey="label" tickLine={false} tick={{ fill: "#64748B", fontSize: 12 }} />
                  <YAxis axisLine={false} tickFormatter={(value) => compactMoney(Number(value))} tickLine={false} tick={{ fill: "#64748B", fontSize: 11 }} width={76} />
                  <Tooltip formatter={(value) => chartMoney(value)} contentStyle={{ borderRadius: 8, border: "1px solid #E2E8F0" }} />
                  <Legend />
                  <Bar dataKey="período" fill="#10B981" name="Período analisado" radius={[4, 4, 0, 0]} />
                  <Bar dataKey="comparação" fill="#94A3B8" name="Período comparado" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            </div>
            <div className="grid gap-3 sm:grid-cols-3 lg:grid-cols-1">
              {[
                { label: "Entradas", amount: comparison.income_change, percent: comparison.income_change_percent, base: comparison.income, positiveIsGood: true },
                { label: "Saídas", amount: comparison.expense_change, percent: comparison.expense_change_percent, base: comparison.expense, positiveIsGood: false },
                { label: "Resultado", amount: comparison.result_change, percent: comparison.result_change_percent, base: comparison.result, positiveIsGood: true },
              ].map((item) => {
                const isGood = (Number(item.amount) >= 0) === item.positiveIsGood;
                return (
                  <div className="metric min-w-0" key={item.label}>
                    <p className="text-xs font-semibold uppercase tracking-wide text-muted">Variação de {item.label.toLowerCase()}</p>
                    <strong className={`mt-2 block break-words text-lg font-bold tracking-tight ${isGood ? "text-emerald-700" : "text-rose-700"}`}>
                      {changeLabel(item.amount, item.percent)}
                    </strong>
                    <span className="mt-2 block text-xs font-medium text-muted">Período comparado: {money(item.base)}</span>
                  </div>
                );
              })}
            </div>
          </div>
        </div>
      )}

      <div className="grid min-w-0 gap-4 xl:grid-cols-2">
        <CategoryChart title="Principais categorias de entrada" data={incomeCategories} color="#10B981" />
        <CategoryChart title="Principais categorias de saída" data={expenseCategories} color="#F87171" />
      </div>

      <div className="panel min-w-0">
        <div className="mb-5">
          <h3 className="panel-title">Movimentações por forma</h3>
          <p className="mt-1 text-sm text-muted">Entradas e saídas liquidadas no período selecionado.</p>
        </div>
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {data.payment_methods.map((item) => (
            <div className="metric min-w-0" key={item.payment_method}>
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0">
                  <p className="text-xs font-semibold uppercase tracking-wide text-muted">{item.label || paymentMethodText(item.payment_method)}</p>
                  <strong className="mt-3 block break-words text-xl font-bold tracking-tight text-ink">{money(item.net_total)}</strong>
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
        <div className="panel min-w-0 space-y-3">
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
