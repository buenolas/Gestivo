import { useMemo, useRef, useState, type KeyboardEvent } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { Barcode, ChevronDown, FilePlus2, Minus, Plus, Search, ShoppingCart } from "lucide-react";
import { apiFetch } from "../api";
import { dateText, money } from "../format";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../components/ui/dialog";
import type { Contact, InventoryProduct, PaymentMethod, POSPricing, POSSale, POSSavedQuote } from "../types";

const paymentMethods: Array<{ value: PaymentMethod; label: string }> = [
  { value: "pix", label: "Pix" },
  { value: "cash", label: "Dinheiro" },
  { value: "credit", label: "Cartão de crédito" },
  { value: "debit", label: "Cartão de débito" },
  { value: "bank_transfer", label: "Transferência" },
  { value: "boleto", label: "Boleto" },
];

type CartProduct = Pick<InventoryProduct, "id" | "name" | "sku" | "barcode" | "sale_price" | "stock_quantity" | "unit">;
type CartEntry = { product: CartProduct; quantity: string };

function quantityText(value: string) {
  const parsed = Number(value);
  return new Intl.NumberFormat("pt-BR", { maximumFractionDigits: 3 }).format(
    Number.isFinite(parsed) ? parsed : 0,
  );
}

function decimalRequestValue(value: string) {
  const trimmed = value.trim();
  if (trimmed.includes(",")) return trimmed.replace(/\./g, "").replace(",", ".") || "0";
  return trimmed || "0";
}

function productSearchUrl(search: string) {
  return `/pos/products?search=${encodeURIComponent(search)}`;
}

