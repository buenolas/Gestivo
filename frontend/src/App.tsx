import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  BarChart3,
  ContactRound,
  CreditCard,
  FileSpreadsheet,
  FolderTree,
  Chrome,
  LayoutDashboard,
  LogOut,
  Mail,
  MailCheck,
  Menu,
  MessageCircle,
  RefreshCw,
  ReceiptText,
  ShieldCheck,
  UsersRound,
  X,
} from "lucide-react";
import { apiFetch, clearToken, getToken, setToken } from "./api";
import type { Company, Subscription, User } from "./types";
import { DashboardPage } from "./pages/DashboardPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { ContactsPage } from "./pages/ContactsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { AccountViewPage } from "./pages/AccountViewPage";
import { ImportsPage } from "./pages/ImportsPage";
import { AdminSubscriptionsPage } from "./pages/AdminSubscriptionsPage";
import { AdminPlansPage } from "./pages/AdminPlansPage";
import { EmployeesPage } from "./pages/EmployeesPage";

type PageKey =
  | "dashboard"
  | "categories"
  | "contacts"
  | "employees"
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
  { key: "employees", label: "Funcionarios", icon: UsersRound },
  { key: "transactions", label: "Lançamentos", icon: ReceiptText },
  { key: "payables", label: "A pagar", icon: ArrowDownCircle },
  { key: "receivables", label: "A receber", icon: ArrowUpCircle },
  { key: "imports", label: "Importação", icon: FileSpreadsheet },
];

const financialPages = new Set<PageKey>([
  "dashboard",
  "categories",
  "employees",
  "transactions",
  "payables",
  "receivables",
  "imports",
]);

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: {
            client_id: string;
            callback: (response: { credential?: string }) => void;
          }) => void;
          renderButton: (
            element: HTMLElement,
            options: {
              theme?: "outline" | "filled_blue" | "filled_black";
              size?: "large" | "medium" | "small";
              width?: number;
              text?: "signin_with" | "signup_with" | "continue_with" | "signin";
              locale?: string;
            },
          ) => void;
        };
      };
    };
  }
}

function pageFromHash(): PageKey {
  const hash = window.location.hash.replace("#/", "");
  return pages.some((page) => page.key === hash) ? (hash as PageKey) : "dashboard";
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [googleReady, setGoogleReady] = useState(false);
  const [form, setForm] = useState({
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
        body: JSON.stringify({ email: form.email, password: form.password }),
      }),
    onSuccess: () => login.mutate(),
  });

  const googleLogin = useMutation({
    mutationFn: async (idToken: string) =>
      apiFetch<{ access_token: string }>("/auth/google", {
        method: "POST",
        body: JSON.stringify({ id_token: idToken }),
      }),
    onSuccess: async (data) => {
      setToken(data.access_token);
      onAuthenticated(data.access_token);
      await queryClient.invalidateQueries();
    },
  });
  const submitGoogleLogin = googleLogin.mutate;
  const handleGoogleCredential = useCallback(
    (response: { credential?: string }) => {
      if (response.credential) submitGoogleLogin(response.credential);
    },
    [submitGoogleLogin],
  );
  const renderGoogleButton = useCallback(
    (element: HTMLDivElement) => {
      if (!googleReady || !window.google) return;
      window.google.accounts.id.renderButton(element, {
        theme: "outline",
        size: "large",
        text: mode === "login" ? "signin_with" : "signup_with",
        locale: "pt-BR",
        width: element.clientWidth || 360,
      });
    },
    [googleReady, mode],
  );

  useEffect(() => {
    if (!GOOGLE_CLIENT_ID) return;

    const scriptId = "google-identity-services";
    const initializeGoogle = () => {
      if (!window.google) return;
      window.google.accounts.id.initialize({
        client_id: GOOGLE_CLIENT_ID,
        callback: handleGoogleCredential,
      });
      setGoogleReady(true);
    };

    const existingScript = document.getElementById(scriptId);
    if (existingScript) {
      if (window.google) initializeGoogle();
      else existingScript.addEventListener("load", initializeGoogle, { once: true });
      return;
    }

    const script = document.createElement("script");
    script.id = scriptId;
    script.src = "https://accounts.google.com/gsi/client";
    script.async = true;
    script.defer = true;
    script.addEventListener("load", initializeGoogle, { once: true });
    document.head.appendChild(script);
  }, [handleGoogleCredential]);

  const error = login.error?.message ?? register.error?.message ?? googleLogin.error?.message;

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
              {mode === "login" ? "Entrar" : "Criar conta"}
            </h2>
            <p className="mt-1 text-sm text-muted">
              {mode === "login" ? "Use seu e-mail e senha." : "Informe apenas e-mail e senha."}
            </p>
          </div>

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
            {mode === "login" ? "Entrar" : "Criar conta"}
          </button>
          {GOOGLE_CLIENT_ID && (
            <GoogleSignInButton
              disabled={!googleReady || googleLogin.isPending}
              onClickContainer={renderGoogleButton}
            />
          )}
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

