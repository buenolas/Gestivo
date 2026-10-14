import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ArrowDownRight, ArrowUpRight, Pencil, TrendingUp, XCircle } from "lucide-react";
import { apiFetch } from "../api";
import { FilterDisclosure } from "../components/FilterDisclosure";
import { currencyInputToDecimal, dateText, formatCurrencyInput, money, typeText } from "../format";
import type { CashFlow, Contact, EmployeeOption, Transaction, TransactionType, User } from "../types";

const today = new Date().toISOString().slice(0, 10);

function Metric({
  icon: Icon,
  label,
  value,
  tone = "neutral",
}: {
  icon: typeof TrendingUp;
  label: string;
  value: string;
  tone?: "neutral" | "good" | "bad";
}) {
  const toneClass =
    tone === "good"
      ? "bg-emerald-50 text-emerald-700"
      : tone === "bad"
        ? "bg-rose-50 text-rose-700"
        : "bg-mint text-brand";

  return (
    <div className="metric">
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-muted">{label}</p>
          <strong className="mt-3 block text-2xl font-bold tracking-tight text-ink">{value}</strong>
        </div>
        <span className={`rounded-md p-2 ${toneClass}`}>
          <Icon className="h-4 w-4" />
        </span>
      </div>
    </div>
  );
}

