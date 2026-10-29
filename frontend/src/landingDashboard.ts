import type { Dashboard } from "./types";

// Dados demonstrativos: a página pública nunca acessa dados de uma empresa.
export const landingDashboard: Dashboard = {
  period_start: "2026-01-01", period_end: "2026-06-30",
  current_balance: "48650.00", month_income: "32400.00", month_expense: "18250.00",
  month_result: "14150.00", month_end_balance_forecast: "51200.00", transaction_count: 42,
  trend_granularity: "month",
  trend_series: [
    { date: "2026-01-01", income: "22000", expense: "15000", result: "7000", transaction_count: 28 },
    { date: "2026-02-01", income: "25000", expense: "16000", result: "9000", transaction_count: 32 },
    { date: "2026-03-01", income: "28000", expense: "17500", result: "10500", transaction_count: 36 },
    { date: "2026-04-01", income: "26000", expense: "17000", result: "9000", transaction_count: 34 },
    { date: "2026-05-01", income: "30000", expense: "18000", result: "12000", transaction_count: 39 },
    { date: "2026-06-01", income: "32400", expense: "18250", result: "14150", transaction_count: 42 },
  ],
  category_totals: [], comparison: null, payment_methods: [], due_alerts: [],
  open_payables: { count: 3, total: "4200.00" }, open_receivables: { count: 4, total: "7500.00" },
  overdue_payables: { count: 0, total: "0.00" }, overdue_receivables: { count: 0, total: "0.00" },
};