function GoogleSignInButton({
  disabled,
  onClickContainer,
}: {
  disabled: boolean;
  onClickContainer: (element: HTMLDivElement) => void;
}) {
  const [container, setContainer] = useState<HTMLDivElement | null>(null);

  useEffect(() => {
    if (!container || disabled) return;
    container.innerHTML = "";
    onClickContainer(container);
  }, [container, disabled, onClickContainer]);

  return (
    <div className="min-h-11 w-full">
      {disabled && (
        <button className="btn-secondary w-full" disabled type="button">
          <Chrome className="h-4 w-4" />
          Google
        </button>
      )}
      <div className={disabled ? "hidden" : ""} ref={setContainer} />
    </div>
  );
}

function OnboardingScreen({
  user,
  onComplete,
  onLogout,
}: {
  user: User;
  onComplete: () => void;
  onLogout: () => void;
}) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({
    company_name: "",
    user_name: user.name,
    opening_balance: "0.00",
  });

  const completeOnboarding = useMutation({
    mutationFn: () =>
      apiFetch<Company>("/companies/me/onboarding", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["company"] });
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      onComplete();
    },
  });

  return (
    <main className="min-h-screen bg-panel px-4 py-10 text-ink">
      <div className="fixed inset-0 bg-ink/30" aria-hidden="true" />
      <section
        className="relative z-10 mx-auto max-w-lg rounded-lg border border-line bg-white p-6 shadow-lg"
        role="dialog"
        aria-modal="true"
      >
        <div>
          <h1 className="text-xl font-semibold">Configuracao inicial</h1>
          <p className="mt-1 text-sm text-muted">
            Complete estes dados para liberar o acesso financeiro da empresa.
          </p>
        </div>

        <form
          className="mt-5 space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            completeOnboarding.mutate();
          }}
        >
          <label className="field" htmlFor="onboarding-company-name">
            Nome da empresa
            <input
              id="onboarding-company-name"
              required
              value={form.company_name}
              onChange={(event) => setForm({ ...form, company_name: event.target.value })}
            />
          </label>
          <label className="field" htmlFor="onboarding-user-name">
            Nome completo do usuario
            <input
              id="onboarding-user-name"
              required
              value={form.user_name}
              onChange={(event) => setForm({ ...form, user_name: event.target.value })}
            />
          </label>
          <label className="field" htmlFor="onboarding-opening-balance">
            Saldo inicial da empresa
            <input
              id="onboarding-opening-balance"
              required
              type="number"
              step="0.01"
              value={form.opening_balance}
              onChange={(event) => setForm({ ...form, opening_balance: event.target.value })}
            />
          </label>

          {completeOnboarding.error && (
            <div className="alert-error">{completeOnboarding.error.message}</div>
          )}

          <div className="flex flex-wrap gap-3">
            <button className="btn-primary" disabled={completeOnboarding.isPending}>
              Salvar e acessar
            </button>
            <button
              className="btn-ghost"
              type="button"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              Sair
            </button>
          </div>
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
  const company = useQuery({
    queryKey: ["company"],
    queryFn: () => apiFetch<Company>("/companies/me"),
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
    employees: <EmployeesPage />,
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
        className={`fixed inset-y-0 left-0 z-30 flex w-72 flex-col border-r border-line bg-white p-4 transition lg:translate-x-0 ${
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
        <nav className="flex-1 space-y-1">
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
        <SidebarContactInfo />
      </aside>

      {menuOpen && <button className="fixed inset-0 z-20 bg-black/20 lg:hidden" onClick={() => setMenuOpen(false)} />}

      <div className="lg:pl-72">
        <header className="sticky top-0 z-10 border-b border-line bg-white/95 px-4 py-3 backdrop-blur">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <button className="icon-btn lg:hidden" onClick={() => setMenuOpen(true)}>
                <Menu className="h-4 w-4" />
              </button>
              <h1 className="truncate text-2xl font-semibold leading-tight text-ink md:text-3xl">
                {company.data?.name ?? activeTitle}
              </h1>
              <div className="hidden">
                <h1 className="text-lg font-semibold">{activeTitle}</h1>
                <p className="text-xs text-muted">{user.name} · {user.email}</p>
              </div>
            </div>
            {subscription.data && <SubscriptionBadge subscription={subscription.data} />}
            <div className="hidden shrink-0 text-right sm:block">
              <p className="text-sm font-medium text-ink">{user.name}</p>
              <p className="text-xs text-muted">{user.email}</p>
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

function SidebarContactInfo() {
  return (
    <div className="mt-4 rounded-lg border border-line bg-panel p-3 text-sm">
      <p className="font-semibold text-ink">Precisa de ajuda?</p>
      <p className="mt-1 text-xs leading-5 text-muted">
        Para liberar ou renovar o acesso, entre em contato.
      </p>
      <div className="mt-3 space-y-2">
        <a
          className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-brand transition hover:bg-white"
          href="https://wa.me/5562996960340"
          rel="noreferrer"
          target="_blank"
        >
          <MessageCircle className="h-4 w-4" />
          (62) 99696-0340
        </a>
        <a
          className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-brand transition hover:bg-white"
          href="mailto:lucasdealmeidabueno@gmail.com"
        >
          <Mail className="h-4 w-4" />
          lucasdealmeidabueno@gmail.com
        </a>
      </div>
    </div>
  );
}

function AdminShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [activePage, setActivePage] = useState<"subscriptions" | "plans">("subscriptions");

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 border-r border-line bg-white p-4 lg:block">
        <div className="mb-6 flex items-center gap-2 font-semibold">
          <ShieldCheck className="h-5 w-5 text-brand" />
          Plataforma
        </div>
        <nav className="space-y-1">
          <button
            className={`nav-item ${activePage === "subscriptions" ? "nav-item-active" : ""}`}
            onClick={() => setActivePage("subscriptions")}
          >
            <ShieldCheck className="h-4 w-4" />
            Assinaturas
          </button>
          <button
            className={`nav-item ${activePage === "plans" ? "nav-item-active" : ""}`}
            onClick={() => setActivePage("plans")}
          >
            <CreditCard className="h-4 w-4" />
            Planos
          </button>
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
          {activePage === "subscriptions" ? <AdminSubscriptionsPage /> : <AdminPlansPage />}
        </main>
      </div>
    </div>
  );
}

function EmailVerificationScreen({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [token, setTokenValue] = useState(
    () => new URLSearchParams(window.location.search).get("email_verification_token") ?? "",
  );

  const confirm = useMutation({
    mutationFn: () =>
      apiFetch<{ message: string }>("/auth/email/confirm", {
        method: "POST",
        body: JSON.stringify({ token }),
      }),
    onSuccess: async () => {
      window.history.replaceState({}, "", window.location.pathname + window.location.hash);
      await queryClient.invalidateQueries({ queryKey: ["me"] });
    },
  });

  const resend = useMutation({
    mutationFn: () =>
      apiFetch<{ message: string }>("/auth/email/verification/resend", {
        method: "POST",
      }),
  });

  useEffect(() => {
    if (token) confirm.mutate();
  }, []);

  return (
    <main className="min-h-screen bg-panel px-4 py-10 text-ink">
      <section className="mx-auto max-w-xl space-y-5 rounded-lg border border-line bg-white p-6 shadow-sm">
        <div className="flex items-center gap-3">
          <MailCheck className="h-6 w-6 text-brand" />
          <div>
            <h1 className="text-xl font-semibold">Confirme seu e-mail</h1>
            <p className="text-sm text-muted">{user.email}</p>
          </div>
        </div>

        <p className="text-sm leading-6 text-muted">
          O login esta liberado, mas o acesso financeiro fica bloqueado ate a confirmacao do e-mail.
          Em modo dev, o link aparece nos logs do backend.
        </p>

        <label className="field" htmlFor="verification-token">
          Token de verificacao
          <input
            id="verification-token"
            value={token}
            onChange={(event) => setTokenValue(event.target.value)}
          />
        </label>

        {confirm.error && <div className="alert-error">{confirm.error.message}</div>}
        {resend.error && <div className="alert-error">{resend.error.message}</div>}
        {resend.data && <div className="alert-warning">{resend.data.message}</div>}

        <div className="flex flex-wrap gap-3">
          <button className="btn-primary" disabled={!token || confirm.isPending} onClick={() => confirm.mutate()}>
            <MailCheck className="h-4 w-4" />
            Confirmar
          </button>
          <button className="btn-secondary" disabled={resend.isPending} onClick={() => resend.mutate()}>
            <RefreshCw className="h-4 w-4" />
            Reenviar
          </button>
          <button
            className="btn-ghost"
            onClick={() => {
              clearToken();
              queryClient.clear();
              onLogout();
            }}
          >
            Sair
          </button>
        </div>
      </section>
    </main>
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
      <h2 className="panel-title">Seu período gratuito terminou.</h2>
      <p className="text-sm leading-6 text-muted">
        Para continuar usando o sistema, realize o pagamento da assinatura.
      </p>
      <p className="text-sm leading-6 text-muted">Entre em contato para liberação.</p>
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
  const company = useQuery({
    queryKey: ["company"],
    queryFn: () => apiFetch<Company>("/companies/me"),
    enabled:
      Boolean(token) &&
      Boolean(me.data?.email_verified_at) &&
      me.data?.role !== "platform_admin",
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
  if (!me.data!.email_verified_at) {
    return <EmailVerificationScreen user={me.data!} onLogout={() => setCurrentToken(null)} />;
  }
  if (company.isLoading) return <div className="screen-state">Carregando empresa...</div>;
  if (company.isError) return <div className="alert-error">{company.error.message}</div>;
  if (!company.data!.onboarding_completed_at) {
    return (
      <OnboardingScreen
        user={me.data!}
        onComplete={() => company.refetch()}
        onLogout={() => setCurrentToken(null)}
      />
    );
  }
  return <CompanyShell user={me.data!} onLogout={() => setCurrentToken(null)} />;
}
