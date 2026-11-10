import { Fragment, type FormEvent, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Archive, Boxes, Check, Pencil, Plus, X } from "lucide-react";
import { apiFetch } from "../api";
import { currencyInputToDecimal, dateText, formatCurrencyInput, money } from "../format";
import type { InventoryMovement, InventoryProduct } from "../types";

const initialProductForm = {
  name: "",
  sku: "",
  barcode: "",
  sale_price: "0,00",
  initial_stock: "0",
  unit: "un",
};

function quantityText(value: string) {
  const parsed = Number(value);
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(
    Number.isFinite(parsed) ? parsed : 0,
  );
}

export function InventoryPage({ canManage = true }: { canManage?: boolean }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState(initialProductForm);
  const [editingId, setEditingId] = useState<string | null>(null);
  const [adjustingId, setAdjustingId] = useState<string | null>(null);
  const [adjustment, setAdjustment] = useState({ quantity: "0", notes: "" });
  const products = useQuery({
    queryKey: ["inventory-products", canManage],
    queryFn: () => apiFetch<InventoryProduct[]>(`/inventory/products${canManage ? "?include_inactive=true" : ""}`),
  });
  const movements = useQuery({
    queryKey: ["inventory-movements"],
    queryFn: () => apiFetch<InventoryMovement[]>("/inventory/movements"),
  });

  const saveProduct = useMutation({
    mutationFn: () =>
      apiFetch<InventoryProduct>(editingId ? `/inventory/products/${editingId}` : "/inventory/products", {
        method: editingId ? "PATCH" : "POST",
        body: JSON.stringify({
          name: form.name,
          sku: form.sku || null,
          barcode: form.barcode || null,
          sale_price: currencyInputToDecimal(form.sale_price),
          unit: form.unit || "un",
          ...(!editingId ? { initial_stock: form.initial_stock || "0" } : {}),
        }),
      }),
    onSuccess: async () => {
      setEditingId(null);
      setForm(initialProductForm);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["inventory-products"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory-movements"] }),
        queryClient.invalidateQueries({ queryKey: ["pos-products"] }),
      ]);
    },
  });

  const update = useMutation({
    mutationFn: ({ id, patch }: { id: string; patch: Partial<InventoryProduct> }) =>
      apiFetch<InventoryProduct>(`/inventory/products/${id}`, {
        method: "PATCH",
        body: JSON.stringify(patch),
      }),
    onSuccess: async () => {
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["inventory-products"] }),
        queryClient.invalidateQueries({ queryKey: ["pos-products"] }),
      ]);
    },
  });

  const setStock = useMutation({
    mutationFn: (productId: string) =>
      apiFetch<InventoryProduct>(`/inventory/products/${productId}/stock`, {
        method: "POST",
        body: JSON.stringify({ quantity: adjustment.quantity, notes: adjustment.notes || null }),
      }),
    onSuccess: async () => {
      setAdjustingId(null);
      setAdjustment({ quantity: "0", notes: "" });
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["inventory-products"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory-movements"] }),
        queryClient.invalidateQueries({ queryKey: ["pos-products"] }),
      ]);
    },
  });

  function submitProduct(event: FormEvent) {
    event.preventDefault();
    saveProduct.mutate();
  }

  function startEditingProduct(product: InventoryProduct) {
    setAdjustingId(null);
    setEditingId(product.id);
    setForm({
      name: product.name,
      sku: product.sku ?? "",
      barcode: product.barcode ?? "",
      sale_price: formatCurrencyInput(product.sale_price),
      initial_stock: product.stock_quantity,
      unit: product.unit,
    });
  }

  function startStockAdjustment(product: InventoryProduct) {
    setEditingId(null);
    setForm(initialProductForm);
    setAdjustingId(product.id);
    setAdjustment({ quantity: product.stock_quantity, notes: "" });
  }

  return (
    <section className="space-y-5">
      <div>
        <h2 className="section-title">Estoque</h2>
        <p className="section-subtitle">Cadastre produtos e acompanhe a disponibilidade usada pelo PDV.</p>
      </div>

      <div className={canManage ? "grid gap-5 xl:grid-cols-[minmax(0,22rem)_minmax(0,1fr)]" : "grid gap-5"}>
        {canManage && (
          <form className="panel space-y-4" onSubmit={submitProduct}>
            <div className="flex items-center justify-between gap-3">
              <h3 className="panel-title">{editingId ? "Editar produto" : "Novo produto"}</h3>
              {editingId && <button className="btn-ghost px-2 py-1 text-xs" type="button" onClick={() => { setEditingId(null); setForm(initialProductForm); }}>Cancelar</button>}
            </div>
            <label className="field" htmlFor="inventory-name">
              Nome
              <input id="inventory-name" required minLength={2} value={form.name} onChange={(event) => setForm({ ...form, name: event.target.value })} />
            </label>
            <label className="field" htmlFor="inventory-sku">
              Código SKU <span className="font-normal text-muted">(opcional)</span>
              <input id="inventory-sku" value={form.sku} onChange={(event) => setForm({ ...form, sku: event.target.value })} />
            </label>
            <label className="field" htmlFor="inventory-barcode">
              Código de barras <span className="font-normal text-muted">(opcional)</span>
              <input id="inventory-barcode" inputMode="numeric" value={form.barcode} onChange={(event) => setForm({ ...form, barcode: event.target.value })} />
            </label>
            <div className="grid grid-cols-2 gap-3">
              <label className="field" htmlFor="inventory-price">
                Preço de venda
                <input id="inventory-price" required inputMode="numeric" value={form.sale_price} onChange={(event) => setForm({ ...form, sale_price: formatCurrencyInput(event.target.value) })} />
              </label>
              <label className="field" htmlFor="inventory-unit">
                Unidade
                <input id="inventory-unit" required maxLength={20} value={form.unit} onChange={(event) => setForm({ ...form, unit: event.target.value })} />
              </label>
            </div>
            {!editingId && (
              <>
                <label className="field" htmlFor="inventory-initial-stock">
                  Estoque inicial
                  <input id="inventory-initial-stock" type="number" min="0" step="0.001" required value={form.initial_stock} onChange={(event) => setForm({ ...form, initial_stock: event.target.value })} />
                </label>
                <p className="text-xs leading-5 text-muted">O estoque inicial também fica registrado no histórico de movimentações.</p>
              </>
            )}
            {saveProduct.error && <div className="alert-error">{saveProduct.error.message}</div>}
            <button className="btn-primary w-full sm:w-auto" disabled={saveProduct.isPending}>
              {editingId ? <Check className="h-4 w-4" /> : <Plus className="h-4 w-4" />}
              {saveProduct.isPending ? "Salvando..." : editingId ? "Salvar alterações" : "Cadastrar produto"}
            </button>
          </form>
        )}

        <div className="panel min-w-0">
          <div className="table-header">
            <div>
              <h3 className="panel-title">Produtos</h3>
              <p className="mt-1 text-xs text-muted">Produtos sem estoque ficam bloqueados para venda no PDV.</p>
            </div>
            {products.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
          </div>
          {products.isLoading && <div className="screen-state">Carregando produtos...</div>}
          {products.isError && <div className="alert-error">{products.error.message}</div>}
          {update.error && <div className="alert-error mb-3">{update.error.message}</div>}
          {products.data?.length === 0 && <div className="screen-state">Nenhum produto cadastrado ainda.</div>}
          <div className="table-wrap responsive-cards">
            <table>
              <thead>
                <tr>
                  <th>Produto</th>
                  <th>SKU</th>
                  <th>Código de barras</th>
                  <th className="text-right">Preço</th>
                  <th className="text-right">Disponível</th>
                  <th>Status</th>
                  {canManage && <th className="text-right">Ações</th>}
                </tr>
              </thead>
            <tbody>
                {(products.data ?? []).map((product) => (
                  <Fragment key={product.id}>
                    <tr key={product.id}>
                      <td data-label="Produto" data-primary="true">{product.name}</td>
                      <td data-label="SKU">{product.sku || "-"}</td>
                      <td data-label="Código de barras">{product.barcode || "-"}</td>
                      <td data-label="Preço" className="text-right">{money(product.sale_price)}</td>
                      <td data-label="Disponível" className="text-right">{quantityText(product.stock_quantity)} {product.unit}</td>
                      <td data-label="Status">{product.is_active ? "Ativo" : "Inativo"}</td>
                      {canManage && (
                        <td data-label="Ações" data-actions className="text-right">
                          {product.is_active && (
                            <>
                              <button className="icon-btn" type="button" title="Editar produto" aria-label={`Editar produto ${product.name}`} onClick={() => startEditingProduct(product)}>
                                <Pencil className="h-4 w-4" />
                              </button>
                              <button className="icon-btn ml-1" type="button" title="Ajustar estoque" aria-label={`Ajustar estoque de ${product.name}`} onClick={() => startStockAdjustment(product)}>
                                <Boxes className="h-4 w-4" />
                              </button>
                              <button className="icon-btn ml-1" type="button" title="Desativar produto" aria-label={`Desativar produto ${product.name}`} onClick={() => update.mutate({ id: product.id, patch: { is_active: false } })}>
                                <Archive className="h-4 w-4" />
                              </button>
                            </>
                          )}
                        </td>
                      )}
                    </tr>
                    {adjustingId === product.id && (
                      <tr key={`${product.id}-stock`}>
                        <td colSpan={canManage ? 7 : 6}>
                          <form className="grid items-end gap-3 rounded-lg bg-panel p-3 sm:grid-cols-[170px_1fr_auto_auto]" onSubmit={(event) => { event.preventDefault(); setStock.mutate(product.id); }}>
                            <label className="field" htmlFor={`stock-quantity-${product.id}`}>
                              Novo saldo ({product.unit})
                              <input id={`stock-quantity-${product.id}`} type="number" min="0" step="0.001" required value={adjustment.quantity} onChange={(event) => setAdjustment({ ...adjustment, quantity: event.target.value })} />
                            </label>
                            <label className="field" htmlFor={`stock-note-${product.id}`}>
                              Motivo do ajuste
                              <input id={`stock-note-${product.id}`} value={adjustment.notes} onChange={(event) => setAdjustment({ ...adjustment, notes: event.target.value })} placeholder="Ex.: reposição ou inventário" />
                            </label>
                            <button className="btn-primary" disabled={setStock.isPending} aria-label="Salvar saldo"><Check className="h-4 w-4" /> Salvar</button>
                            <button className="btn-secondary" type="button" onClick={() => setAdjustingId(null)} aria-label="Cancelar ajuste"><X className="h-4 w-4" /></button>
                            {setStock.error && <p className="alert-error sm:col-span-4">{setStock.error.message}</p>}
                          </form>
                        </td>
                      </tr>
                    )}
                  </Fragment>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      <div className="panel">
        <div className="table-header">
          <div>
            <h3 className="panel-title">Movimentações recentes</h3>
            <p className="mt-1 text-xs text-muted">Entradas, baixas de venda e ajustes de estoque.</p>
          </div>
          {movements.isFetching && <span className="text-sm text-muted">Atualizando...</span>}
        </div>
        {movements.isError && <div className="alert-error">{movements.error.message}</div>}
        {movements.data?.length === 0 && <div className="screen-state">Ainda não há movimentações.</div>}
        <div className="table-wrap responsive-cards">
          <table>
            <thead>
              <tr><th>Data</th><th>Produto</th><th>Movimento</th><th className="text-right">Variação</th><th className="text-right">Saldo após</th><th>Observação</th></tr>
            </thead>
            <tbody>
              {(movements.data ?? []).map((movement) => {
                const label = movement.movement_type === "sale" ? "Venda PDV" : movement.movement_type === "inbound" ? "Entrada" : "Ajuste";
                const delta = Number(movement.quantity_change);
                const deltaText = new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(delta);
                return (
                  <tr key={movement.id}>
                    <td data-label="Data">{dateText(movement.created_at)}</td>
                    <td data-label="Produto" data-primary="true">{movement.product_name}</td>
                    <td data-label="Movimento">{label}</td>
                    <td data-label="Variação" className="text-right">{delta > 0 ? "+" : ""}{deltaText}</td>
                    <td data-label="Saldo após" className="text-right">{quantityText(movement.stock_after)} {movement.product_unit}</td>
                    <td data-label="Observação">{movement.notes || "-"}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>
    </section>
  );
}
