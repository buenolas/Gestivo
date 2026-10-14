import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Trash2 } from "lucide-react";
import { apiFetch } from "../api";
import { typeText } from "../format";
import type { Category } from "../types";

export function CategoriesPage({ canManage = true }: { canManage?: boolean }) {
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
    <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,22.5rem)_minmax(0,1fr)]">
      <form className="panel min-w-0 space-y-4" onSubmit={onSubmit}>
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
        <button className="btn-primary w-full sm:w-auto" disabled={create.isPending}>Salvar categoria</button>
      </form>

      <div className="panel min-w-0">
        <div className="table-header">
          <h2 className="panel-title">Categorias</h2>
          {categories.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {categories.isError && <div className="alert-error">{categories.error.message}</div>}
        {categories.isLoading ? (
          <div className="screen-state mt-4">Carregando categorias...</div>
        ) : categories.isError ? null :
          (categories.data ?? []).length === 0 ? (
          <div className="screen-state mt-4">
            Nenhuma categoria cadastrada. Use o formulário para criar a primeira.
          </div>
        ) : (
        <div className="table-wrap responsive-cards">
          <table aria-label="Categorias financeiras">
            <thead className="sr-only sm:not-sr-only">
              <tr>
                <th scope="col">Nome</th>
                <th scope="col">Tipo</th>
                <th scope="col">Status</th>
                <th scope="col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {(categories.data ?? []).map((category) => (
                <tr key={category.id}>
                  <td data-label="Nome" data-primary="true">{category.name}</td>
                  <td data-label="Tipo">{typeText(category.type)}</td>
                  <td data-label="Status">{category.is_active ?"Ativa" : "Inativa"}</td>
                  <td data-actions className="text-right">
                    {canManage && category.is_active && (
                      <button className="icon-btn" type="button" aria-label={`Desativar categoria: ${category.name}`} onClick={() => remove.mutate(category.id)}>
                        <Trash2 className="h-4 w-4" />
                      </button>
                    )}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        )}
      </div>
    </section>
  );
}
