export type User = {
  id: string;
  company_id: string;
  name: string;
  email: string;
  role: "platform_admin" | "company_admin" | "user";
  is_active: boolean;
  email_verified_at: string | null;
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
  is_platform_company: boolean;
  created_at: string;
  updated_at: string;
};

export type AdminCompanySubscription = Subscription & {
  company_name: string;
};

export type ManualPayment = {
  id: string;
  company_id: string;
  amount: string;
  paid_at: string;
  period_start: string;
  period_end: string;
  notes: string | null;
  created_by: string;
  created_at: string;
  updated_at: string;
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
  source: string;
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
