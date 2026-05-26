import { useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  BarChart3,
  ContactRound,
  FileSpreadsheet,
  FolderTree,
  LayoutDashboard,
  LogOut,
  Menu,
  ReceiptText,
  ShieldCheck,
  X,
} from "lucide-react";
import { apiFetch, clearToken, getToken, setToken } from "./api";
import type { Subscription, User } from "./types";
import { DashboardPage } from "./pages/DashboardPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { ContactsPage } from "./pages/ContactsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { AccountViewPage } from "./pages/AccountViewPage";
import { ImportsPage } from "./pages/ImportsPage";
import { AdminSubscriptionsPage } from "./pages/AdminSubscriptionsPage";

type PageKey =
  | "dashboard"
  | "categories"
  | "contacts"
  | "transactions"
  | "payables"
  | "receivables"
  | "imports";

const pages: Array<{
  key: PageKey;
  label: string;
  icon: typeof LayoutDashboard;
}> = [
  { key: "dashboard", label: "Dashboard", icon: LayoutDashboard },
  { key: "categories", label: "Categorias", icon: FolderTree },
  { key: "contacts", label: "Contatos", icon: ContactRound },
  { key: "transactions", label: "Lançamentos", icon: ReceiptText },
  { key: "payables", label: "A pagar", icon: ArrowDownCircle },
  { key: "receivables", label: "A receber", icon: ArrowUpCircle },
  { key: "imports", label: "Importação", icon: FileSpreadsheet },
];

const financialPages = new Set<PageKey>([
  "dashboard",
  "categories",
  "transactions",
  "payables",
  "receivables",
  "imports",
]);

