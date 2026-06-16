import { useMemo, useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { AlertTriangle, Banknote, CalendarClock, TrendingDown, TrendingUp, Users } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import type {
  AdminChartPoint,
  AdminFinancialDashboard,
  AdminFinancialSeriesPoint,
  AdminFinancialTable,
  Plan,
  SubscriptionStatus,
} from "../types";

const subscriptionLabels: Record<SubscriptionStatus, string> = {
  trialing: "Trial",
  active: "Ativa",
  pending_payment: "Pagamento pendente",
  blocked: "Bloqueada",
  canceled: "Cancelada",
};

const paymentLabels: Record<string, string> = {
  paid: "Pago",
  pending: "Pendente",
  overdue: "Vencido",
  canceled: "Cancelado",
  refunded: "Estornado",
  "-": "Sem pagamento",
};

const cardDefinitions = [
  ["mrr", "MRR atual", "money", TrendingUp],
  ["arr", "ARR estimado", "money", TrendingUp],
  ["received_current_month", "Recebido no mês", "money", Banknote],
  ["received_last_30_days", "Recebido em 30 dias", "money", Banknote],
  ["forecast_current_month", "Previsto no mês", "money", CalendarClock],
  ["forecast_next_30_days", "Previsto em 30 dias", "money", CalendarClock],
  ["pending_revenue", "Receita pendente", "money", AlertTriangle],
  ["overdue_revenue", "Receita vencida", "money", AlertTriangle],
  ["lost_cancellations", "Perdida por cancelamentos", "money", TrendingDown],
  ["lost_delinquency", "Perdida por bloqueios", "money", TrendingDown],
  ["average_ticket", "Ticket médio", "money", Banknote],
  ["paying_customers", "Clientes pagantes", "number", Users],
  ["valid_subscriptions", "Assinaturas válidas", "number", Users],
  ["received_today", "Recebido hoje", "money", Banknote],
  ["received_current_week", "Recebido na semana", "money", Banknote],
  ["renewals_current_month", "Renovações no mês", "number", CalendarClock],
  ["renewals_next_7_days", "Renovações em 7 dias", "number", CalendarClock],
  ["renewals_next_30_days", "Renovações em 30 dias", "number", CalendarClock],
  ["monthly_financial_churn_rate", "Churn financeiro mensal", "percent", TrendingDown],
  ["delinquency_rate", "Taxa de inadimplência", "percent", AlertTriangle],
] as const;

export function AdminFinancialPage() {
  const now = new Date();
  const [period, setPeriod] = useState({
    start: `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-01`,
    end: now.toISOString().slice(0, 10),
  });
  const [filters, setFilters] = useState({
    search: "",
    subscription_status: "",
    payment_status: "",
    plan_id: "",
    payment_method: "",
    page: 1,
  });

  const dashboardQuery = new URLSearchParams({
    period_start: `${period.start}T00:00:00Z`,
    period_end: `${period.end}T23:59:59Z`,
  });
  const tableQuery = new URLSearchParams({ page: String(filters.page), page_size: "15" });
  Object.entries(filters).forEach(([key, value]) => {
    if (key !== "page" && value) tableQuery.set(key, String(value));
  });

  const dashboard = useQuery({
    queryKey: ["admin-financial-dashboard", period],
    queryFn: () =>
      apiFetch<AdminFinancialDashboard>(`/admin/financial/dashboard?${dashboardQuery}`),
  });
  const table = useQuery({
    queryKey: ["admin-financial-payments", filters],
    queryFn: () => apiFetch<AdminFinancialTable>(`/admin/financial/payments?${tableQuery}`),
  });
  const plans = useQuery({
    queryKey: ["admin-plans"],
    queryFn: () => apiFetch<Plan[]>("/admin/plans"),
  });

  const metrics = dashboard.data?.metrics;
  const series = dashboard.data?.monthly_series ?? [];
  const updateFilter = (key: keyof typeof filters, value: string | number) =>
    setFilters((current) => ({ ...current, [key]: value, page: key === "page" ?Number(value) : 1 }));

  return (
    <section className="space-y-6">
      <div className="flex flex-col gap-4 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <h2 className="section-title">Dashboard financeiro</h2>
          <p className="section-subtitle">
            Receita recebida, prevista, pendente e perdida pela plataforma.
          </p>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          <label className="field" htmlFor="financial-start">
            Início
            <input
              id="financial-start"
              type="date"
              value={period.start}
              onChange={(event) => setPeriod({ ...period, start: event.target.value })}
            />
          </label>
          <label className="field" htmlFor="financial-end">
            Fim
            <input
              id="financial-end"
              type="date"
              value={period.end}
              onChange={(event) => setPeriod({ ...period, end: event.target.value })}
            />
          </label>
        </div>
      </div>

      {dashboard.isLoading && <div className="screen-state">Calculando indicadores financeiros...</div>}
      {dashboard.isError && <div className="alert-error">{dashboard.error.message}</div>}

      {metrics && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4 2xl:grid-cols-5">
            {cardDefinitions.map(([key, label, format, Icon]) => {
              const value = metrics[key];
              const warning = ["pending_revenue", "overdue_revenue", "lost_cancellations", "lost_delinquency"].includes(key);
              return (
                <article key={key} className={`metric ${warning ?"border-amber-200 bg-amber-50/40" : ""}`}>
                  <div className="flex items-center justify-between gap-2">
                    <p>{label}</p>
                    <Icon className={`h-4 w-4 ${warning ?"text-amber-700" : "text-brand"}`} />
                  </div>
                  <strong>{formatMetric(value, format)}</strong>
                </article>
              );
            })}
          </div>

          <div className="grid gap-5 xl:grid-cols-2">
            <SeriesChart title="Receita mensal recebida" series={series} keys={["received"]} />
            <SeriesChart title="Prevista vs recebida" series={series} keys={["forecast", "received"]} />
            <SeriesChart title="MRR ao longo dos meses" series={series} keys={["mrr"]} />
            <SeriesChart title="ARR estimado" series={series} keys={["arr"]} />
            <BreakdownChart title="Receita por plano" points={dashboard.data?.revenue_by_plan ?? []} />
            <BreakdownChart title="Receita por status" points={dashboard.data?.revenue_by_subscription_status ?? []} />
            <SeriesChart title="Pagamentos recebidos por mês" series={series} keys={["payments_received"]} moneyValues={false} />
            <SeriesChart title="Pagamentos pendentes por mês" series={series} keys={["pending"]} />
            <SeriesChart title="Churn financeiro por mês" series={series} keys={["churn"]} />
            <SeriesChart title="Ticket médio ao longo dos meses" series={series} keys={["average_ticket"]} />
          </div>
        </>
      )}

      <div className="panel">
        <div className="table-header">
          <div>
            <h3 className="panel-title">Pagamentos e assinaturas</h3>
            <p className="section-subtitle">{table.data?.total ?? 0} empresa(s) encontrada(s).</p>
          </div>
          {table.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>

        <div className="mt-4 grid gap-3 md:grid-cols-2 xl:grid-cols-5">
          <label className="field" htmlFor="financial-search">
            Empresa
            <input
              id="financial-search"
              placeholder="Buscar por nome"
              value={filters.search}
              onChange={(event) => updateFilter("search", event.target.value)}
            />
          </label>
          <FilterSelect
            id="subscription-filter"
            label="Assinatura"
            value={filters.subscription_status}
            onChange={(value) => updateFilter("subscription_status", value)}
            options={Object.entries(subscriptionLabels)}
          />
          <FilterSelect
            id="payment-filter"
            label="Pagamento"
            value={filters.payment_status}
            onChange={(value) => updateFilter("payment_status", value)}
            options={[["paid", "Recebidos"], ["pending", "Pendentes"], ["overdue", "Vencidos"], ["canceled", "Cancelados"], ["refunded", "Estornados"]]}
          />
          <FilterSelect
            id="plan-filter"
            label="Plano"
            value={filters.plan_id}
            onChange={(value) => updateFilter("plan_id", value)}
            options={(plans.data ?? []).map((plan) => [plan.id, plan.name])}
          />
          <FilterSelect
            id="method-filter"
            label="Método"
            value={filters.payment_method}
            onChange={(value) => updateFilter("payment_method", value)}
            options={[["manual", "Renovação manual"]]}
          />
        </div>

        {table.isError && <div className="alert-error mt-4">{table.error.message}</div>}
        {table.isLoading && <div className="screen-state mt-4">Carregando tabela financeira...</div>}
        {table.data?.items.length === 0 && <div className="screen-state mt-4">Nenhum registro para os filtros selecionados.</div>}
        {!!table.data?.items.length && (
          <>
            <div className="table-wrap">
              <table>
                <thead>
                  <tr>
                    <th>Empresa</th><th>Plano</th><th>Valor</th><th>Assinatura</th><th>Pagamento</th>
                    <th>Pago em</th><th>Próximo vencimento</th><th>Atraso</th><th>Método</th>
                    <th>Recebido</th><th>Pendente</th><th>Admin</th><th>Observação</th><th>Criado em</th><th>Atualizado em</th>
                  </tr>
                </thead>
                <tbody>
                  {table.data.items.map((item) => (
                    <tr key={item.company_id}>
                      <td className="font-medium">{item.company_name}</td>
                      <td>{item.plan_name ?? "-"}</td>
                      <td>{money(item.plan_value)}</td>
                      <td><StatusBadge status={item.subscription_status} /></td>
                      <td><PaymentBadge status={item.payment_status} /></td>
                      <td>{dateText(item.payment_date)}</td>
                      <td>{dateText(item.next_due_date)}</td>
                      <td>{item.days_overdue ?`${item.days_overdue} dia(s)` : "-"}</td>
                      <td>{item.payment_method === "manual" ?"Manual" : item.payment_method ?? "-"}</td>
                      <td className="font-medium text-emerald-700">{money(item.received_amount)}</td>
                      <td className="font-medium text-amber-700">{money(item.pending_amount)}</td>
                      <td>{item.renewed_by_admin ?? "-"}</td>
                      <td className="max-w-48 truncate" title={item.notes ?? ""}>{item.notes ?? "-"}</td>
                      <td>{dateText(item.created_at)}</td>
                      <td>{dateText(item.updated_at)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
            <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
              <button className="btn-secondary" disabled={filters.page <= 1} onClick={() => updateFilter("page", filters.page - 1)}>Anterior</button>
              <span className="text-sm text-muted">Página {table.data.page} de {table.data.pages}</span>
              <button className="btn-secondary" disabled={filters.page >= table.data.pages} onClick={() => updateFilter("page", filters.page + 1)}>Próxima</button>
            </div>
          </>
        )}
      </div>
    </section>
  );
}

function formatMetric(value: string | number, format: "money" | "number" | "percent") {
  if (format === "money") return money(value);
  if (format === "percent") return `${Number(value).toLocaleString("pt-BR", { minimumFractionDigits: 2, maximumFractionDigits: 2 })}%`;
  return Number(value).toLocaleString("pt-BR");
}

function SeriesChart({
  title,
  series,
  keys,
  moneyValues = true,
}: {
  title: string;
  series: AdminFinancialSeriesPoint[];
  keys: Array<keyof AdminFinancialSeriesPoint>;
  moneyValues?: boolean;
}) {
  const max = useMemo(
    () => Math.max(...series.flatMap((point) => keys.map((key) => Number(point[key]) || 0)), 1),
    [keys, series],
  );
  const colors = ["bg-brand", "bg-sky-500"];
  return (
    <article className="panel">
      <h3 className="panel-title">{title}</h3>
      <div className="mt-4 space-y-3">
        {series.map((point) => (
          <div key={`${title}-${point.month}`} className="grid grid-cols-[56px_minmax(72px,1fr)_minmax(72px,auto)] items-center gap-2 text-xs sm:grid-cols-[70px_1fr_100px] sm:gap-3">
            <span className="text-muted">{monthText(point.month)}</span>
            <div className="space-y-1">
              {keys.map((key, index) => {
                const value = Number(point[key]) || 0;
                return <div key={key} className={`h-2 rounded ${colors[index]}`} style={{ width: `${Math.max(value / max * 100, value ?3 : 0)}%` }} />;
              })}
            </div>
            <span className="text-right font-medium">{moneyValues ?money(String(point[keys[0]])) : Number(point[keys[0]]).toLocaleString("pt-BR")}</span>
          </div>
        ))}
      </div>
    </article>
  );
}

function BreakdownChart({ title, points }: { title: string; points: AdminChartPoint[] }) {
  const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
  return (
    <article className="panel">
      <h3 className="panel-title">{title}</h3>
      <div className="mt-4 space-y-3">
        {points.length === 0 && <p className="text-sm text-muted">Sem dados no período.</p>}
        {points.map((point) => {
          const value = Number(point.value) || 0;
          return (
            <div key={`${title}-${point.label}`} className="grid grid-cols-[minmax(72px,0.8fr)_minmax(72px,1fr)_minmax(72px,auto)] items-center gap-2 text-xs sm:grid-cols-[120px_1fr_100px] sm:gap-3 sm:text-sm">
              <span className="truncate text-muted">{point.label}</span>
              <div className="h-3 rounded bg-panel"><div className="h-3 rounded bg-brand" style={{ width: `${Math.max(value / max * 100, value ?4 : 0)}%` }} /></div>
              <span className="text-right font-medium">{money(point.value)}</span>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function FilterSelect({ id, label, value, options, onChange }: { id: string; label: string; value: string; options: string[][]; onChange: (value: string) => void }) {
  return (
    <label className="field" htmlFor={id}>
      {label}
      <select id={id} value={value} onChange={(event) => onChange(event.target.value)}>
        <option value="">Todos</option>
        {options.map(([optionValue, optionLabel]) => <option key={optionValue} value={optionValue}>{optionLabel}</option>)}
      </select>
    </label>
  );
}

function StatusBadge({ status }: { status: SubscriptionStatus }) {
  const tone = {
    active: "bg-emerald-50 text-emerald-700",
    trialing: "bg-sky-50 text-sky-700",
    pending_payment: "bg-amber-50 text-amber-800",
    blocked: "bg-rose-50 text-rose-700",
    canceled: "bg-zinc-100 text-zinc-700",
  }[status];
  return <span className={`rounded-md px-2 py-1 text-xs font-semibold ${tone}`}>{subscriptionLabels[status]}</span>;
}

function PaymentBadge({ status }: { status: string }) {
  const tone = status === "paid" ?"bg-emerald-50 text-emerald-700" : status === "overdue" ?"bg-rose-50 text-rose-700" : "bg-amber-50 text-amber-800";
  return <span className={`rounded-md px-2 py-1 text-xs font-semibold ${tone}`}>{paymentLabels[status] ?? status}</span>;
}

function monthText(value: string) {
  const [year, month] = value.split("-");
  return `${month}/${year.slice(2)}`;
}
