import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { apiFetch } from "../api";
import { typeText } from "../format";
import type { Category } from "../types";

export function CategoriesPage() {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", type: "expense" });
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<Category[]>("/financial-categories"),
  });

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Category>("/financial-categories", {
        method: "POST",
        body: JSON.stringify({ ...form, is_active: true }),
      }),
    onSuccess: async () => {
      setForm({ name: "", type: "expense" });
      await queryClient.invalidateQueries({ queryKey: ["categories"] });
    },
  });

  const remove = useMutation({
    mutationFn: (id: string) => apiFetch<Category>(`/financial-categories/${id}`, { method: "DELETE" }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["categories"] }),
  });

  function onSubmit(event: FormEvent) {
    event.preventDefault();
    create.mutate();
  }

  return (
    <section className="grid gap-5 xl:grid-cols-[360px_1fr]">
      <form className="panel space-y-4" onSubmit={onSubmit}>
        <h2 className="panel-title">Nova categoria</h2>
        <label className="field" htmlFor="category-name">
          Nome
          <input id="category-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="field" htmlFor="category-type">
          Tipo
          <select id="category-type" value={form.type} onChange={(event) => setForm({ ...form, type: event.target.value })}>
            <option value="expense">Saída</option>
            <option value="income">Entrada</option>
          </select>
        </label>
        {create.error && <div className="alert-error">{create.error.message}</div>}
        <button className="btn-primary" disabled={create.isPending}>Salvar categoria</button>
      </form>

      <div className="panel">
        <div className="table-header">
          <h2 className="panel-title">Categorias</h2>
          {categories.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {categories.isError && <div className="alert-error">{categories.error.message}</div>}
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
              {(categories.data ?? []).map((category) => (
                <tr key={category.id}>
                  <td>{category.name}</td>
                  <td>{typeText(category.type)}</td>
                  <td>{category.is_active ? "Ativa" : "Inativa"}</td>
                  <td className="text-right">
                    {category.is_active && (
                      <button className="icon-btn" title="Desativar" onClick={() => remove.mutate(category.id)}>
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
