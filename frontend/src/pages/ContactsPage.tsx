import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { apiFetch } from "../api";
import { typeText } from "../format";
import type { Contact } from "../types";

export function ContactsPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", type: "both" });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: () => apiFetch<Contact[]>("/contacts"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Contact>("/contacts", {
        method: "POST",
        body: JSON.stringify({ ...form, is_active: true }),
      }),
    onSuccess: async () => {
      setForm({ name: "", type: "both" });
      await queryClient.invalidateQueries({ queryKey: ["contacts"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch<Contact>(`/contacts/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["contacts"] }),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form className="panel space-y-4" onSubmit={onSubmit}>
        <h2 className="panel-title">Novo contato</h2>
        <label className="field" htmlFor="contact-name">
          Nome
          <input id="contact-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="field" htmlFor="contact-type">
          Tipo
          <select id="contact-type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
            <option value="customer">Cliente</option>
            <option value="supplier">Fornecedor</option>
            <option value="both">Ambos</option>
          </select>
        </label>
        {create.error && <div className="alert-error">{create.error.message}</div>}
        <button className="btn-primary" disabled={create.isPending}>Salvar contato</button>
      </form>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Contatos</h2>
          {contacts.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {contacts.isError && <div className="alert-error">{contacts.error.message}</div>}
        <div className="table-wrap">
          <table>
            <thead>
              <tr>
                <th>Nome</th>
                <th>Tipo</th>
                <th>Status</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {(contacts.data ?? []).map((contact) => (
                <tr key={contact.id}>
                  <td>{contact.name}</td>
                  <td>{typeText(contact.type)}</td>
                  <td>{contact.is_active ? "Ativo" : "Inativo"}</td>
                  <td className="text-right">
                    {contact.is_active && (
                      <button className="icon-btn" title="Desativar" onClick={() => remove.mutate(contact.id)}>
                        <Trash2 className="h-4 w-4" />
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
