import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  Ban,
  CheckCircle2,
  Eye,
  Filter,
  LockOpen,
  RefreshCw,
  Search,
  ShieldAlert,
} from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import type {
  AdminChartPoint,
  AdminClientDashboard,
  AdminClientDetail,
  AdminClientList,
  AdminClientListItem,
  ManualPayment,
  Plan,
  SubscriptionStatus,
} from "../types";

const statusLabels: Record<SubscriptionStatus, string> = {
  trialing: "Trial",
  active: "Ativa",
  pending_payment: "Pendente",
  blocked: "Bloqueada",
  canceled: "Cancelada",
};

const filterOptions = [
  ["", "Todos"],
  ["active", "Ativos"],
  ["trialing", "Em trial"],
  ["overdue", "Vencidos"],
  ["blocked", "Bloqueados"],
  ["canceled", "Cancelados"],
  ["trial_ending", "Trial vencendo"],
  ["subscription_ending", "Assinatura vencendo"],
  ["no_recent_login", "Sem login recente"],
  ["no_month_usage", "Sem uso no mês"],
];

export function AdminClientsPage() {
  const queryClient = useQueryClient();
  const [page, setPage] = useState(1);
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState("");
  const [planId, setPlanId] = useState("");
  const [filterKey, setFilterKey] = useState("");
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(null);
  const [renewForm, setRenewForm] = useState({ plan_id: "", paid_at: "", notes: "" });
  const [planChangeId, setPlanChangeId] = useState("");

  const dashboard = useQuery({
    queryKey: ["admin-clients-dashboard"],
    queryFn: () => apiFetch<AdminClientDashboard>("/admin/dashboard/clients"),
  });
  const plans = useQuery({
    queryKey: ["admin-plans"],
    queryFn: () => apiFetch<Plan[]>("/admin/plans"),
  });
  const list = useQuery({
    queryKey: ["admin-clients", page, search, status, planId, filterKey],
    queryFn: () => {
      const params = new URLSearchParams({
        page: String(page),
        page_size: "15",
      });
      if (search.trim()) params.set("search", search.trim());
      if (status) params.set("subscription_status", status);
      if (planId) params.set("plan_id", planId);
      if (filterKey) params.set("filter_key", filterKey);
      return apiFetch<AdminClientList>(`/admin/clients?${params.toString()}`);
    },
  });
  const detail = useQuery({
    queryKey: ["admin-client-detail", selectedCompanyId],
    queryFn: () => apiFetch<AdminClientDetail>(`/admin/clients/${selectedCompanyId}`),
    enabled: Boolean(selectedCompanyId),
  });

  const invalidateAdminClients = async () => {
    await queryClient.invalidateQueries({ queryKey: ["admin-clients"] });
    await queryClient.invalidateQueries({ queryKey: ["admin-clients-dashboard"] });
    await queryClient.invalidateQueries({ queryKey: ["admin-client-detail"] });
  };

  const action = useMutation({
    mutationFn: ({ companyId, kind }: { companyId: string; kind: string }) =>
      apiFetch(`/admin/clients/${companyId}/${kind}`, { method: "POST" }),
    onSuccess: invalidateAdminClients,
  });

  const renew = useMutation({
    mutationFn: () => {
      if (!selectedCompanyId) throw new Error("Selecione uma empresa.");
      return apiFetch<ManualPayment>(`/admin/clients/${selectedCompanyId}/renew`, {
        method: "POST",
        body: JSON.stringify({
          plan_id: renewForm.plan_id || null,
          paid_at: renewForm.paid_at ? `${renewForm.paid_at}T12:00:00Z` : null,
          notes: renewForm.notes || null,
        }),
      });
    },
    onSuccess: async () => {
      setRenewForm({ plan_id: "", paid_at: "", notes: "" });
      await invalidateAdminClients();
    },
  });

  const changePlan = useMutation({
    mutationFn: () => {
      if (!selectedCompanyId || !planChangeId) throw new Error("Selecione empresa e plano.");
      return apiFetch(`/admin/clients/${selectedCompanyId}/plan`, {
        method: "PATCH",
        body: JSON.stringify({ plan_id: planChangeId }),
      });
    },
    onSuccess: invalidateAdminClients,
  });

  function submitFilters(event: FormEvent) {
    event.preventDefault();
    setPage(1);
  }

  function confirmAction(company: AdminClientListItem, kind: string, label: string) {
    if (!window.confirm(`${label} ${company.company_name}?`)) return;
    action.mutate({ companyId: company.company_id, kind });
  }

  const selectedCompany = useMemo(
    () => list.data?.items.find((item) => item.company_id === selectedCompanyId) ?? detail.data,
    [detail.data, list.data?.items, selectedCompanyId],
  );

  return (
    <section className="space-y-5">
      <div>
        <h2 className="section-title">Dashboard admin de clientes</h2>
        <p className="section-subtitle">
          Saúde da base, assinaturas, risco, uso da plataforma e ações administrativas.
        </p>
      </div>

      {dashboard.isLoading && <div className="screen-state">Carregando indicadores...</div>}
      {dashboard.isError && <div className="alert-error">{dashboard.error.message}</div>}
      {dashboard.data && (
        <>
          <div className="grid gap-3 sm:grid-cols-2 lg:grid-cols-4">
            {dashboard.data.cards.map((card) => (
              <article key={card.key} className="metric">
                <p>{card.label}</p>
                <strong>{String(card.value)}</strong>
              </article>
            ))}
          </div>

          <div className="grid gap-4 xl:grid-cols-3">
            <Chart title="Clientes por status" points={dashboard.data.subscription_status} />
            <Chart title="Novos clientes por mês" points={dashboard.data.new_clients_by_month} />
            <Chart title="Conversões por mês" points={dashboard.data.trial_conversions_by_month} />
            <Chart title="Cancelamentos por mês" points={dashboard.data.cancellations_by_month} />
            <Chart title="Base ativa" points={dashboard.data.active_base_by_month} />
            <Chart title="Ativos vs risco" points={dashboard.data.active_vs_risk} />
            <Chart title="Clientes por plano" points={dashboard.data.plan_distribution} />
            <Chart title="Mais ativos" points={dashboard.data.most_active_by_transactions} />
            <Chart title="Maior volume financeiro" points={dashboard.data.highest_financial_volume} moneyValues />
          </div>
        </>
      )}

      <form className="panel grid gap-3 lg:grid-cols-[1.4fr_1fr_1fr_1fr_auto]" onSubmit={submitFilters}>
        <label className="field" htmlFor="admin-client-search">
          Busca
          <div className="relative">
            <Search className="pointer-events-none absolute left-3 top-3 h-4 w-4 text-muted" />
            <input
              id="admin-client-search"
              className="pl-9"
              placeholder="Empresa, responsável ou e-mail"
              value={search}
              onChange={(event) => setSearch(event.target.value)}
            />
          </div>
        </label>
        <label className="field" htmlFor="admin-client-status">
          Status
          <select id="admin-client-status" value={status} onChange={(event) => setStatus(event.target.value)}>
            <option value="">Todos</option>
            {Object.entries(statusLabels).map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="admin-client-plan">
          Plano
          <select id="admin-client-plan" value={planId} onChange={(event) => setPlanId(event.target.value)}>
            <option value="">Todos</option>
            {(plans.data ?? []).map((plan) => (
              <option key={plan.id} value={plan.id}>{plan.name}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="admin-client-filter">
          Filtro
          <select id="admin-client-filter" value={filterKey} onChange={(event) => setFilterKey(event.target.value)}>
            {filterOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full">
            <Filter className="h-4 w-4" />
            Filtrar
          </button>
        </div>
      </form>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Clientes</h2>
          {list.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {list.isError && <div className="alert-error">{list.error.message}</div>}
        {list.data?.items.length === 0 && <div className="screen-state mt-4">Nenhum cliente encontrado.</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Empresa</th>
                <th>Responsável</th>
                <th>Status</th>
                <th>Plano</th>
                <th>Cadastro</th>
                <th>Trial</th>
                <th>Assinatura</th>
                <th>Dias</th>
                <th>Último login</th>
                <th>Usuários</th>
                <th>Lançamentos</th>
                <th>Importações</th>
                <th>Uso</th>
                <th>Ações</th>
              </tr>
            </thead>
            <tbody>
              {(list.data?.items ?? []).map((client) => (
                <tr key={client.company_id} className={client.is_at_risk ? "bg-amber-50/45" : ""}>
                  <td className="font-medium">{client.company_name}</td>
                  <td>
                    <div>{client.admin_name ?? "-"}</div>
                    <div className="text-xs text-muted">{client.admin_email ?? "-"}</div>
                  </td>
                  <td><StatusBadge status={client.subscription_status} /></td>
                  <td>
                    <div>{client.plan_name ?? "-"}</div>
                    <div className="text-xs text-muted">{client.plan_price ? money(client.plan_price) : ""}</div>
                  </td>
                  <td>{dateText(client.created_at)}</td>
                  <td>{dateText(client.trial_ends_at)}</td>
                  <td>{dateText(client.subscription_valid_until)}</td>
                  <td>{client.days_remaining ?? "-"}</td>
                  <td>{dateText(client.last_login_at)}</td>
                  <td>{client.users_count}</td>
                  <td>{client.financial_transactions_count}</td>
                  <td>{client.imports_count}</td>
                  <td>{client.usage_status}</td>
                  <td>
                    <div className="flex flex-wrap gap-2">
                      <button className="icon-btn" title="Visualizar detalhes" onClick={() => setSelectedCompanyId(client.company_id)}>
                        <Eye className="h-4 w-4" />
                      </button>
                      <button className="icon-btn" title="Bloquear" onClick={() => confirmAction(client, "block", "Bloquear")}>
                        <Ban className="h-4 w-4" />
                      </button>
                      <button className="icon-btn" title="Desbloquear" onClick={() => confirmAction(client, "unblock", "Desbloquear")}>
                        <LockOpen className="h-4 w-4" />
                      </button>
                      <button className="icon-btn" title="Cancelar" onClick={() => confirmAction(client, "cancel", "Cancelar")}>
                        <ShieldAlert className="h-4 w-4" />
                      </button>
                      <button className="icon-btn" title="Reativar" onClick={() => confirmAction(client, "reactivate", "Reativar")}>
                        <RefreshCw className="h-4 w-4" />
                      </button>
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        {list.data && (
          <div className="mt-4 flex items-center justify-between gap-3 text-sm">
            <span className="text-muted">{list.data.total} cliente(s)</span>
            <div className="flex gap-2">
              <button className="btn-secondary" disabled={page <= 1} onClick={() => setPage(page - 1)}>Anterior</button>
              <span className="flex items-center px-2">Página {list.data.page} de {list.data.pages}</span>
              <button className="btn-secondary" disabled={page >= list.data.pages} onClick={() => setPage(page + 1)}>Próxima</button>
            </div>
          </div>
        )}
      </div>

      {selectedCompanyId && (
        <div className="fixed inset-0 z-40 overflow-y-auto bg-black/30 px-4 py-6">
          <section className="mx-auto max-w-5xl space-y-5 rounded-lg border border-line bg-white p-5 shadow-lg">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h2 className="panel-title">{selectedCompany?.company_name ?? "Cliente"}</h2>
                <p className="section-subtitle">{selectedCompany?.admin_email}</p>
              </div>
              <button className="btn-secondary" onClick={() => setSelectedCompanyId(null)}>Fechar</button>
            </div>
            {detail.isLoading && <div className="screen-state">Carregando detalhes...</div>}
            {detail.isError && <div className="alert-error">{detail.error.message}</div>}
            {detail.data && (
              <>
                <div className="grid gap-3 md:grid-cols-4">
                  <Detail label="Status" value={statusLabels[detail.data.subscription_status]} />
                  <Detail label="Plano" value={detail.data.plan_name ?? "-"} />
                  <Detail label="Vencimento" value={dateText(detail.data.subscription_valid_until)} />
                  <Detail label="Última importação" value={dateText(detail.data.last_import_at)} />
                </div>

                <div className="grid gap-4 lg:grid-cols-2">
                  <form className="panel grid gap-3" onSubmit={(event) => { event.preventDefault(); renew.mutate(); }}>
                    <h3 className="panel-title">Renovar assinatura</h3>
                    <label className="field" htmlFor="detail-renew-plan">
                      Plano
                      <select id="detail-renew-plan" required value={renewForm.plan_id} onChange={(event) => setRenewForm({ ...renewForm, plan_id: event.target.value })}>
                        <option value="">Selecione</option>
                        {(plans.data ?? []).map((plan) => <option key={plan.id} value={plan.id}>{plan.name} - {money(plan.price)}</option>)}
                      </select>
                    </label>
                    <label className="field" htmlFor="detail-renew-date">
                      Data do pagamento
                      <input id="detail-renew-date" type="date" value={renewForm.paid_at} onChange={(event) => setRenewForm({ ...renewForm, paid_at: event.target.value })} />
                    </label>
                    <label className="field" htmlFor="detail-renew-notes">
                      Observações
                      <input id="detail-renew-notes" value={renewForm.notes} onChange={(event) => setRenewForm({ ...renewForm, notes: event.target.value })} />
                    </label>
                    {renew.error && <div className="alert-error">{renew.error.message}</div>}
                    <button className="btn-primary" disabled={renew.isPending}><CheckCircle2 className="h-4 w-4" />Renovar</button>
                  </form>

                  <form className="panel grid gap-3" onSubmit={(event) => { event.preventDefault(); if (window.confirm("Alterar plano da empresa?")) changePlan.mutate(); }}>
                    <h3 className="panel-title">Alterar plano</h3>
                    <label className="field" htmlFor="detail-plan-change">
                      Novo plano
                      <select id="detail-plan-change" required value={planChangeId} onChange={(event) => setPlanChangeId(event.target.value)}>
                        <option value="">Selecione</option>
                        {(plans.data ?? []).map((plan) => <option key={plan.id} value={plan.id}>{plan.name} - {money(plan.price)}</option>)}
                      </select>
                    </label>
                    {changePlan.error && <div className="alert-error">{changePlan.error.message}</div>}
                    <button className="btn-secondary" disabled={changePlan.isPending}>Alterar plano</button>
                  </form>
                </div>

                <div className="grid gap-4 lg:grid-cols-3">
                  <History title="Usuários" rows={detail.data.users} />
                  <History title="Pagamentos/renovações" rows={detail.data.payment_history} />
                  <History title="Eventos recentes" rows={detail.data.usage_events} />
                </div>
              </>
            )}
          </section>
        </div>
      )}
    </section>
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
  return <span className={`rounded-md px-2 py-1 text-xs font-semibold ${tone}`}>{statusLabels[status]}</span>;
}

function Chart({ title, points, moneyValues = false }: { title: string; points: AdminChartPoint[]; moneyValues?: boolean }) {
  const max = Math.max(...points.map((point) => Number(point.value) || 0), 1);
  return (
    <article className="panel">
      <h3 className="panel-title">{title}</h3>
      <div className="mt-4 space-y-3">
        {points.map((point) => {
          const value = Number(point.value) || 0;
          return (
            <div key={`${title}-${point.label}`} className="grid grid-cols-[120px_1fr_70px] items-center gap-3 text-sm">
              <span className="truncate text-muted">{point.label}</span>
              <div className="h-3 rounded bg-panel">
                <div className="h-3 rounded bg-brand" style={{ width: `${Math.max((value / max) * 100, value > 0 ? 4 : 0)}%` }} />
              </div>
              <span className="text-right font-medium">{moneyValues ? money(value) : value}</span>
            </div>
          );
        })}
      </div>
    </article>
  );
}

function Detail({ label, value }: { label: string; value: string }) {
  return (
    <div className="metric">
      <p>{label}</p>
      <strong className="text-base">{value}</strong>
    </div>
  );
}

function History({ title, rows }: { title: string; rows: Array<Record<string, string | boolean | null>> }) {
  return (
    <div className="panel">
      <h3 className="panel-title">{title}</h3>
      <div className="mt-3 max-h-80 space-y-3 overflow-auto text-sm">
        {rows.length === 0 && <p className="text-muted">Sem registros.</p>}
        {rows.map((row, index) => (
          <div key={`${title}-${index}`} className="rounded-md border border-line p-3">
            {Object.entries(row).slice(0, 5).map(([key, value]) => (
              <div key={key} className="flex justify-between gap-3">
                <span className="text-muted">{key}</span>
                <span className="text-right font-medium">{String(value ?? "-")}</span>
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
