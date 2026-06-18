export function money(value: string | number | null | undefined) {
  const parsed = Number(value ?? 0);
  return new Intl.NumberFormat("pt-BR", {
    style: "currency",
    currency: "BRL",
  }).format(Number.isFinite(parsed) ?parsed : 0);
}

export function formatCurrencyInput(value: string | number | null | undefined) {
  const digits = String(value ?? "").replace(/\D/g, "").replace(/^0+(?=\d)/, "") || "0";
  const padded = digits.padStart(3, "0");
  const cents = padded.slice(-2);
  const integer = padded.slice(0, -2).replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  return `${integer},${cents}`;
}

export function currencyInputToDecimal(value: string) {
  const digits = value.replace(/\D/g, "").replace(/^0+(?=\d)/, "") || "0";
  const padded = digits.padStart(3, "0");
  return `${padded.slice(0, -2)}.${padded.slice(-2)}`;
}

export function dateText(value: string | null | undefined) {
  if (!value) return "-";
  const [datePart] = value.split("T");
  const [year, month, day] = datePart.split("-");
  if (!year || !month || !day) return value;
  return `${day}/${month}/${year}`;
}

export function statusText(status: string) {
  const labels: Record<string, string> = {
    pending: "Pendente",
    settled: "Liquidado",
    canceled: "Cancelado",
    uploaded: "Enviado",
    validated: "Validado",
    failed: "Com erro",
    confirmed: "Confirmado",
    active: "Ativo",
    inactive: "Inativo",
    ended: "Encerrado",
  };
  return labels[status] ?? status;
}

export function typeText(type: string) {
  const labels: Record<string, string> = {
    income: "Entrada",
    expense: "Saída",
    customer: "Cliente",
    supplier: "Fornecedor",
    both: "Ambos",
  };
  return labels[type] ?? type;
}
