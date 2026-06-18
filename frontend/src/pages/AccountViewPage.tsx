import { useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { CheckCircle2 } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money, statusText } from "../format";
import type { Contact, Transaction } from "../types";

export function AccountViewPage({ kind }: { kind: "payables" | "receivables" }) {
  const queryClient = useQueryClient();
  const isPayable = kind === "payables";
  const [filters, setFilters] = useState({ contact_id: "" });
  const query = new URLSearchParams();
  if (filters.contact_id) query.set("contact_id", filters.contact_id);
  const list = useQuery({
    queryKey: [kind, filters],
    queryFn: () => apiFetch<Transaction[]>(`/${kind}${query.toString() ? `?${query}` : ""}`),
  });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: () => apiFetch<Contact[]>("/contacts"),
  });
  const contactById = new Map((contacts.data ?? []).map((contact) => [contact.id, contact.name]));
  const settle = useMutation({
    mutationFn: (id: string) =>
      apiFetch<Transaction>(`/${kind}/${id}/${isPayable ?"pay" : "receive"}`, {
        method: "POST",
        body: JSON.stringify({}),
      }),
    onSuccess: () => queryClient.invalidateQueries(),
  });

  return (
    <section className="panel">
      <div className="table-header">
        <div>
          <h2 className="panel-title">{isPayable ?"Contas a pagar" : "Contas a receber"}</h2>
          <p className="section-subtitle">Visão filtrada dos lançamentos financeiros.</p>
        </div>
        <div className="grid w-full gap-2 sm:w-64">
          <select value={filters.contact_id} onChange={(event) => setFilters({ ...filters, contact_id: event.target.value })}>
            <option value="">Todos contatos</option>
            {(contacts.data ?? []).map((contact) => (
              <option key={contact.id} value={contact.id}>{contact.name}</option>
            ))}
          </select>
        </div>
      </div>
      {list.isLoading && <div className="screen-state">Carregando...</div>}
      {list.isError && <div className="alert-error">{list.error.message}</div>}
      <div className="table-wrap">
        <table>
          <thead>
            <tr>
              <th>Descrição</th>
              <th>Contato</th>
              <th>Status</th>
              <th>Competência</th>
              <th>Vencimento</th>
              <th className="text-right">Valor</th>
              <th></th>
            </tr>
          </thead>
          <tbody>
            {(list.data ?? []).map((item) => (
              <tr key={item.id}>
                <td>{item.description}</td>
                <td>{item.contact_id ? contactById.get(item.contact_id) ?? "-" : "-"}</td>
                <td>{statusText(item.status)}</td>
                <td>{dateText(item.competence_date)}</td>
                <td>{dateText(item.due_date)}</td>
                <td className="text-right">{money(item.amount)}</td>
                <td className="text-right">
                  {item.status === "pending" && (
                    <button className="icon-btn" title={isPayable ?"Pagar" : "Receber"} onClick={() => settle.mutate(item.id)}>
                      <CheckCircle2 className="h-4 w-4" />
                    </button>
                  )}
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </section>
  );
}
