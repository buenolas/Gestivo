import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Ban, CheckCircle2, Download, Pencil, XCircle } from "lucide-react";
import { apiFetch, apiUrl, getToken } from "../api";
import { currencyInputToDecimal, dateText, formatCurrencyInput, money, paymentMethodText, statusText, typeText } from "../format";
import type { Category, Contact, Transaction } from "../types";

const today = new Date().toISOString().slice(0, 10);
const paymentMethodOptions = [
  ["credit", "Credito"],
  ["debit", "Debito"],
  ["pix", "Pix"],
  ["boleto", "Boleto"],
  ["bank_transfer", "Transferencia"],
  ["cash", "Dinheiro"],
] as const;

export function TransactionsPage({ canManageAll = true }: { canManageAll?: boolean }) {
  const queryClient = useQueryClient();
  const [exportError, setExportError] = useState("");
  const [filters, setFilters] = useState({
    type: "",
    status: "",
    category_id: "",
    contact_id: "",
    payment_method: "",
    start_date: "",
    end_date: "",
    search: "",
  });
  const [form, setForm] = useState({
    description: "",
    amount: "0,00",
    type: "expense",
    competence_date: today,
    due_date: "",
    category_id: "",
    contact_id: "",
    payment_method: "",
    notes: "",
  });
  const [editingId, setEditingId] = useState<string | null>(null);
  const [settlingTransaction, setSettlingTransaction] = useState<Transaction | null>(null);
  const [settlePaymentMethod, setSettlePaymentMethod] = useState("");

  const query = new URLSearchParams({ source: "manual" });
  if (filters.type) query.set("type", filters.type);
  if (filters.status) query.set("status", filters.status);
  if (filters.category_id) query.set("category_id", filters.category_id);
  if (filters.contact_id) query.set("contact_id", filters.contact_id);
  if (filters.payment_method) query.set("payment_method", filters.payment_method);
  if (filters.start_date) query.set("start_date", filters.start_date);
  if (filters.end_date) query.set("end_date", filters.end_date);
  if (filters.search) query.set("search", filters.search);

  const transactions = useQuery({
    queryKey: ["transactions", filters],
    queryFn: () => apiFetch<Transaction[]>(`/financial-transactions${query.toString() ?`?${query}` : ""}`),
  });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<Category[]>("/financial-categories"),
  });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: () => apiFetch<Contact[]>("/contacts"),
  });
  const contactById = new Map((contacts.data ?? []).map((contact) => [contact.id, contact.name]));

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Transaction>("/financial-transactions", {
        method: "POST",
        body: JSON.stringify({
          description: form.description,
          amount: currencyInputToDecimal(form.amount),
          type: form.type,
          competence_date: form.competence_date,
          due_date: form.due_date || null,
          category_id: form.category_id || null,
          contact_id: form.contact_id || null,
          payment_method: form.payment_method || null,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["transactions"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const update = useMutation({
    mutationFn: () =>
      apiFetch<Transaction>(`/financial-transactions/${editingId}`, {
        method: "PATCH",
        body: JSON.stringify({
          description: form.description,
          amount: currencyInputToDecimal(form.amount),
          type: form.type,
          competence_date: form.competence_date,
          due_date: form.due_date || null,
          category_id: form.category_id || null,
          contact_id: form.contact_id || null,
          payment_method: form.payment_method || null,
          notes: form.notes || null,
        }),
      }),
    onSuccess: async () => {
      resetForm();
      await queryClient.invalidateQueries({ queryKey: ["transactions"] });
      await queryClient.invalidateQueries({ queryKey: ["dashboard"] });
    },
  });

  const settle = useMutation({
    mutationFn: ({ id, payment_method }: { id: string; payment_method: string }) =>
      apiFetch<Transaction>(`/financial-transactions/${id}/settle`, {
        method: "POST",
        body: JSON.stringify({ payment_method: payment_method || null }),
      }),
    onSuccess: async () => {
      setSettlingTransaction(null);
      setSettlePaymentMethod("");
      await queryClient.invalidateQueries();
    },
  });
  const cancel = useMutation({
    mutationFn: (id: string) => apiFetch<Transaction>(`/financial-transactions/${id}/cancel`, { method: "POST" }),
    onSuccess: () => queryClient.invalidateQueries(),
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
      due_date: "",
      category_id: "",
      contact_id: "",
      payment_method: "",
      notes: "",
    });
  }

  function startEditing(transaction: Transaction) {
    setEditingId(transaction.id);
    setForm({
      description: transaction.description,
      amount: formatCurrencyInput(transaction.amount),
      type: transaction.type,
      competence_date: transaction.competence_date,
      due_date: transaction.due_date ?? "",
      category_id: transaction.category_id ?? "",
      contact_id: transaction.contact_id ?? "",
      payment_method: transaction.payment_method ?? "",
      notes: transaction.notes ?? "",
    });
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  async function exportCsv() {
    setExportError("");
    const token = getToken();
    const response = await fetch(`${apiUrl}/exports/financial-transactions.csv${query.toString() ?`?${query}` : ""}`, {
      headers: token ?{ Authorization: `Bearer ${token}` } : {},
    });
    if (!response.ok) {
      const payload = await response.json().catch(() => null);
      setExportError(typeof payload?.detail === "string" ? payload.detail : "Nao foi possivel exportar os lancamentos.");
      return;
    }
    const blob = await response.blob();
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = "lancamentos-financeiros.csv";
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  }

  return (
    <section className="space-y-5">
      <form className="panel grid gap-4 lg:grid-cols-4" onSubmit={onSubmit}>
        <div className="flex flex-wrap items-center justify-between gap-3 lg:col-span-4">
          <h2 className="panel-title">
            {editingId ?"Editar lancamento" : "Novo lancamento"}
          </h2>
          {editingId && (
            <button className="btn-ghost" type="button" onClick={resetForm}>
              <XCircle className="h-4 w-4" />
              Cancelar edicao
            </button>
          )}
        </div>
        <label className="field lg:col-span-2" htmlFor="transaction-description">
          Descrição
          <input id="transaction-description" required minLength={2} value={form.description} onChange={(event) => setForm({ ...form, description: event.target.value })} />
        </label>
        <label className="field" htmlFor="transaction-amount">
          Valor
          <input id="transaction-amount" required inputMode="numeric" value={form.amount} onChange={(event) => setForm({ ...form, amount: formatCurrencyInput(event.target.value) })} />
        </label>
        <label className="field" htmlFor="transaction-type">
          Tipo
          <select id="transaction-type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
            <option value="expense">Saída</option>
            <option value="income">Entrada</option>
          </select>
        </label>
        <label className="field" htmlFor="transaction-competence-date">
          Competência
          <input id="transaction-competence-date" required type="date" value={form.competence_date} onChange={(event) => setForm({ ...form, competence_date: event.target.value })} />
        </label>
        <label className="field" htmlFor="transaction-due-date">
          Vencimento
          <input id="transaction-due-date" type="date" value={form.due_date} onChange={(event) => setForm({ ...form, due_date: event.target.value })} />
        </label>
        <label className="field" htmlFor="transaction-category">
          Categoria
          <select id="transaction-category" value={form.category_id} onChange={(event) => setForm({ ...form, category_id: event.target.value })}>
            <option value="">Sem categoria</option>
            {(categories.data ?? []).filter((item) => item.is_active).map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="transaction-contact">
          Cliente/Fornecedor
          <select id="transaction-contact" value={form.contact_id} onChange={(event) => setForm({ ...form, contact_id: event.target.value })}>
            <option value="">Sem cliente/fornecedor</option>
            {(contacts.data ?? []).filter((item) => item.is_active).map((contact) => (
              <option key={contact.id} value={contact.id}>{contact.name}</option>
            ))}
          </select>
        </label>
        <label className="field" htmlFor="transaction-payment-method">
          Forma de pagamento
          <select id="transaction-payment-method" value={form.payment_method} onChange={(event) => setForm({ ...form, payment_method: event.target.value })}>
            <option value="">Nao registrar</option>
            {paymentMethodOptions.map(([value, label]) => (
              <option key={value} value={value}>{label}</option>
            ))}
          </select>
        </label>
        <label className="field lg:col-span-2" htmlFor="transaction-notes">
          Observações
          <input id="transaction-notes" value={form.notes} onChange={(event) => setForm({ ...form, notes: event.target.value })} />
        </label>
        <div className="flex items-end">
          <button className="btn-primary w-full" disabled={create.isPending || update.isPending}>
            {editingId ?"Salvar alteracoes" : "Salvar"}
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
          <h2 className="panel-title">Lançamentos</h2>
          <div className="grid w-full gap-2 sm:w-auto sm:grid-cols-3 lg:grid-cols-9">
            <select value={filters.type} onChange={(event) => setFilters({ ...filters, type: event.target.value })}>
              <option value="">Todos os tipos</option>
              <option value="income">Entradas</option>
              <option value="expense">Saídas</option>
            </select>
            <select value={filters.status} onChange={(event) => setFilters({ ...filters, status: event.target.value })}>
              <option value="">Todos os status</option>
              <option value="pending">Pendentes</option>
              <option value="settled">Liquidados</option>
              <option value="canceled">Cancelados</option>
            </select>
            <select value={filters.category_id} onChange={(event) => setFilters({ ...filters, category_id: event.target.value })}>
              <option value="">Todas categorias</option>
              {(categories.data ?? []).map((category) => (
                <option key={category.id} value={category.id}>{category.name}</option>
              ))}
            </select>
            <select value={filters.contact_id} onChange={(event) => setFilters({ ...filters, contact_id: event.target.value })}>
              <option value="">Clientes/fornecedores</option>
              {(contacts.data ?? []).map((contact) => (
                <option key={contact.id} value={contact.id}>{contact.name}</option>
              ))}
            </select>
            <select value={filters.payment_method} onChange={(event) => setFilters({ ...filters, payment_method: event.target.value })}>
              <option value="">Todas as formas</option>
              {paymentMethodOptions.map(([value, label]) => (
                <option key={value} value={value}>{label}</option>
              ))}
            </select>
            <input type="date" value={filters.start_date} onChange={(event) => setFilters({ ...filters, start_date: event.target.value })} />
            <input type="date" value={filters.end_date} onChange={(event) => setFilters({ ...filters, end_date: event.target.value })} />
            <input placeholder="Buscar" value={filters.search} onChange={(event) => setFilters({ ...filters, search: event.target.value })} />
            {canManageAll && (
              <button className="btn-secondary inline-flex items-center justify-center gap-2" type="button" onClick={exportCsv}>
                <Download className="h-4 w-4" />
                CSV
              </button>
            )}
          </div>
        </div>
        {transactions.isError && <div className="alert-error">{transactions.error.message}</div>}
        {exportError && <div className="alert-error">{exportError}</div>}
        {settlingTransaction && (
          <div className="alert-warning mb-4 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
            <label className="field flex-1" htmlFor="settle-payment-method">
              Forma ao liquidar: {settlingTransaction.description}
              <select id="settle-payment-method" value={settlePaymentMethod} onChange={(event) => setSettlePaymentMethod(event.target.value)}>
                <option value="">Nao registrar</option>
                {paymentMethodOptions.map(([value, label]) => (
                  <option key={value} value={value}>{label}</option>
                ))}
              </select>
            </label>
            <div className="flex gap-2">
              <button className="btn-primary" type="button" disabled={settle.isPending} onClick={() => settle.mutate({ id: settlingTransaction.id, payment_method: settlePaymentMethod })}>
                Confirmar
              </button>
              <button className="btn-ghost" type="button" onClick={() => setSettlingTransaction(null)}>
                Cancelar
              </button>
            </div>
          </div>
        )}
        {settle.error && <div className="alert-error">{settle.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Descrição</th>
                <th>Cliente/Fornecedor</th>
                <th>Tipo</th>
                <th>Status</th>
                <th>Forma</th>
                <th>Competência</th>
                <th>Vencimento</th>
                <th className="text-right">Valor</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(transactions.data ?? []).map((transaction) => (
                <tr key={transaction.id}>
                  <td>{transaction.description}</td>
                  <td>{transaction.contact_id ? contactById.get(transaction.contact_id) ?? "-" : "-"}</td>
                  <td>{typeText(transaction.type)}</td>
                  <td>{statusText(transaction.status)}</td>
                  <td>{paymentMethodText(transaction.payment_method)}</td>
                  <td>{dateText(transaction.competence_date)}</td>
                  <td>{dateText(transaction.due_date)}</td>
                  <td className="text-right">{money(transaction.amount)}</td>
                  <td className="text-right">
                    <div className="inline-flex gap-2">
                      {transaction.status !== "canceled" && (
                        <button className="icon-btn" title="Editar" onClick={() => startEditing(transaction)}>
                          <Pencil className="h-4 w-4" />
                        </button>
                      )}
                      {canManageAll && transaction.status === "pending" && (
                        <>
                        <button className="icon-btn" title="Liquidar" onClick={() => {
                          setSettlingTransaction(transaction);
                          setSettlePaymentMethod(transaction.payment_method ?? "");
                        }}>
                          <CheckCircle2 className="h-4 w-4" />
                        </button>
                        <button className="icon-btn" title="Cancelar" onClick={() => cancel.mutate(transaction.id)}>
                          <Ban className="h-4 w-4" />
                        </button>
                        </>
                      )}
                    </div>
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