export function POSPage() {
  const queryClient = useQueryClient();
  const searchInput = useRef<HTMLInputElement>(null);
  const quotesSection = useRef<HTMLDetailsElement>(null);
  const [search, setSearch] = useState("");
  const [scanMessage, setScanMessage] = useState("");
  const [cart, setCart] = useState<Record<string, CartEntry>>({});
  const [quoteId, setQuoteId] = useState<string | null>(null);
  const [paymentMethod, setPaymentMethod] = useState<PaymentMethod>("pix");
  const [contactId, setContactId] = useState("");
  const [notes, setNotes] = useState("");
  const [discountType, setDiscountType] = useState<"none" | "percentage" | "amount">("none");
  const [discountValue, setDiscountValue] = useState("0.00");
  const [checkoutOpen, setCheckoutOpen] = useState(false);
  const [quoteOpen, setQuoteOpen] = useState(false);
  const [quoteCustomer, setQuoteCustomer] = useState("");
  const [quoteContactId, setQuoteContactId] = useState("");
  const [quoteNotes, setQuoteNotes] = useState("");

  const searchTerm = search.trim();
  const products = useQuery({
    queryKey: ["pos-products", searchTerm],
    queryFn: () => apiFetch<InventoryProduct[]>(productSearchUrl(searchTerm)),
    enabled: searchTerm.length > 0,
  });
  const contacts = useQuery({
    queryKey: ["contacts"],
    queryFn: () => apiFetch<Contact[]>("/contacts"),
  });
  const savedQuotes = useQuery({
    queryKey: ["pos-quotes"],
    queryFn: () => apiFetch<POSSavedQuote[]>("/pos/quotes"),
  });

  const cartItems = useMemo(
    () => Object.entries(cart)
      .filter(([, entry]) => entry.quantity !== "" && Number(entry.quantity) > 0)
      .map(([product_id, entry]) => ({ product_id, quantity: entry.quantity })),
    [cart],
  );
  const normalizedDiscountValue = decimalRequestValue(discountValue);
  const pricing = useQuery({
    queryKey: ["pos-pricing", cartItems, discountType, normalizedDiscountValue, quoteId],
    queryFn: () => apiFetch<POSPricing>("/pos/quote", {
      method: "POST",
      body: JSON.stringify({
        items: cartItems,
        discount_type: discountType,
        discount_value: normalizedDiscountValue,
        quote_id: quoteId,
      }),
    }),
    enabled: cartItems.length > 0,
    retry: false,
  });

  const checkout = useMutation({
    mutationFn: () => apiFetch<POSSale>("/pos/sales", {
      method: "POST",
      body: JSON.stringify({
        items: cartItems,
        payment_method: paymentMethod,
        contact_id: contactId || null,
        notes: notes || null,
        discount_type: discountType,
        discount_value: normalizedDiscountValue,
        quote_id: quoteId,
      }),
    }),
    onSuccess: async () => {
      setCart({});
      setQuoteId(null);
      setContactId("");
      setNotes("");
      setDiscountType("none");
      setDiscountValue("0.00");
      setPaymentMethod("pix");
      setCheckoutOpen(false);
      await Promise.all([
        queryClient.invalidateQueries({ queryKey: ["pos-quotes"] }),
        queryClient.invalidateQueries({ queryKey: ["pos-products"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory-products"] }),
        queryClient.invalidateQueries({ queryKey: ["inventory-movements"] }),
        queryClient.invalidateQueries({ queryKey: ["transactions"] }),
        queryClient.invalidateQueries({ queryKey: ["dashboard"] }),
        queryClient.invalidateQueries({ queryKey: ["cashflow"] }),
      ]);
    },
  });

  const createQuote = useMutation({
    mutationFn: () => apiFetch<POSSavedQuote>("/pos/quotes", {
      method: "POST",
      body: JSON.stringify({
        items: cartItems,
        customer_name: quoteCustomer.trim(),
        contact_id: quoteContactId || null,
        notes: quoteNotes || null,
      }),
    }),
    onSuccess: async () => {
      setCart({});
      setQuoteId(null);
      setQuoteCustomer("");
      setQuoteContactId("");
      setQuoteNotes("");
      setQuoteOpen(false);
      await queryClient.invalidateQueries({ queryKey: ["pos-quotes"] });
    },
  });

  function setQuantity(productId: string, quantity: string) {
    setQuoteId(null);
    setCart((current) => {
      if (quantity === "") return { ...current, [productId]: { ...current[productId], quantity } };
      if (Number(quantity) <= 0) {
        const next = { ...current };
        delete next[productId];
        return next;
      }
      return { ...current, [productId]: { ...current[productId], quantity } };
    });
  }

  function addProduct(product: InventoryProduct) {
    if (Number(product.stock_quantity) <= 0) return;
    const nextQuantity = Number(cart[product.id]?.quantity || 0) + 1;
    if (nextQuantity > Number(product.stock_quantity)) {
      setScanMessage(`Estoque disponível de ${product.name}: ${quantityText(product.stock_quantity)} ${product.unit}.`);
      return;
    }
    setScanMessage("");
    setQuoteId(null);
    setCart((current) => {
      const oldEntry = current[product.id];
      return {
        ...current,
        [product.id]: {
          product,
          quantity: String(Number(oldEntry?.quantity || 0) + 1),
        },
      };
    });
    setSearch("");
    requestAnimationFrame(() => searchInput.current?.focus());
  }

  async function addProductFromSearch() {
    if (!searchTerm) return;
    try {
      const matches = await queryClient.fetchQuery({
        queryKey: ["pos-products", searchTerm],
        queryFn: () => apiFetch<InventoryProduct[]>(productSearchUrl(searchTerm)),
      });
      const lowerTerm = searchTerm.toLowerCase();
      const match = matches.find((product) =>
        product.barcode === searchTerm
        || product.sku?.toLowerCase() === lowerTerm
        || product.name.toLowerCase() === lowerTerm,
      ) ?? (matches.length === 1 ? matches[0] : undefined);
      if (match && Number(match.stock_quantity) > 0) {
        addProduct(match);
      } else if (match) {
        setScanMessage(`${match.name} está sem estoque disponível.`);
      } else {
        setScanMessage(matches.length ? "Refine a busca ou selecione o produto na lista." : "Nenhum produto encontrado com esse nome ou código.");
      }
    } catch {
      // TanStack Query exposes request errors in the search results panel.
    }
  }

  function onSearchKeyDown(event: KeyboardEvent<HTMLInputElement>) {
    if (event.key === "Enter") {
      event.preventDefault();
      void addProductFromSearch();
    }
  }

  function loadQuote(quote: POSSavedQuote) {
    if (quote.status !== "open") return;
    const nextCart: Record<string, CartEntry> = {};
    for (const item of quote.items) {
      nextCart[item.product_id] = {
        product: {
          id: item.product_id,
          name: item.product_name,
          sku: item.sku,
          barcode: item.barcode,
          sale_price: item.unit_price,
          stock_quantity: item.stock_quantity,
          unit: item.unit,
        },
        quantity: item.quantity,
      };
    }
    setCart(nextCart);
    setQuoteId(quote.id);
    setContactId(quote.contact_id ?? "");
    setNotes(quote.notes ?? "");
    setDiscountType("none");
    setDiscountValue("0.00");
    setSearch("");
    setScanMessage("");
    quotesSection.current?.removeAttribute("open");
    requestAnimationFrame(() => searchInput.current?.focus());
  }

  const cartEntries = Object.entries(cart).filter(([, entry]) => entry.quantity !== "" && Number(entry.quantity) > 0);
  const canCheckout = cartItems.length > 0 && Boolean(pricing.data) && !pricing.isFetching && !pricing.isError;
  const openQuotesCount = (savedQuotes.data ?? []).filter((quote) => quote.status === "open").length;

  return (
    <section className="space-y-5">
      <div>
        <h2 className="section-title">Ponto de venda</h2>
        <p className="section-subtitle">Pesquise por nome, SKU ou código de barras. A venda atualiza o financeiro e o estoque.</p>
      </div>

      <div className="grid items-start gap-5 xl:grid-cols-[minmax(0,1.2fr)_minmax(340px,0.8fr)]">
        <div className="panel min-w-0 space-y-4">
          <div>
            <h3 className="panel-title">Buscar produto</h3>
            <label className="relative mt-3 block">
              <Search className="pointer-events-none absolute left-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" />
              <input
                ref={searchInput}
                className="w-full py-3 pl-12 pr-12 text-base"
                aria-label="Buscar produto por nome, SKU ou código de barras"
                placeholder="Digite o nome ou código, ou escaneie o código de barras"
                value={search}
                onChange={(event) => { setSearch(event.target.value); setScanMessage(""); }}
                onKeyDown={onSearchKeyDown}
                autoComplete="off"
                autoFocus
              />
              <Barcode className="pointer-events-none absolute right-4 top-1/2 h-5 w-5 -translate-y-1/2 text-muted" />
            </label>
            <p className="mt-2 text-xs text-muted">Leitores de código de barras funcionam como teclado: escaneie e pressione Enter.</p>
          </div>

          {products.isFetching && <p className="text-sm text-muted" role="status">Buscando produtos...</p>}
          {products.isError && <div className="alert-error">{products.error.message}</div>}
          {scanMessage && <p className="text-sm text-muted" role="status">{scanMessage}</p>}
          {!searchTerm ? (
            <div className="rounded-lg border border-dashed border-line px-5 py-8 text-center text-sm text-muted">
              Os produtos aparecem aqui conforme a busca. Digite para começar.
            </div>
          ) : products.data?.length === 0 && !products.isFetching ? (
            <div className="screen-state">Nenhum produto encontrado. Confira o nome ou código de barras.</div>
          ) : (
            <div className="divide-y divide-line rounded-lg border border-line">
              {(products.data ?? []).map((product) => {
                const available = Number(product.stock_quantity);
                const inCart = cart[product.id]?.quantity;
                return (
                  <div key={product.id} className="flex flex-wrap items-center justify-between gap-3 p-4">
                    <div className="min-w-0 flex-1">
                      <div className="flex flex-wrap items-center gap-x-3 gap-y-1">
                        <h4 className="font-semibold text-ink">{product.name}</h4>
                        <span className="font-semibold text-ink">{money(product.sale_price)}</span>
                      </div>
                      <p className="mt-1 text-xs text-muted">
                        {[product.sku && `SKU ${product.sku}`, product.barcode && `Cód. barras ${product.barcode}`].filter(Boolean).join(" · ") || "Sem código cadastrado"}
                      </p>
                      <p className={`mt-1 text-xs ${available > 0 ? "text-muted" : "font-medium text-amber-800"}`}>
                        {available > 0 ? `${quantityText(product.stock_quantity)} ${product.unit} disponível` : "Sem estoque"}
                        {inCart && ` · ${quantityText(inCart)} no carrinho`}
                      </p>
                    </div>
                    <button className="btn-secondary px-3 py-2 text-sm" type="button" disabled={available <= 0} onClick={() => addProduct(product)}>
                      <Plus className="h-4 w-4" /> Adicionar
                    </button>
                  </div>
                );
              })}
            </div>
          )}
        </div>

        <div className="panel space-y-4">
          <div className="flex items-center gap-2">
            <ShoppingCart className="h-5 w-5 text-accent" />
            <h3 className="panel-title">Venda atual</h3>
          </div>
          {quoteId && (
            <div className="flex items-center justify-between gap-2 rounded-md bg-panel px-3 py-2 text-sm">
              <span className="text-ink">Convertendo orçamento salvo</span>
              <button className="btn-ghost px-2 py-1 text-xs" type="button" onClick={() => { setQuoteId(null); setCart({}); setNotes(""); setContactId(""); }}>
                Sair do orçamento
              </button>
            </div>
          )}
          {cartEntries.length === 0 ? (
            <div className="rounded-lg border border-dashed border-line px-4 py-8 text-center text-sm text-muted">Pesquise e adicione produtos para iniciar uma venda.</div>
          ) : (
            <div className="space-y-3">
              {cartEntries.map(([productId, entry]) => (
                <div key={productId} className="flex items-start gap-3 border-b border-line pb-3 last:border-0">
                  <div className="min-w-0 flex-1">
                    <p className="font-medium text-ink">{entry.product.name}</p>
                    <p className="mt-1 text-xs text-muted">{money(entry.product.sale_price)} por {entry.product.unit}</p>
                  </div>
                  <label className="sr-only" htmlFor={`pos-quantity-${productId}`}>Quantidade de {entry.product.name}</label>
                  <div className="flex items-center gap-1">
                    <button className="icon-btn h-8 w-8" type="button" aria-label={`Remover ${entry.product.name} do carrinho`} onClick={() => setQuantity(productId, "0")}>
                      <Minus className="h-3.5 w-3.5" />
                    </button>
                    <input id={`pos-quantity-${productId}`} className="w-24 text-right" type="number" min="0.001" max={entry.product.stock_quantity} step="0.001" value={entry.quantity} onChange={(event) => setQuantity(productId, event.target.value)} />
                    <button className="icon-btn h-8 w-8" type="button" aria-label={`Aumentar ${entry.product.name}`} disabled={Number(entry.quantity) >= Number(entry.product.stock_quantity)} onClick={() => setQuantity(productId, String(Number(entry.quantity || 0) + 1))}>
                      <Plus className="h-3.5 w-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          )}

          {pricing.isFetching && <p className="text-sm text-muted" role="status">Conferindo estoque e total...</p>}
          {pricing.isError && <div className="alert-error">{pricing.error.message}</div>}
          {pricing.data && (
            <div className="space-y-2 border-t border-line pt-3">
              {pricing.data.items.map((item) => (
                <div key={item.product_id} className="flex justify-between gap-3 text-xs text-muted">
                  <span>{quantityText(item.quantity)} × {item.product_name}</span>
                  <span>{money(item.line_total)}</span>
                </div>
              ))}
              <div className="flex justify-between pt-2 text-sm">
                <span className="font-semibold text-ink">Subtotal</span>
                <span className="font-semibold text-ink">{money(pricing.data.subtotal)}</span>
              </div>
              {pricing.data.discount_amount !== "0.00" && (
                <div className="flex justify-between text-sm text-muted">
                  <span>Desconto</span><span>− {money(pricing.data.discount_amount)}</span>
                </div>
              )}
              <div className="flex justify-between text-base">
                <span className="font-semibold text-ink">Total</span>
                <span className="font-bold text-ink">{money(pricing.data.total)}</span>
              </div>
            </div>
          )}

          {checkout.error && <div className="alert-error">{checkout.error.message}</div>}
          <div className="grid gap-2 sm:grid-cols-2 xl:grid-cols-1 2xl:grid-cols-2">
            <button className="btn-secondary w-full" type="button" disabled={cartItems.length === 0 || createQuote.isPending} onClick={() => setQuoteOpen(true)}>
              <FilePlus2 className="h-4 w-4" /> Criar orçamento
            </button>
            <button className="btn-primary w-full" type="button" disabled={!canCheckout || checkout.isPending} onClick={() => setCheckoutOpen(true)}>
              {checkout.isPending ? "Registrando venda..." : "Finalizar venda"}
            </button>
          </div>
          <p className="text-xs leading-5 text-muted">O pagamento e o desconto são definidos ao finalizar. A baixa do estoque ocorre somente após a confirmação.</p>
        </div>
      </div>

      <details ref={quotesSection} className="panel group">
        <summary className="flex cursor-pointer list-none items-center justify-between gap-3">
          <div>
            <h3 className="panel-title">Orçamentos</h3>
            <p className="mt-1 text-xs text-muted">{openQuotesCount} em aberto · não reservam estoque</p>
          </div>
          <ChevronDown className="h-5 w-5 text-muted transition group-open:rotate-180" />
        </summary>
        <div className="mt-4 border-t border-line pt-4">
          {savedQuotes.isLoading && <div className="screen-state">Carregando orçamentos...</div>}
          {savedQuotes.isError && <div className="alert-error">{savedQuotes.error.message}</div>}
          {savedQuotes.data?.length === 0 && <div className="screen-state">Nenhum orçamento salvo ainda.</div>}
          <div className="divide-y divide-line">
            {(savedQuotes.data ?? []).map((quote) => (
              <div key={quote.id} className="flex flex-col gap-3 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="flex flex-wrap items-center gap-2">
                    <p className="font-semibold text-ink">{quote.customer_name}</p>
                    <span className={`rounded-full px-2 py-0.5 text-xs ${quote.status === "open" ? "bg-emerald-50 text-emerald-800" : "bg-panel text-muted"}`}>
                      {quote.status === "open" ? "Em aberto" : "Convertido"}
                    </span>
                  </div>
                  <p className="mt-1 text-xs text-muted">{dateText(quote.created_at)} · {quote.items.map((item) => `${quantityText(item.quantity)} × ${item.product_name}`).join(", ")}</p>
                </div>
                <div className="flex shrink-0 items-center justify-between gap-3 sm:justify-end">
                  <span className="font-semibold text-ink">{money(quote.total)}</span>
                  {quote.status === "open" && (
                    <button className="btn-secondary px-3 py-2 text-xs" type="button" onClick={() => loadQuote(quote)}>
                      Converter para venda
                    </button>
                  )}
                </div>
              </div>
            ))}
          </div>
        </div>
      </details>

      <Dialog open={checkoutOpen} onOpenChange={setCheckoutOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Finalizar venda</DialogTitle>
            <DialogDescription>Escolha a forma de pagamento e aplique um desconto, se necessário.</DialogDescription>
          </DialogHeader>
          <div className="mt-5 space-y-4">
            <label className="field" htmlFor="pos-payment-method">
              Forma de pagamento
              <select id="pos-payment-method" value={paymentMethod} onChange={(event) => setPaymentMethod(event.target.value as PaymentMethod)}>
                {paymentMethods.map((method) => <option key={method.value} value={method.value}>{method.label}</option>)}
              </select>
            </label>
            <div className="grid gap-3 sm:grid-cols-[1fr_1fr]">
              <label className="field" htmlFor="pos-discount-type">
                Desconto
                <select id="pos-discount-type" value={discountType} onChange={(event) => setDiscountType(event.target.value as typeof discountType)}>
                  <option value="none">Sem desconto</option>
                  <option value="percentage">Porcentagem</option>
                  <option value="amount">Valor em reais</option>
                </select>
              </label>
              {discountType !== "none" && (
                <label className="field" htmlFor="pos-discount-value">
                  {discountType === "percentage" ? "Percentual (%)" : "Valor (R$)"}
                  <input id="pos-discount-value" type="number" min="0" step="0.01" inputMode="decimal" value={discountValue} onChange={(event) => setDiscountValue(event.target.value)} />
                </label>
              )}
            </div>
            <label className="field" htmlFor="pos-contact">
              Contraparte <span className="font-normal text-muted">(opcional)</span>
              <select id="pos-contact" value={contactId} onChange={(event) => setContactId(event.target.value)}>
                <option value="">Venda sem contraparte</option>
                {(contacts.data ?? []).map((contact) => <option key={contact.id} value={contact.id}>{contact.name}</option>)}
              </select>
            </label>
            <label className="field" htmlFor="pos-notes">
              Observações <span className="font-normal text-muted">(opcional)</span>
              <textarea id="pos-notes" rows={2} maxLength={1000} value={notes} onChange={(event) => setNotes(event.target.value)} />
            </label>
            {pricing.data && (
              <div className="space-y-2 rounded-lg bg-panel p-4 text-sm">
                <div className="flex justify-between"><span>Subtotal</span><span>{money(pricing.data.subtotal)}</span></div>
                <div className="flex justify-between"><span>Desconto</span><span>− {money(pricing.data.discount_amount)}</span></div>
                <div className="flex justify-between border-t border-line pt-2 font-semibold text-ink"><span>Total da venda</span><span>{money(pricing.data.total)}</span></div>
              </div>
            )}
            {pricing.isError && <div className="alert-error">{pricing.error.message}</div>}
            {checkout.error && <div className="alert-error">{checkout.error.message}</div>}
            <button className="btn-primary w-full" type="button" disabled={!canCheckout || checkout.isPending} onClick={() => checkout.mutate()}>
              {checkout.isPending ? "Registrando venda..." : "Confirmar venda"}
            </button>
          </div>
        </DialogContent>
      </Dialog>

      <Dialog open={quoteOpen} onOpenChange={setQuoteOpen}>
        <DialogContent className="max-h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>Criar orçamento</DialogTitle>
            <DialogDescription>O orçamento será salvo com os preços atuais, sem reservar produtos no estoque.</DialogDescription>
          </DialogHeader>
          <div className="mt-5 space-y-4">
            <label className="field" htmlFor="pos-quote-customer">
              Nome da pessoa ou empresa
              <input id="pos-quote-customer" required minLength={2} maxLength={160} value={quoteCustomer} onChange={(event) => setQuoteCustomer(event.target.value)} />
            </label>
            <label className="field" htmlFor="pos-quote-contact">
              Contraparte cadastrada <span className="font-normal text-muted">(opcional)</span>
              <select id="pos-quote-contact" value={quoteContactId} onChange={(event) => setQuoteContactId(event.target.value)}>
                <option value="">Não vincular contato</option>
                {(contacts.data ?? []).map((contact) => <option key={contact.id} value={contact.id}>{contact.name}</option>)}
              </select>
            </label>
            <label className="field" htmlFor="pos-quote-notes">
              Observações <span className="font-normal text-muted">(opcional)</span>
              <textarea id="pos-quote-notes" rows={2} maxLength={1000} value={quoteNotes} onChange={(event) => setQuoteNotes(event.target.value)} />
            </label>
            {createQuote.error && <div className="alert-error">{createQuote.error.message}</div>}
            <button className="btn-primary w-full" type="button" disabled={cartItems.length === 0 || quoteCustomer.trim().length < 2 || createQuote.isPending} onClick={() => createQuote.mutate()}>
              {createQuote.isPending ? "Salvando orçamento..." : "Salvar orçamento"}
            </button>
          </div>
        </DialogContent>
      </Dialog>
    </section>
  );
}
