import { fireEvent, render, screen, waitFor } from "@testing-library/react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { beforeEach, describe, expect, it, vi } from "vitest";
import { apiFetch } from "../api";
import { AdminFinancialPage } from "./AdminFinancialPage";

vi.mock("../api", () => ({
  apiFetch: vi.fn(),
}));

const apiFetchMock = vi.mocked(apiFetch);
const now = "2026-06-10T12:00:00Z";
const dashboard = {
  generated_at: now,
  period_start: now,
  period_end: now,
  metrics: {
    mrr: "100.00",
    arr: "1200.00",
    received_current_month: "300.00",
    received_last_30_days: "450.00",
    forecast_current_month: "500.00",
    forecast_next_30_days: "600.00",
    pending_revenue: "80.00",
    overdue_revenue: "50.00",
    lost_cancellations: "20.00",
    lost_delinquency: "10.00",
    average_ticket: "50.00",
    paying_customers: 2,
    valid_subscriptions: 2,
    received_today: "100.00",
    received_current_week: "200.00",
    received_current_month_total: "300.00",
    renewals_current_month: 2,
    renewals_next_7_days: 1,
    renewals_next_30_days: 3,
    monthly_financial_churn_rate: "2.50",
    delinquency_rate: "10.00",
  },
  monthly_series: [{
    month: "2026-06",
    received: "300.00",
    forecast: "500.00",
    mrr: "100.00",
    arr: "1200.00",
    pending: "80.00",
    churn: "20.00",
    average_ticket: "50.00",
    payments_received: 2,
  }],
  revenue_by_plan: [{ label: "Mensal", value: "300.00" }],
  revenue_by_subscription_status: [{ label: "active", value: "100.00" }],
};
const plans = [{
  id: "plan-1",
  name: "Mensal",
  slug: "monthly",
  billing_cycle: "monthly",
  duration_months: 1,
  price: "50.00",
  is_active: true,
  description: null,
  created_at: now,
  updated_at: now,
}];
const table = {
  items: [{
    company_id: "company-1",
    company_name: "Empresa Alfa",
    plan_id: "plan-1",
    plan_name: "Mensal",
    plan_value: "50.00",
    subscription_status: "active",
    payment_status: "paid",
    payment_date: now,
    next_due_date: now,
    days_overdue: 0,
    payment_method: "manual",
    received_amount: "50.00",
    pending_amount: "0.00",
    renewed_by_admin: "Admin",
    notes: "Confirmado",
    created_at: now,
    updated_at: now,
  }],
  total: 1,
  page: 1,
  page_size: 15,
  pages: 1,
};

function renderPage() {
  const queryClient = new QueryClient({
    defaultOptions: { queries: { retry: false } },
  });
  return render(
    <QueryClientProvider client={queryClient}>
      <AdminFinancialPage />
    </QueryClientProvider>,
  );
}

describe("AdminFinancialPage", () => {
  beforeEach(() => {
    apiFetchMock.mockReset();
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.startsWith("/admin/financial/dashboard")) return dashboard;
      if (path.startsWith("/admin/financial/payments")) return table;
      if (path === "/admin/plans") return plans;
      throw new Error("Rota inesperada");
    });
  });

  it("renders loading, cards, charts, table and applies filters", async () => {
    renderPage();

    expect(screen.getByText("Calculando indicadores financeiros...")).toBeInTheDocument();
    expect(await screen.findByText("MRR atual")).toBeInTheDocument();
    expect(screen.getAllByText("R$ 100,00").length).toBeGreaterThan(0);
    expect(screen.getByText("Prevista vs recebida")).toBeInTheDocument();
    expect(screen.getByText("Empresa Alfa")).toBeInTheDocument();
    expect(screen.getByText("Pago")).toBeInTheDocument();
    expect(screen.getByText("10,00%")).toBeInTheDocument();

    fireEvent.change(screen.getByLabelText("Assinatura"), {
      target: { value: "active" },
    });

    await waitFor(() => {
      expect(apiFetchMock).toHaveBeenCalledWith(
        expect.stringContaining("subscription_status=active"),
      );
    });
  });

  it("renders API errors", async () => {
    apiFetchMock.mockRejectedValue(new Error("Falha financeira"));
    renderPage();

    expect((await screen.findAllByText("Falha financeira")).length).toBeGreaterThan(0);
  });

  it("renders the empty table state", async () => {
    apiFetchMock.mockImplementation(async (path: string) => {
      if (path.startsWith("/admin/financial/dashboard")) return dashboard;
      if (path.startsWith("/admin/financial/payments")) {
        return { ...table, items: [], total: 0 };
      }
      return plans;
    });
    renderPage();

    expect(
      await screen.findByText("Nenhum registro para os filtros selecionados."),
    ).toBeInTheDocument();
  });
});
