import { FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { ChevronRight, Trash2 } from "lucide-react";
import { apiFetch } from "../api";
import type { Category } from "../types";

export function CategoriesPage({ canManage = true }: { canManage?: boolean }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ name: "", parent_id: "" });
  const [expandedParentIds, setExpandedParentIds] = useState<Set<string>>(() => new Set());
  const categories = useQuery({
    queryKey: ["categories"],
    queryFn: () => apiFetch<Category[]>("/financial-categories"),
  });
  const allCategories = categories.data ?? [];
  const categoryById = new Map(allCategories.map((category) => [category.id, category]));
  const activeParents = allCategories.filter((category) => category.is_active && !category.parent_id);
  const childrenByParentId = new Map<string, Category[]>();
  for (const category of allCategories) {
    if (!category.parent_id) continue;
    const children = childrenByParentId.get(category.parent_id) ?? [];
    children.push(category);
    childrenByParentId.set(category.parent_id, children);
  }
  const displayCategories = allCategories
    .filter((category) => !category.parent_id)
    .flatMap((parent) => [
      parent,
      ...(expandedParentIds.has(parent.id) ? childrenByParentId.get(parent.id) ?? [] : []),
    ]);

  const create = useMutation({
    mutationFn: () =>
      apiFetch<Category>("/financial-categories", {
        method: "POST",
        body: JSON.stringify({
          name: form.name,
          parent_id: form.parent_id || null,
          is_active: true,
        }),
      }),
    onSuccess: async () => {
      setForm({ name: "", parent_id: "" });
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

  function toggleSubcategories(parentId: string) {
    setExpandedParentIds((current) => {
      const next = new Set(current);
      if (next.has(parentId)) next.delete(parentId);
      else next.add(parentId);
      return next;
    });
  }

  function confirmDeactivation(category: Category) {
    const activeChildren = allCategories.filter(
      (item) => item.parent_id === category.id && item.is_active,
    ).length;
    const detail = activeChildren > 0
      ? ` Também serão desativadas ${activeChildren} subcategorias ativas.`
      : "";
    const confirmed = window.confirm(
      `Desativar a categoria ${category.name}?${detail} Lançamentos existentes serão preservados.`,
    );
    if (confirmed) remove.mutate(category.id);
  }

  return (
    <section className="grid min-w-0 gap-5 xl:grid-cols-[minmax(0,22.5rem)_minmax(0,1fr)]">
      <form className="panel min-w-0 space-y-4" onSubmit={onSubmit}>
        <h2 className="panel-title">Nova categoria</h2>
        <label className="field" htmlFor="category-name">
          Nome
          <input id="category-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
        </label>
        <label className="field" htmlFor="category-parent">
          Subcategoria de (opcional)
          <select id="category-parent" value={form.parent_id} onChange={(event) => setForm({ ...form, parent_id: event.target.value })}>
            <option value="">Nenhuma — categoria principal</option>
            {activeParents.map((category) => (
              <option key={category.id} value={category.id}>{category.name}</option>
            ))}
          </select>
        </label>
        <p className="text-xs leading-5 text-muted">Subcategorias ajudam a detalhar uma categoria principal e ficam limitadas a um nível.</p>
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
                <th scope="col">Categoria</th>
                <th scope="col">Nível</th>
                <th scope="col">Status</th>
                <th scope="col">Ações</th>
              </tr>
            </thead>
            <tbody>
              {displayCategories.map((category) => (
                <tr key={category.id}>
                  <td data-label="Categoria" data-primary="true">
                    <span className="flex min-w-0 items-center gap-2">
                      {category.parent_id ? (
                        <span className="ml-4 text-muted" aria-hidden="true">↳</span>
                      ) : childrenByParentId.has(category.id) ? (
                        <button
                          className="icon-btn h-7 w-7 shrink-0 border-0 shadow-none"
                          type="button"
                          aria-label={`${expandedParentIds.has(category.id) ? "Ocultar" : "Mostrar"} subcategorias de ${category.name}`}
                          aria-expanded={expandedParentIds.has(category.id)}
                          onClick={() => toggleSubcategories(category.id)}
                        >
                          <ChevronRight
                            className={`h-4 w-4 transition-transform duration-150 ${expandedParentIds.has(category.id) ? "rotate-90" : ""}`}
                            aria-hidden="true"
                          />
                        </button>
                      ) : (
                        <span className="h-7 w-7 shrink-0" aria-hidden="true" />
                      )}
                      <span className={category.parent_id ? "text-muted" : "font-semibold"}>
                        {category.name}
                      </span>
                    </span>
                  </td>
                  <td data-label="Nível">
                    {category.parent_id
                      ? `Subcategoria de ${categoryById.get(category.parent_id)?.name ?? "categoria removida"}`
                      : "Principal"}
                  </td>
                  <td data-label="Status">{category.is_active ?"Ativa" : "Inativa"}</td>
                  <td data-actions className="text-right">
                    {canManage && category.is_active && (
                      <button className="icon-btn" type="button" aria-label={`Desativar categoria: ${category.name}`} onClick={() => confirmDeactivation(category)}>
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
