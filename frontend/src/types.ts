export type User = {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: "platform_admin" | "company_admin" | "user";
  is_active: boolean;
  must_change_password: boolean;
  email_verified_at: string | null;
};

export type CompanyUser = {
  id: string;
  name: string;
  email: string;
  role: "company_admin" | "user";
  is_active: boolean;
  must_change_password: boolean;
  created_at: string;
  updated_at: string;
};

export type SubscriptionStatus =
  | "trialing"
  | "active"
  | "pending_payment"
  | "canceled"
  | "blocked";

export type Subscription = {
  company_id: string;
  status: SubscriptionStatus;
  is_valid: boolean;
  trial_ends_at: string;
  subscription_valid_until: string | null;
  access_until: string | null;
};

export type Company = {
  id: string;
  name: string;
  subscription_status: SubscriptionStatus;
  trial_ends_at: string;
  subscription_valid_until: string | null;
  opening_balance: string;
  opening_balance_date: string | null;
  onboarding_completed_at: string | null;
  is_platform_company: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminCompanySubscription = Subscription & {
  company_name: string;
  current_plan_id: string | null;
  current_plan_name: string | null;
};

export type AdminMetricCard = {
  key: string;
  label: string;
  value: number | string;
};

export type AdminChartPoint = {
  label: string;
  value: number | string;
};

export type AdminClientDashboard = {
  cards: AdminMetricCard[];
  subscription_status: AdminChartPoint[];
  new_clients_by_month: AdminChartPoint[];
  trial_conversions_by_month: AdminChartPoint[];
  cancellations_by_month: AdminChartPoint[];
  active_base_by_month: AdminChartPoint[];
  active_vs_risk: AdminChartPoint[];
  plan_distribution: AdminChartPoint[];
  most_active_by_transactions: AdminChartPoint[];
  highest_financial_volume: AdminChartPoint[];
};

export type AdminClientListItem = {
  company_id: string;
  company_name: string;
  admin_name: string | null;
  admin_email: string | null;
  subscription_status: SubscriptionStatus;
  plan_id: string | null;
  plan_name: string | null;
  plan_price: string | null;
  created_at: string;
  trial_started_at: string | null;
  trial_ends_at: string;
  subscription_started_at: string | null;
  subscription_valid_until: string | null;
  days_remaining: number | null;
  last_login_at: string | null;
  users_count: number;
  financial_transactions_count: number;
  imports_count: number;
  usage_status: "ativo" | "pouco uso" | "sem uso recente" | "nunca usou";
  is_at_risk: boolean;
};

export type AdminClientList = {
  items: AdminClientListItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type AdminClientDetail = AdminClientListItem & {
  blocked_at: string | null;
  canceled_at: string | null;
  users: Array<Record<string, string | boolean | null>>;
  renewal_history: Array<Record<string, string | null>>;
  payment_history: Array<Record<string, string | null>>;
  usage_events: Array<Record<string, string | null>>;
  last_import_at: string | null;
};

export type ManualPayment = {
  id: string;
  company_id: string;
  plan_id: string | null;
  plan_slug: string | null;
  billing_cycle: BillingCycle | null;
  duration_months: number | null;
  price_at_payment: string | null;
  amount: string;
  status: "paid" | "pending" | "canceled" | "refunded";
  payment_method: string;
  paid_at: string | null;
  due_date: string | null;
  period_start: string;
  period_end: string;
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
};

export type BillingCycle = "monthly" | "semiannual" | "annual";

export type Plan = {
  id: string;
  name: string;
  slug: "monthly" | "semiannual" | "annual";
  billing_cycle: BillingCycle;
  duration_months: number;
  price: string;
  is_active: boolean;
  description: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminFinancialMetrics = {
  mrr: string;
  arr: string;
  received_current_month: string;
  received_last_30_days: string;
  forecast_current_month: string;
  forecast_next_30_days: string;
  pending_revenue: string;
  overdue_revenue: string;
  lost_cancellations: string;
  lost_delinquency: string;
  average_ticket: string;
  paying_customers: number;
  valid_subscriptions: number;
  received_today: string;
  received_current_week: string;
  received_current_month_total: string;
  renewals_current_month: number;
  renewals_next_7_days: number;
  renewals_next_30_days: number;
  monthly_financial_churn_rate: string;
  delinquency_rate: string;
};

export type AdminFinancialSeriesPoint = {
  month: string;
  received: string;
  forecast: string;
  mrr: string;
  arr: string;
  pending: string;
  churn: string;
  average_ticket: string;
  payments_received: number;
};

export type AdminFinancialDashboard = {
  generated_at: string;
  period_start: string;
  period_end: string;
  metrics: AdminFinancialMetrics;
  monthly_series: AdminFinancialSeriesPoint[];
  revenue_by_plan: AdminChartPoint[];
  revenue_by_subscription_status: AdminChartPoint[];
};

export type AdminFinancialTableItem = {
  company_id: string;
  company_name: string;
  plan_id: string | null;
  plan_name: string | null;
  plan_value: string;
  subscription_status: SubscriptionStatus;
  payment_status: string;
  payment_date: string | null;
  next_due_date: string | null;
  days_overdue: number;
  payment_method: string | null;
  received_amount: string;
  pending_amount: string;
  renewed_by_admin: string | null;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type AdminFinancialTable = {
  items: AdminFinancialTableItem[];
  total: number;
  page: number;
  page_size: number;
  pages: number;
};

export type Category = {
  id: string;
  name: string;
  type: "income" | "expense";
  is_active: boolean;
};

export type Contact = {
  id: string;
  name: string;
  type: "customer" | "supplier" | "both";
  is_active: boolean;
};

export type TransactionStatus = "pending" | "settled" | "canceled";
export type TransactionType = "income" | "expense";

export type Transaction = {
  id: string;
  category_id: string | null;
  contact_id: string | null;
  employee_id: string | null;
  import_batch_id: string | null;
  description: string;
  amount: string;
  type: TransactionType;
  status: TransactionStatus;
  competence_date: string;
  reference_month: string | null;
  due_date: string | null;
  settled_at: string | null;
  notes: string | null;
  product_name: string | null;
  product_unit_price: string | null;
  product_quantity: string | null;
  product_unit: string | null;
  source: string;
  created_by: string;
  updated_by: string;
};

export type EmployeeStatus = "active" | "inactive" | "ended";

export type Employee = {
  id: string;
  company_id: string;
  name: string;
  position: string | null;
  salary_amount: string;
  contract_start_date: string;
  contract_end_date: string | null;
  status: EmployeeStatus;
  notes: string | null;
  created_at: string;
  updated_at: string;
};

export type SalaryExpenseGeneration = {
  reference_month: string;
  created_count: number;
  skipped_count: number;
  transactions: Transaction[];
};

export type Dashboard = {
  period_start: string;
  period_end: string;
  current_balance: string;
  month_income: string;
  month_expense: string;
  month_result: string;
  open_payables: { count: number; total: string };
  open_receivables: { count: number; total: string };
  overdue_payables: { count: number; total: string };
  overdue_receivables: { count: number; total: string };
  due_alerts: Array<{
    transaction_id: string;
    kind: TransactionType;
    severity: "yellow" | "orange" | "red";
    title: string;
    description: string;
    amount: string;
    due_date: string;
    days_until_due: number;
    contact_name: string | null;
    category_name: string | null;
  }>;
  month_end_balance_forecast: string;
};

export type CashFlow = {
  generated_at: string;
  summary: {
    income_total: string;
    expense_total: string;
    result: string;
  };
  items: Transaction[];
};

export type ImportBatch = {
  id: string;
  filename: string;
  file_type: "csv" | "xlsx";
  status: "uploaded" | "validated" | "failed" | "confirmed";
  headers: string[];
  preview_rows: Array<Record<string, string | null>>;
  mapping: Record<string, string | null> | null;
  validation_errors: Array<{
    row_number: number;
    field: string;
    message: string;
    value: string | null;
  }>;
  duplicate_warnings: Array<{
    row_number: number;
    scope: string;
    message: string;
  }>;
  summary: null | {
    total_rows: number;
    valid_rows: number;
    error_rows: number;
    duplicate_warnings: number;
    income_count: number;
    expense_count: number;
    income_total: string;
    expense_total: string;
    import_mode: string;
  };
};
