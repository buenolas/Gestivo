import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2, Pencil, X } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import type { Plan } from "../types";

function normalizeMoneyInput(value: string) {
  return value.trim().replace(/\./g, "").replace(",", ".");
}

function cycleText(cycle: Plan["billing_cycle"]) {
  const labels: Record<Plan["billing_cycle"], string> = {
    monthly: "Mensal",
    semiannual: "Semestral",
    annual: "Anual",
  };
  return labels[cycle];
}

type EditForm = {
  price: string;
  is_active: boolean;
  description: string;
};

export function AdminPlansPage() {
  const queryClient = useQueryClient();
  const [editingPlan, setEditingPlan] = useState<Plan | null>(null);
  const [form, setForm] = useState<EditForm>({
    price: "",
    is_active: true,
    description: "",
  });
  const [successMessage, setSuccessMessage] = useState("");

  const plans = useQuery({
    queryKey: ["admin-plans"],
    queryFn: () => apiFetch<Plan[]>("/admin/plans"),
  });

  const updatePlan = useMutation({
    mutationFn: () => {
      if (!editingPlan) throw new Error("Nenhum plano selecionado.");
      return apiFetch<Plan>(`/admin/plans/${editingPlan.id}`, {
        method: "PATCH",
        body: JSON.stringify({
          price: normalizeMoneyInput(form.price),
          is_active: form.is_active,
          description: form.description || null,
        }),
      });
    },
    onSuccess: async (plan) => {
      setSuccessMessage(`Plano ${plan.name} atualizado.`);
      setEditingPlan(null);
      await queryClient.invalidateQueries({ queryKey: ["admin-plans"] });
    },
  });

  function startEditing(plan: Plan) {
    setSuccessMessage("");
    setEditingPlan(plan);
    setForm({
      price: Number(plan.price).toLocaleString("pt-BR", {
        minimumFractionDigits: 2,
        maximumFractionDigits: 2,
      }),
      is_active: plan.is_active,
      description: plan.description ?? "",
    });
  }

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (editingPlan?.is_active && !form.is_active) {
      const confirmed = window.confirm(
        "Desativar este plano impede novas renovacoes com ele. Deseja continuar?",
      );
      if (!confirmed) return;
    }
    updatePlan.mutate();
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="section-title">Planos da plataforma</h2>
        <p className="section-subtitle">Configure os valores dos planos disponiveis para assinatura.</p>
      </div>

      {plans.isLoading && <div className="screen-state">Carregando planos...</div>}
      {plans.isError && <div className="alert-error">{plans.error.message}</div>}
      {successMessage && (
        <div className="rounded-md border border-emerald-200 bg-emerald-50 px-3 py-2 text-sm text-emerald-800">
          {successMessage}
        </div>
      )}

      <div className="grid gap-4 lg:grid-cols-3">
        {(plans.data ?? []).map((plan) => (
          <article key={plan.id} className="metric space-y-4">
            <div className="flex items-start justify-between gap-3">
              <div>
                <h3 className="text-lg font-semibold text-ink">{plan.name}</h3>
                <p className="text-sm text-muted">{cycleText(plan.billing_cycle)}</p>
              </div>
              <span
                className={`rounded-md px-2 py-1 text-xs font-semibold ${
                  plan.is_active ? "bg-emerald-50 text-emerald-700" : "bg-zinc-100 text-zinc-600"
                }`}
              >
                {plan.is_active ? "Ativo" : "Inativo"}
              </span>
            </div>
            <div>
              <p>Valor atual</p>
              <strong>{money(plan.price)}</strong>
            </div>
            <dl className="grid grid-cols-2 gap-3 text-sm">
              <div>
                <dt className="text-muted">Duracao</dt>
                <dd className="font-medium">{plan.duration_months} mes(es)</dd>
              </div>
              <div>
                <dt className="text-muted">Atualizado em</dt>
                <dd className="font-medium">{dateText(plan.updated_at)}</dd>
              </div>
              <div className="col-span-2">
                <dt className="text-muted">Slug</dt>
                <dd className="font-medium">{plan.slug}</dd>
              </div>
            </dl>
            <p className="min-h-10 text-sm leading-5 text-muted">{plan.description ?? "-"}</p>
            <button className="btn-secondary w-full" onClick={() => startEditing(plan)}>
              <Pencil className="h-4 w-4" />
              Editar
            </button>
          </article>
        ))}
      </div>

      {editingPlan && (
        <form className="panel grid gap-4 lg:grid-cols-3" onSubmit={onSubmit}>
          <div className="lg:col-span-3 flex items-start justify-between gap-3">
            <div>
              <h3 className="panel-title">Editar {editingPlan.name}</h3>
              <p className="section-subtitle">
                Slug, ciclo de cobranca e duracao sao campos estruturais e ficam bloqueados.
              </p>
            </div>
            <button className="icon-btn" type="button" onClick={() => setEditingPlan(null)}>
              <X className="h-4 w-4" />
            </button>
          </div>
          <label className="field" htmlFor="plan-price">
            Valor
            <input
              id="plan-price"
              required
              inputMode="decimal"
              placeholder="49,90"
              value={form.price}
              onChange={(event) => setForm({ ...form, price: event.target.value })}
            />
          </label>
          <label className="field" htmlFor="plan-status">
            Status
            <select
              id="plan-status"
              value={form.is_active ? "active" : "inactive"}
              onChange={(event) => setForm({ ...form, is_active: event.target.value === "active" })}
            >
              <option value="active">Ativo</option>
              <option value="inactive">Inativo</option>
            </select>
          </label>
          <div className="grid grid-cols-2 gap-3 text-sm">
            <div>
              <p className="text-muted">Ciclo</p>
              <p className="font-medium">{cycleText(editingPlan.billing_cycle)}</p>
            </div>
            <div>
              <p className="text-muted">Duracao</p>
              <p className="font-medium">{editingPlan.duration_months} mes(es)</p>
            </div>
          </div>
          <label className="field lg:col-span-3" htmlFor="plan-description">
            Descricao
            <textarea
              id="plan-description"
              rows={3}
              value={form.description}
              onChange={(event) => setForm({ ...form, description: event.target.value })}
            />
          </label>
          {updatePlan.error && <div className="alert-error lg:col-span-3">{updatePlan.error.message}</div>}
          <div className="flex flex-wrap gap-3 lg:col-span-3">
            <button className="btn-primary" disabled={updatePlan.isPending}>
              <CheckCircle2 className="h-4 w-4" />
              Salvar plano
            </button>
            <button className="btn-secondary" type="button" onClick={() => setEditingPlan(null)}>
              Cancelar
            </button>
          </div>
        </form>
      )}
    </section>
  );
}