export function CashFlowPage({ user }: { user: User }) {
  const queryClient = useQueryClient();
  const [editingId, setEditingId] = useState<string | null>(null);
  const [form, setForm] = useState({
    description: "",
    amount: "0,00",
    type: "expense" as TransactionType,
    competence_date: today,
    contact_id: "",
    employee_id: "",
    notes: "",
  });
  const [filters, setFilters] = useState({
    type: "",
    contact_id: "",
    employee_id: "",
    start_date: "",
    end_date: "",
    search: "",
  });

  const query = new URLSearchParams();
  if (filters.type) query.set("type", filters.type);
  if (filters.contact_id) query.set("contact_id", filters.contact_id);
  if (filters.employee_id) query.set("employee_id", filters.employee_id);
  if (filters.start_date) query.set("start_date", filters.start_date);
  if (filters.end_date) query.set("end_date", filters.end_date);
  if (filters.search) query.set("search", filters.search);

  const cashFlow = useQuery({
    queryKey: ["cash-flow", filters],
    queryFn: () => apiFetch<CashFlow>(`/cash-flow${query.toString() ? `?${query}` : ""}`),
  });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: () => apiFetch<Contact[]>("/contacts"),
  });
  const employees = useQuery({
    queryKey: ["employee-options"],
    queryFn: () => apiFetch<EmployeeOption[]>("/employees/options"),
  });
  const contactById = new Map((contacts.data ?? []).map((contact) => [contact.id, contact.name]));
  const employeeById = new Map((employees.data ?? []).map((employee) => [employee.id, employee.name]));
  const activeFilterCount = Object.values(filters).filter(Boolean).length;

  const create = useMutation({
    mutationFn: () =>
      apiFetch("/cash-flow", {
        method: "POST",
        body: JSON.stringify({
          description: form.description,
          amount: currencyInputToDecimal(form.amount),
          type: form.type,
          competence_date: form.competence_date,
          contact_id: form.contact_id || null,
          employee_id: form.employee_id || null,
          notes: form.notes || null,
        }),
    }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["cash-flow"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const update = useMutation({
    mutationFn: () =>
      apiFetch(`/cash-flow/${editingId}`, {
        method: "PATCH",
        body: JSON.stringify({
          description: form.description,
          amount: currencyInputToDecimal(form.amount),
          type: form.type,
          competence_date: form.competence_date,
          contact_id: form.contact_id || null,
          employee_id: form.employee_id || null,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["cash-flow"] });
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
      description: "",
      amount: "0,00",
      type: "expense",
      competence_date: today,
      contact_id: "",
      employee_id: "",
      notes: "",
    });
  }

  function startEditing(item: Transaction) {
    setEditingId(item.id);
    setForm({
      description: item.description,
      amount: formatCurrencyInput(item.amount),
      type: item.type,
      competence_date: item.competence_date,
      contact_id: item.contact_id ?? "",
      employee_id: item.employee_id ?? "",
      notes: item.notes ?? "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function canEdit(item: Transaction) {
    return user.role === "company_admin" || item.created_by === user.id;
  }

  const summary = cashFlow.data?.summary ?? {
    income_total: "0.00",
    expense_total: "0.00",
    result: "0.00",
  };

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <div className="lg:col-span-4">
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">Dinheiro físico</p>
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="panel-title">
              {editingId ? "Editar movimentação de caixa" : "Nova movimentação de caixa"}
            </h2>
            {editingId && (
              <button className="btn-ghost" type="button" onClick={resetForm}>
                <XCircle className="h-4 w-4" />
                Cancelar edição
              </button>
            )}
          </div>
        </div>
        <label className="field lg:col-span-2" htmlFor="cash-description">
          Descrição
          <input id="cash-description" required minLength={2} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        <label className="field" htmlFor="cash-amount">
          Valor
          <input id="cash-amount" required inputMode="numeric" value={form.amount} onChange={(event) => setForm({ ...form, amount: formatCurrencyInput(event.target.value) })} />
        </label>
        <label className="field" htmlFor="cash-type">
          Tipo
          <select id="cash-type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value as TransactionType })}>
            <option value="expense">Saída</option>
            <option value="income">Entrada</option>
          </select>
        </label>
        <label className="field" htmlFor="cash-date">
          Data
          <input id="cash-date" required type="date" value={form.competence_date} onChange={(event) => setForm({ ...form, competence_date: event.target.value })} />
        </label>
        <label className="field" htmlFor="cash-contact">
          Cliente/Fornecedor
          <select id="cash-contact" value={form.contact_id} onChange={(event) => setForm({ ...form, contact_id: event.target.value })}>
            <option value="">Sem cliente/fornecedor</option>
            {(contacts.data ?? []).filter((contact) => contact.is_active).map((contact) => (
              <option key={contact.id} value={contact.id}>{contact.name}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="cash-employee">
          Funcionário
          <select id="cash-employee" value={form.employee_id} onChange={(event) => setForm({ ...form, employee_id: event.target.value })}>
            <option value="">Sem funcionário</option>
            {(employees.data ?? []).filter((employee) => employee.status === "active").map((employee) => (
              <option key={employee.id} value={employee.id}>{employee.name}</option>
            ))}
          </select>
        </label>
        <label className="field lg:col-span-2" htmlFor="cash-notes">
          Observações
          <input id="cash-notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending || update.isPending}>
            {editingId ? "Salvar alterações" : "Salvar no caixa"}
          </button>
        </div>
        {(create.error || update.error) && (
          <div className="alert-error lg:col-span-4">
            {create.error?.message ?? update.error?.message}
          </div>
        )}
      </form>

      <div className="grid gap-4 md:grid-cols-3">
        <Metric icon={ArrowUpRight} label="Entradas de caixa" value={money(summary.income_total)} tone="good" />
        <Metric icon={ArrowDownRight} label="Saídas de caixa" value={money(summary.expense_total)} tone="bad" />
        <Metric icon={TrendingUp} label="Resultado do caixa" value={money(summary.result)} />
      </div>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Movimentações de caixa</h2>
        </div>
        <FilterDisclosure
          activeCount={activeFilterCount}
          hint="Refine por tipo, cliente ou fornecedor, funcionário, período ou descrição."
          onClear={() => setFilters({ type: "", contact_id: "", employee_id: "", start_date: "", end_date: "", search: "" })}
        >
          <label className="field" htmlFor="cash-filter-type">
            Tipo
            <select id="cash-filter-type" value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })}>
              <option value="">Entradas e saídas</option>
              <option value="income">Entradas</option>
              <option value="expense">Saídas</option>
            </select>
          </label>
          <label className="field" htmlFor="cash-filter-contact">
            Cliente/fornecedor
            <select id="cash-filter-contact" value={filters.contact_id} onChange={(event) => setFilters({ ...filters, contact_id: event.target.value })}>
              <option value="">Todos os contatos</option>
              {(contacts.data ?? []).map((contact) => (
                <option key={contact.id} value={contact.id}>{contact.name}</option>
              ))}
            </select>
          </label>
          <label className="field" htmlFor="cash-filter-employee">
            Funcionário
            <select id="cash-filter-employee" value={filters.employee_id} onChange={(event) => setFilters({ ...filters, employee_id: event.target.value })}>
              <option value="">Todos os funcionários</option>
              {(employees.data ?? []).map((employee) => (
                <option key={employee.id} value={employee.id}>{employee.name}</option>
              ))}
            </select>
          </label>
          <label className="field" htmlFor="cash-filter-start-date">
            Competência a partir de
            <input id="cash-filter-start-date" type="date" value={filters.start_date} onChange={(event) => setFilters({ ...filters, start_date: event.target.value })} />
          </label>
          <label className="field" htmlFor="cash-filter-end-date">
            Competência até
            <input id="cash-filter-end-date" type="date" value={filters.end_date} onChange={(event) => setFilters({ ...filters, end_date: event.target.value })} />
          </label>
          <label className="field sm:col-span-2" htmlFor="cash-filter-search">
            Buscar movimentações
            <input id="cash-filter-search" type="search" placeholder="Descrição, cliente ou funcionário" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
          </label>
        </FilterDisclosure>
        {cashFlow.isError && <div className="alert-error">{cashFlow.error.message}</div>}
        <div className="table-wrap responsive-cards">
          <table aria-label="Movimentações de caixa">
            <thead className="sr-only sm:not-sr-only">
              <tr>
                <th scope="col">Data</th>
                <th scope="col">Descrição</th>
                <th scope="col">Cliente/Fornecedor</th>
                <th scope="col">Funcionário</th>
                <th scope="col">Tipo</th>
                <th scope="col" className="text-right">Valor</th>
                <th scope="col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(cashFlow.data?.items ?? []).map((item) => (
                <tr key={item.id}>
                  <td data-label="Data">{dateText(item.competence_date)}</td>
                  <td data-label="Descrição" data-primary="true">{item.description}</td>
                  <td data-label="Cliente/Fornecedor">{item.contact_id ? contactById.get(item.contact_id) ?? "-" : "-"}</td>
                  <td data-label="Funcionário">{item.employee_id ? employeeById.get(item.employee_id) ?? "-" : "-"}</td>
                  <td data-label="Tipo">{typeText(item.type)}</td>
                  <td data-label="Valor" className="text-right font-semibold">{money(item.amount)}</td>
                  <td data-actions className="text-right">
                    {canEdit(item) && (
                      <button className="icon-btn" type="button" aria-label={`Editar movimentação: ${item.description}`} onClick={() => startEditing(item)}>
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
