import { FormEvent, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { PackagePlus, Pencil, XCircle } from "lucide-react";
import { apiFetch } from "../api";
import { currencyInputToDecimal, dateText, formatCurrencyInput, money, statusText } from "../format";
import type { EmployeeOption, Transaction, User } from "../types";

const today = new Date().toISOString().slice(0, 10);

function normalizeDecimalInput(value: string) {
  return value.trim().replace(",", ".");
}

function toCurrencyNumber(value: string) {
  const parsed = Number(currencyInputToDecimal(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

function toNumber(value: string) {
  const parsed = Number(normalizeDecimalInput(value));
  return Number.isFinite(parsed) ? parsed : 0;
}

export function ProductOutputsPage({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    employee_id: "",
    product_name: "",
    unit_price: "0,00",
    quantity: "",
    unit: "un",
    competence_date: today,
    notes: "",
  });
  const [filters, setFilters] = useState({ employee_id: "" });
  const query = new URLSearchParams();
  if (filters.employee_id) query.set("employee_id", filters.employee_id);

  const outputs = useQuery({
    queryKey: ["product-outputs", filters],
    queryFn: () => apiFetch<Transaction[]>(`/product-outputs${query.toString() ? `?${query}` : ""}`),
  });
  const employees = useQuery({
    queryKey: ["employee-options"],
    queryFn: () => apiFetch<EmployeeOption[]>("/employees/options"),
  });
  const employeeById = new Map((employees.data ?? []).map((employee) => [employee.id, employee.name]));

  const calculatedTotal = useMemo(() => {
    return toCurrencyNumber(form.unit_price) * toNumber(form.quantity);
  }, [form.unit_price, form.quantity]);

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Transaction>("/product-outputs", {
        method: "POST",
        body: JSON.stringify({
          employee_id: form.employee_id,
          product_name: form.product_name,
          unit_price: currencyInputToDecimal(form.unit_price),
          quantity: normalizeDecimalInput(form.quantity),
          unit: form.unit || "un",
          competence_date: form.competence_date,
          notes: form.notes || null,
        }),
    }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["product-outputs"] });
      await queryClient.invalidateQueries({ queryKey: ["receivables"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const update = useMutation({
    mutationFn: () =>
      apiFetch<Transaction>(`/product-outputs/${editingId}`, {
        method: "PATCH",
        body: JSON.stringify({
          employee_id: form.employee_id,
          product_name: form.product_name,
          unit_price: currencyInputToDecimal(form.unit_price),
          quantity: normalizeDecimalInput(form.quantity),
          unit: form.unit || "un",
          competence_date: form.competence_date,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["product-outputs"] });
      await queryClient.invalidateQueries({ queryKey: ["receivables"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    if (editingId) update.mutate();
    else create.mutate();
  }

  function resetForm() {
    setEditingId(null);
    setForm({
      employee_id: "",
      product_name: "",
      unit_price: "0,00",
      quantity: "",
      unit: "un",
      competence_date: today,
      notes: "",
    });
  }

  function startEditing(item: Transaction) {
    setEditingId(item.id);
    setForm({
      employee_id: item.employee_id ?? "",
      product_name: item.product_name ?? item.description,
      unit_price: formatCurrencyInput(item.product_unit_price),
      quantity: item.product_quantity ?? "",
      unit: item.product_unit ?? "un",
      competence_date: item.competence_date,
      notes: item.notes ?? "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function canEdit(item: Transaction) {
    return user.role === "company_admin" || item.created_by === user.id;
  }

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <div className="flex items-start gap-3 lg:col-span-4">
          <span className="rounded-md bg-mint p-2 text-brand">
            <PackagePlus className="h-5 w-5" />
          </span>
          <div>
            <p className="text-xs font-semibold uppercase tracking-wide text-accent">Valor a receber</p>
            <div className="flex flex-wrap items-center gap-3">
              <h2 className="panel-title">
                {editingId ? "Editar saída de produto" : "Nova saída de produto"}
              </h2>
              {editingId && (
                <button className="btn-ghost" type="button" onClick={resetForm}>
                  <XCircle className="h-4 w-4" />
                  Cancelar edição
                </button>
              )}
            </div>
          </div>
        </div>
        <label className="field" htmlFor="output-employee">
          Funcionário
          <select id="output-employee" required value={form.employee_id} onChange={(event) => setForm({ ...form, employee_id: event.target.value })}>
            <option value="">Selecione</option>
            {(employees.data ?? []).filter((employee) => employee.status === "active").map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.name}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="output-product">
          Produto
          <input id="output-product" required minLength={2} value={form.product_name} onChange={(event) => setForm({ ...form, product_name: event.target.value })} />
        </label>
        <label className="field" htmlFor="output-price">
          Valor por unidade/kg
          <input id="output-price" required inputMode="numeric" value={form.unit_price} onChange={(event) => setForm({ ...form, unit_price: formatCurrencyInput(event.target.value) })} />
        </label>
        <label className="field" htmlFor="output-quantity">
          Quantidade/peso
          <input id="output-quantity" required inputMode="decimal" placeholder="1,5" value={form.quantity} onChange={(event) => setForm({ ...form, quantity: event.target.value })} />
        </label>
        <label className="field" htmlFor="output-unit">
          Unidade
          <select id="output-unit" value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })}>
            <option value="un">Unidade</option>
            <option value="kg">Kg</option>
          </select>
        </label>
        <label className="field" htmlFor="output-date">
          Data
          <input id="output-date" required type="date" value={form.competence_date} onChange={(event) => setForm({ ...form, competence_date: event.target.value })} />
        </label>
        <label className="field lg:col-span-2" htmlFor="output-notes">
          Observações
          <input id="output-notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        <div className="metric flex items-center justify-between gap-3 lg:col-span-3">
          <span className="text-sm font-semibold text-muted">Total a receber</span>
          <strong className="text-xl font-bold text-ink">{money(calculatedTotal)}</strong>
        </div>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending || update.isPending}>
            {editingId ? "Salvar alterações" : "Registrar saída"}
          </button>
        </div>
        {(create.error || update.error) && (
          <div className="alert-error lg:col-span-4">
            {create.error?.message ?? update.error?.message}
          </div>
        )}
      </form>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Saídas registradas</h2>
          <div className="grid w-full gap-2 sm:w-64">
            <select value={filters.employee_id} onChange={(event) => setFilters({ ...filters, employee_id: event.target.value })}>
              <option value="">Todos funcionários</option>
              {(employees.data ?? []).map((employee) => (
                <option key={employee.id} value={employee.id}>{employee.name}</option>
              ))}
            </select>
          </div>
        </div>
        {outputs.isError && <div className="alert-error">{outputs.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Data</th>
                <th>Funcionário</th>
                <th>Produto</th>
                <th>Status</th>
                <th className="text-right">Valor unitário/kg</th>
                <th className="text-right">Qtd/peso</th>
                <th className="text-right">Total a receber</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(outputs.data ?? []).map((item) => (
                <tr key={item.id}>
                  <td>{dateText(item.competence_date)}</td>
                  <td>{item.employee_id ? employeeById.get(item.employee_id) ?? "-" : "-"}</td>
                  <td>{item.product_name ?? item.description}</td>
                  <td>{statusText(item.status)}</td>
                  <td className="text-right">{money(item.product_unit_price)}</td>
                  <td className="text-right">{item.product_quantity ?? "-"} {item.product_unit ?? ""}</td>
                  <td className="text-right">{money(item.amount)}</td>
                  <td className="text-right">
                    {canEdit(item) && (
                      <button className="icon-btn" title="Editar" onClick={() => startEditing(item)}>
                        <Pencil className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
