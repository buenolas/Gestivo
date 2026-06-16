import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import type { AdminCompanySubscription, ManualPayment, Plan, SubscriptionStatus } from "../types";

function statusText(status: SubscriptionStatus) {
  const labels: Record<SubscriptionStatus, string> = {
    trialing: "Trial",
    active: "Ativa",
    pending_payment: "Pagamento pendente",
    canceled: "Cancelada",
    blocked: "Bloqueada",
  };
  return labels[status];
}

function cycleText(cycle: Plan["billing_cycle"]) {
  const labels: Record<Plan["billing_cycle"], string> = {
    monthly: "Mensal",
    semiannual: "Semestral",
    annual: "Anual",
  };
  return labels[cycle];
}

export function AdminSubscriptionsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    company_id: "",
    plan_id: "",
    paid_at: "",
    notes: "",
  });
  const companies = useQuery({
    queryKey: ["admin-subscription-companies"],
    queryFn: () => apiFetch<AdminCompanySubscription[]>("/admin/subscriptions/companies"),
  });
  const plans = useQuery({
    queryKey: ["admin-plans"],
    queryFn: () => apiFetch<Plan[]>("/admin/plans"),
  });

  const selectedCompany = useMemo(
    () => companies.data?.find((company) => company.company_id === form.company_id),
    [companies.data, form.company_id],
  );
  const selectedPlan = useMemo(
    () => plans.data?.find((plan) => plan.id === form.plan_id),
    [plans.data, form.plan_id],
  );

  const renew = useMutation({
    mutationFn: () =>
      apiFetch<ManualPayment>("/admin/subscriptions/manual-renewals", {
        method: "POST",
        body: JSON.stringify({
          company_id: form.company_id,
          plan_id: form.plan_id,
          paid_at: form.paid_at ?`${form.paid_at}T12:00:00Z` : null,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      setForm({ company_id: "", plan_id: "", paid_at: "", notes: "" });
      await queryClient.invalidateQueries({ queryKey: ["admin-subscription-companies"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    renew.mutate();
  }

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <h2 className="panel-title lg:col-span-4">Renovacao manual</h2>
        <label className="field lg:col-span-2" htmlFor="renew-company">
          Empresa
          <select
            id="renew-company"
            required
            value={form.company_id}
            onChange={(event) => setForm({ ...form, company_id: event.target.value })}
          >
            <option value="">Selecione uma empresa</option>
            {(companies.data ?? []).map((company) => (
              <option key={company.company_id} value={company.company_id}>
                {company.company_name}
              </option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="renew-plan">
          Plano
          <select
            id="renew-plan"
            required
            value={form.plan_id}
            onChange={(event) => setForm({ ...form, plan_id: event.target.value })}
          >
            <option value="">Selecione um plano</option>
            {(plans.data ?? []).map((plan) => (
              <option key={plan.id} value={plan.id} disabled={!plan.is_active}>
                {plan.name} - {money(plan.price)}
              </option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="renew-paid-at">
          Data do pagamento
          <input
            id="renew-paid-at"
            type="date"
            value={form.paid_at}
            onChange={(event) => setForm({ ...form, paid_at: event.target.value })}
          />
        </label>
        <label className="field lg:col-span-3" htmlFor="renew-notes">
          Observacoes
          <input
            id="renew-notes"
            value={form.notes}
            onChange={(event) => setForm({ ...form, notes: event.target.value })}
          />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={renew.isPending || !selectedCompany || !selectedPlan}>
            <CheckCircle2 className="h-4 w-4" />
            Renovar
          </button>
        </div>
        {renew.error && <div className="alert-error lg:col-span-4">{renew.error.message}</div>}
        {plans.isError && <div className="alert-error lg:col-span-4">{plans.error.message}</div>}
      </form>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Empresas</h2>
          {companies.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {companies.isError && <div className="alert-error">{companies.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Empresa</th>
                <th>Status</th>
                <th>Plano atual</th>
                <th>Trial ate</th>
                <th>Assinatura ate</th>
                <th>Acesso ate</th>
              </tr>
            </thead>
            <tbody>
              {(companies.data ?? []).map((company) => (
                <tr key={company.company_id}>
                  <td>{company.company_name}</td>
                  <td>{statusText(company.status)}</td>
                  <td>{company.current_plan_name ?? "-"}</td>
                  <td>{dateText(company.trial_ends_at)}</td>
                  <td>{dateText(company.subscription_valid_until)}</td>
                  <td>{dateText(company.access_until)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>

      {selectedCompany && (
        <div className="metric">
          <p>Empresa selecionada</p>
          <strong>{selectedCompany.company_name}</strong>
          <p className="mt-2 text-sm text-muted">
            Status atual: {statusText(selectedCompany.status)}. A renovacao registra o pagamento manual
            e libera acesso conforme a duracao do plano.
          </p>
          {selectedPlan && (
            <p className="mt-2 text-sm text-muted">
              Plano selecionado: {cycleText(selectedPlan.billing_cycle)}, {selectedPlan.duration_months} mes(es), valor {money(selectedPlan.price)}.
            </p>
          )}
        </div>
      )}
    </section>
  );
}