function pageFromHash(): PageKey {
  const hash = window.location.hash.replace("#/", "");
  return pages.some((page) => page.key === hash) ? (hash as PageKey) : "dashboard";
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [form, setForm] = useState({
    company_name: "",
    name: "",
    email: "",
    password: "",
  });

  const login = useMutation({
    mutationFn: async () =>
      apiFetch<{ access_token: string }>("/auth/login", {
        method: "POST",
        body: JSON.stringify({ email: form.email, password: form.password }),
      }),
    onSuccess: async (data) => {
      setToken(data.access_token);
      onAuthenticated(data.access_token);
      await queryClient.invalidateQueries();
    },
  });

  const register = useMutation({
    mutationFn: async () =>
      apiFetch<User>("/auth/register", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: () => login.mutate(),
  });

  const error = login.error?.message ?? register.error?.message;

  return (
    <main className="min-h-screen bg-panel px-4 py-10">
      <section className="mx-auto grid max-w-5xl gap-8 lg:grid-cols-[1fr_420px] lg:items-center">
        <div className="space-y-5">
          <p className="text-sm font-semibold uppercase tracking-wide text-brand">
            Gestão Financeira Empresarial
          </p>
          <h1 className="max-w-2xl text-4xl font-semibold text-ink">
            Controle financeiro simples para sair da planilha.
          </h1>
          <p className="max-w-xl text-base leading-7 text-muted">
            Acesse categorias, lançamentos, contas a pagar, contas a receber e importação de
            planilhas em um fluxo direto.
          </p>
        </div>

        <form
          className="space-y-4 rounded-lg border border-line bg-white p-6 shadow-sm"
          onSubmit={(event) => {
            event.preventDefault();
            if (mode === "login") login.mutate();
            else register.mutate();
          }}
        >
          <div>
            <h2 className="text-xl font-semibold text-ink">
              {mode === "login" ? "Entrar" : "Criar empresa"}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {mode === "login" ? "Use seu e-mail e senha." : "O primeiro usuário vira admin."}
            </p>
          </div>

          {mode === "register" && (
            <>
              <label className="field" htmlFor="company-name">
                Empresa
                <input
                  id="company-name"
                  required
                  value={form.company_name}
                  onChange={(event) => setForm({ ...form, company_name: event.target.value })}
                />
              </label>
              <label className="field" htmlFor="user-name">
                Nome
                <input
                  id="user-name"
                  required
                  value={form.name}
                  onChange={(event) => setForm({ ...form, name: event.target.value })}
                />
              </label>
            </>
          )}

          <label className="field" htmlFor="email">
            E-mail
            <input
              id="email"
              required
              type="email"
              value={form.email}
              onChange={(event) => setForm({ ...form, email: event.target.value })}
            />
          </label>
          <label className="field" htmlFor="password">
            Senha
            <input
              id="password"
              required
              type="password"
              value={form.password}
              onChange={(event) => setForm({ ...form, password: event.target.value })}
            />
          </label>

          {error && <div className="alert-error">{error}</div>}

          <button className="btn-primary w-full" disabled={login.isPending || register.isPending}>
            {mode === "login" ? "Entrar" : "Criar e entrar"}
          </button>
          <button
            className="btn-ghost w-full"
            type="button"
            onClick={() => setMode(mode === "login" ? "register" : "login")}
          >
            {mode === "login" ? "Criar uma empresa" : "Já tenho conta"}
          </button>
        </form>
      </section>
    </main>
  );
}

function CompanyShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [activePage, setActivePage] = useState<PageKey>(pageFromHash);
  const [menuOpen, setMenuOpen] = useState(false);
  const subscription = useQuery({
    queryKey: ["subscription-status"],
    queryFn: () => apiFetch<Subscription>("/subscription/status"),
  });

  useEffect(() => {
    const onHashChange = () => setActivePage(pageFromHash());
    window.addEventListener("hashchange", onHashChange);
    return () => window.removeEventListener("hashchange", onHashChange);
  }, []);

  const activeTitle = useMemo(
    () => pages.find((page) => page.key === activePage)?.label ?? "Dashboard",
    [activePage],
  );

  const content = {
    dashboard: <DashboardPage />,
    categories: <CategoriesPage />,
    contacts: <ContactsPage />,
    transactions: <TransactionsPage />,
    payables: <AccountViewPage kind="payables" />,
    receivables: <AccountViewPage kind="receivables" />,
    imports: <ImportsPage />,
  }[activePage];
  const isFinancialPage = financialPages.has(activePage);
  const shouldBlockFinancialPage =
    isFinancialPage && subscription.data !== undefined && !subscription.data.is_valid;
  const shellContent = shouldBlockFinancialPage ? (
    <SubscriptionBlocked subscription={subscription.data!} />
  ) : (
    content
  );

  function navigate(page: PageKey) {
    window.location.hash = `/${page}`;
    setActivePage(page);
    setMenuOpen(false);
  }

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside
        className={`fixed inset-y-0 left-0 z-30 w-72 border-r border-line bg-white p-4 transition lg:translate-x-0 ${
          menuOpen ? "translate-x-0" : "-translate-x-full"
        }`}
      >
        <div className="mb-6 flex items-center justify-between">
          <div className="flex items-center gap-2 font-semibold">
            <BarChart3 className="h-5 w-5 text-brand" />
            Financeiro
          </div>
          <button className="icon-btn lg:hidden" onClick={() => setMenuOpen(false)}>
            <X className="h-4 w-4" />
          </button>
        </div>
        <nav className="space-y-1">
          {pages.map((page) => {
            const Icon = page.icon;
            return (
              <button
                key={page.key}
                className={`nav-item ${activePage === page.key ? "nav-item-active" : ""}`}
                onClick={() => navigate(page.key)}
              >
                <Icon className="h-4 w-4" />
                {page.label}
              </button>
            );
          })}
        </nav>
      </aside>

      {menuOpen && <button className="fixed inset-0 z-20 bg-black/20 lg:hidden" onClick={() => setMenuOpen(false)} />}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <div className="flex items-center gap-3">
              <button className="icon-btn lg:hidden" onClick={() => setMenuOpen(true)}>
                <Menu className="h-4 w-4" />
              </button>
              <div>
                <h1 className="text-lg font-semibold">{activeTitle}</h1>
                <p className="text-xs text-muted">{user.name} · {user.email}</p>
              </div>
            </div>
            {subscription.data && <SubscriptionBadge subscription={subscription.data} />}
            <button
              className="btn-secondary"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">
          {subscription.isLoading && isFinancialPage ? (
            <div className="screen-state">Verificando assinatura...</div>
          ) : (
            shellContent
          )}
        </main>
      </div>
    </div>
  );
}

function AdminShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-white p-4 lg:block">
        <div className="mb-6 flex items-center gap-2 font-semibold">
          <ShieldCheck className="h-5 w-5 text-brand" />
          Plataforma
        </div>
        <nav className="space-y-1">
          <div className="nav-item nav-item-active">
            <ShieldCheck className="h-4 w-4" />
            Assinaturas
          </div>
        </nav>
      </aside>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <div>
              <h1 className="text-lg font-semibold">Administração da plataforma</h1>
              <p className="text-xs text-muted">{user.name} · {user.email}</p>
            </div>
            <button
              className="btn-secondary"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              <LogOut className="h-4 w-4" />
              Sair
            </button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-4 py-6">
          <AdminSubscriptionsPage />
        </main>
      </div>
    </div>
  );
}

function subscriptionStatusText(status: Subscription["status"]) {
  const labels: Record<Subscription["status"], string> = {
    trialing: "Trial",
    active: "Ativa",
    pending_payment: "Pagamento pendente",
    canceled: "Cancelada",
    blocked: "Bloqueada",
  };
  return labels[status];
}

function SubscriptionBadge({ subscription }: { subscription: Subscription }) {
  const tone = subscription.is_valid
    ? "border-emerald-200 bg-emerald-50 text-emerald-800"
    : "border-amber-200 bg-amber-50 text-amber-900";
  const accessDate = subscription.access_until
    ? new Date(subscription.access_until).toLocaleDateString("pt-BR")
    : null;

  return (
    <div className={`hidden rounded-md border px-3 py-2 text-xs font-medium sm:block ${tone}`}>
      {subscriptionStatusText(subscription.status)}
      {accessDate ? ` até ${accessDate}` : ""}
    </div>
  );
}

function SubscriptionBlocked({ subscription }: { subscription: Subscription }) {
  return (
    <section className="panel max-w-2xl space-y-3">
      <h2 className="panel-title">Acesso financeiro bloqueado</h2>
      <p className="text-sm leading-6 text-muted">
        A assinatura da empresa está com status {subscriptionStatusText(subscription.status).toLowerCase()}.
        O login continua disponível, mas as rotas financeiras ficam bloqueadas até a renovação manual por
        um administrador da plataforma.
      </p>
      <div className="alert-warning">
        Após a confirmação do pagamento fora da plataforma, peça a renovação manual da assinatura.
      </div>
    </section>
  );
}

export default function App() {
  const [token, setCurrentToken] = useState(getToken());
  const me = useQuery({
    queryKey: ["me", token],
    queryFn: () => apiFetch<User>("/auth/me"),
    enabled: Boolean(token),
  });

  useEffect(() => {
    if (me.isError) {
      clearToken();
      setCurrentToken(null);
    }
  }, [me.isError]);

  if (!token) return <LoginScreen onAuthenticated={setCurrentToken} />;
  if (me.isLoading) return <div className="screen-state">Carregando sessão...</div>;
  if (me.isError) {
    return <LoginScreen onAuthenticated={setCurrentToken} />;
  }
  if (me.data!.role === "platform_admin") {
    return <AdminShell user={me.data!} onLogout={() => setCurrentToken(null)} />;
  }
  return <CompanyShell user={me.data!} onLogout={() => setCurrentToken(null)} />;
}
