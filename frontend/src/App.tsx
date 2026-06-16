import { useCallback, useEffect, useMemo, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  ArrowDownCircle,
  ArrowUpCircle,
  Building2,
  Chrome,
  CircleDollarSign,
  CreditCard,
  FileSpreadsheet,
  FolderTree,
  KeyRound,
  LayoutDashboard,
  LogOut,
  Mail,
  MailCheck,
  Menu,
  MessageCircle,
  ReceiptText,
  RefreshCw,
  ShieldCheck,
  Sparkles,
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
import { AdminClientsPage } from "./pages/AdminClientsPage";
import { AdminPlansPage } from "./pages/AdminPlansPage";
import { AdminFinancialPage } from "./pages/AdminFinancialPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { CompanyUsersPage } from "./pages/CompanyUsersPage";
import { brandAssets } from "./assets/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { TooltipProvider } from "@/components/ui/tooltip";

type PageKey =
  | "dashboard"
  | "categories"
  | "contacts"
  | "employees"
  | "users"
  | "transactions"
  | "payables"
  | "receivables"
  | "imports";

const pages: Array<{
  key: PageKey;
  label: string;
  description: string;
  icon: typeof LayoutDashboard;
}> = [
  { key: "dashboard", label: "Visão geral", description: "Indicadores do mês", icon: LayoutDashboard },
  { key: "transactions", label: "Lançamentos", description: "Entradas e saídas", icon: ReceiptText },
  { key: "payables", label: "A pagar", description: "Compromissos", icon: ArrowDownCircle },
  { key: "receivables", label: "A receber", description: "Recebimentos", icon: ArrowUpCircle },
  { key: "categories", label: "Categorias", description: "Plano financeiro", icon: FolderTree },
  { key: "imports", label: "Importação", description: "CSV e XLSX", icon: FileSpreadsheet },
  { key: "employees", label: "Funcionários", description: "Despesas salariais", icon: UsersRound },
  { key: "users", label: "Usuários", description: "Acesso da empresa", icon: UsersRound },
  { key: "contacts", label: "Contatos", description: "Contrapartes", icon: Building2 },
];

const financialPages = new Set<PageKey>([
  "dashboard",
  "categories",
  "employees",
  "users",
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
  return pages.some((page) => page.key === hash) ?(hash as PageKey) : "dashboard";
}

function BrandLogo({ compact = false, variant = "primary" }: { compact?: boolean; variant?: "primary" | "dark" }) {
  if (compact) {
    return (
      <img
        className="h-10 w-10 object-contain"
        src={variant === "dark" ?brandAssets.symbolLight : brandAssets.symbolDefault}
        alt="Gestivo"
      />
    );
  }

  return (
    <img
      className="h-11 w-auto object-contain"
      src={variant === "dark" ?brandAssets.logoDark : brandAssets.logoPrimary}
      alt="Gestivo"
    />
  );
}

function LoginScreen({ onAuthenticated }: { onAuthenticated: (token: string) => void }) {
  const queryClient = useQueryClient();
  const [mode, setMode] = useState<"login" | "register">("login");
  const [googleReady, setGoogleReady] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });

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
        text: mode === "login" ?"signin_with" : "signup_with",
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
    <main className="min-h-screen bg-panel px-4 py-6 text-ink md:py-10">
      <section className="mx-auto grid min-h-[calc(100vh-3rem)] max-w-6xl overflow-hidden rounded-lg border border-line bg-white shadow-[0_30px_90px_rgba(15,23,42,0.10)] lg:min-h-[calc(100vh-5rem)] lg:grid-cols-[1.2fr_460px]">
        <div className="relative flex min-h-[420px] flex-col justify-between overflow-hidden bg-ink p-6 text-white sm:p-8 md:p-12 lg:min-h-[560px]">
          <div className="relative z-10">
            <BrandLogo variant="dark" />
            <Badge className="mt-10 bg-white/10 text-white" variant="outline">
              SaaS financeiro B2B
            </Badge>
            <h1 className="mt-6 max-w-2xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
              Gestão financeira ativa para negócios em crescimento.
            </h1>
            <p className="mt-6 max-w-xl text-lg leading-8 text-slate-300">
              Organize caixa, receitas, despesas e indicadores em uma experiência visual, segura e pronta para sair das planilhas.
            </p>
            <div className="mt-10 grid max-w-xl gap-3 sm:grid-cols-3">
              {[
                ["30 dias", "Trial gratuito"],
                ["CSV/XLSX", "Importação"],
                ["Multiempresa", "Dados isolados"],
              ].map(([value, label]) => (
                <div key={label} className="rounded-md border border-white/10 bg-white/5 p-4">
                  <strong className="block text-xl text-highlight">{value}</strong>
                  <span className="mt-1 block text-xs font-medium text-slate-300">{label}</span>
                </div>
              ))}
            </div>
          </div>
          <div className="relative z-10 mt-10 h-2 w-44 rounded-full bg-highlight" />
        </div>

        <form
          className="flex flex-col justify-center space-y-5 p-6 md:p-10"
          onSubmit={(event) => {
            event.preventDefault();
            if (mode === "login") login.mutate();
            else register.mutate();
          }}
        >
          <div>
            <p className="text-sm font-semibold text-accent">{mode === "login" ?"Acessar plataforma" : "Começar agora"}</p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-ink">
              {mode === "login" ?"Entre na sua conta" : "Crie sua empresa"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-muted">
              {mode === "login" ?"Use seu e-mail e senha para continuar." : "Informe e-mail e senha para iniciar o trial."}
            </p>
          </div>

          <label className="field" htmlFor="email">
            E-mail
            <input id="email" required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          <label className="field" htmlFor="password">
            Senha
            <input id="password" required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
          </label>

          {error && <div className="alert-error">{error}</div>}

          <Button className="w-full" disabled={login.isPending || register.isPending} size="lg" variant="premium">
            <Sparkles className="h-4 w-4" />
            {mode === "login" ?"Entrar" : "Criar conta"}
          </Button>
          {GOOGLE_CLIENT_ID && (
            <GoogleSignInButton disabled={!googleReady || googleLogin.isPending} onClickContainer={renderGoogleButton} />
          )}
          <Button className="w-full" type="button" variant="ghost" onClick={() => setMode(mode === "login" ?"register" : "login")}>
            {mode === "login" ?"Criar uma empresa" : "Já tenho conta"}
          </Button>
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
        <Button className="w-full" disabled type="button" variant="secondary">
          <Chrome className="h-4 w-4" />
          Google
        </Button>
      )}
      <div className={disabled ?"hidden" : ""} ref={setContainer} />
    </div>
  );
}

function OnboardingScreen({ user, onComplete, onLogout }: { user: User; onComplete: () => void; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ company_name: "", user_name: user.name, opening_balance: "0.00" });

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
      <section className="mx-auto max-w-xl space-y-6 rounded-lg border border-line bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.10)]">
        <BrandLogo />
        <div>
          <h1 className="text-2xl font-bold">Configuração inicial</h1>
          <p className="mt-1 text-sm leading-6 text-muted">Complete estes dados para liberar o acesso financeiro da empresa.</p>
        </div>

        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            completeOnboarding.mutate();
          }}
        >
          <label className="field" htmlFor="onboarding-company-name">
            Nome da empresa
            <input id="onboarding-company-name" required value={form.company_name} onChange={(event) => setForm({ ...form, company_name: event.target.value })} />
          </label>
          <label className="field" htmlFor="onboarding-user-name">
            Nome completo do usuário
            <input id="onboarding-user-name" required value={form.user_name} onChange={(event) => setForm({ ...form, user_name: event.target.value })} />
          </label>
          <label className="field" htmlFor="onboarding-opening-balance">
            Saldo inicial da empresa
            <input id="onboarding-opening-balance" required type="number" step="0.01" value={form.opening_balance} onChange={(event) => setForm({ ...form, opening_balance: event.target.value })} />
          </label>

          {completeOnboarding.error && <div className="alert-error">{completeOnboarding.error.message}</div>}

          <div className="flex flex-wrap gap-3">
            <Button disabled={completeOnboarding.isPending} variant="premium">Salvar e acessar</Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              Sair
            </Button>
          </div>
        </form>
      </section>
    </main>
  );
}

function PasswordChangeScreen({ user, onComplete, onLogout }: { user: User; onComplete: () => void; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [form, setForm] = useState({ current_password: "", new_password: "" });
  const changePassword = useMutation({
    mutationFn: () =>
      apiFetch<User>("/auth/change-password", {
        method: "POST",
        body: JSON.stringify(form),
      }),
    onSuccess: async () => {
      await queryClient.invalidateQueries({ queryKey: ["me"] });
      onComplete();
    },
  });

  return (
    <main className="min-h-screen bg-panel px-4 py-10 text-ink">
      <section className="mx-auto max-w-lg space-y-5 rounded-lg border border-line bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.10)]">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-mint p-3 text-accent">
            <KeyRound className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Defina sua senha</h1>
            <p className="text-sm text-muted">{user.email}</p>
          </div>
        </div>
        <p className="text-sm leading-6 text-muted">Troque a senha temporária antes de acessar os dados da empresa.</p>
        <form
          className="space-y-4"
          onSubmit={(event) => {
            event.preventDefault();
            changePassword.mutate();
          }}
        >
          <label className="field" htmlFor="current-password">
            Senha temporária
            <input id="current-password" required type="password" value={form.current_password} onChange={(event) => setForm({ ...form, current_password: event.target.value })} />
          </label>
          <label className="field" htmlFor="new-password">
            Nova senha
            <input id="new-password" required minLength={8} type="password" value={form.new_password} onChange={(event) => setForm({ ...form, new_password: event.target.value })} />
          </label>
          {changePassword.error && <div className="alert-error">{changePassword.error.message}</div>}
          <div className="flex gap-3">
            <Button disabled={changePassword.isPending} variant="premium">Salvar nova senha</Button>
            <Button
              type="button"
              variant="ghost"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              Sair
            </Button>
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
  const isAdmin = user.role === "company_admin";
  const visiblePages = useMemo(
    () => (isAdmin ?pages : pages.filter((page) => ["transactions", "categories", "contacts"].includes(page.key))),
    [isAdmin],
  );
  const subscription = useQuery({ queryKey: ["subscription-status"], queryFn: () => apiFetch<Subscription>("/subscription/status") });
  const company = useQuery({ queryKey: ["company"], queryFn: () => apiFetch<Company>("/companies/me") });

  useEffect(() => {
    const syncPage = () => {
      const nextPage = pageFromHash();
      if (!visiblePages.some((page) => page.key === nextPage)) {
        window.location.hash = "/transactions";
        setActivePage("transactions");
        return;
      }
      setActivePage(nextPage);
    };
    syncPage();
    window.addEventListener("hashchange", syncPage);
    return () => window.removeEventListener("hashchange", syncPage);
  }, [visiblePages]);

  const activeMeta = useMemo(() => pages.find((page) => page.key === activePage) ?? pages[0], [activePage]);
  const content = {
    dashboard: <DashboardPage />,
    categories: <CategoriesPage canManage={isAdmin} />,
    contacts: <ContactsPage canManage={isAdmin} />,
    employees: <EmployeesPage />,
    users: <CompanyUsersPage />,
    transactions: <TransactionsPage canManageAll={isAdmin} />,
    payables: <AccountViewPage kind="payables" />,
    receivables: <AccountViewPage kind="receivables" />,
    imports: <ImportsPage />,
  }[activePage];
  const isFinancialPage = financialPages.has(activePage);
  const shouldBlockFinancialPage = isFinancialPage && subscription.data !== undefined && !subscription.data.is_valid;
  const shellContent = shouldBlockFinancialPage ?<SubscriptionBlocked subscription={subscription.data!} /> : content;

  function navigate(page: PageKey) {
    window.location.hash = `/${page}`;
    setActivePage(page);
    setMenuOpen(false);
  }

  const sidebar = <SidebarNavigation pages={visiblePages} activePage={activePage} navigate={navigate} />;

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col bg-ink p-4 text-white lg:flex">
        {sidebar}
      </aside>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent>{sidebar}</SheetContent>
      </Sheet>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-white/90 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <Button className="shrink-0 lg:hidden" size="icon" variant="secondary" onClick={() => setMenuOpen(true)} aria-label="Abrir navegação">
                <Menu className="h-4 w-4" />
              </Button>
              <div className="lg:hidden">
                <BrandLogo compact />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">{activeMeta.description}</p>
                <h1 className="truncate text-2xl font-bold leading-tight text-ink md:text-3xl">
                  {company.data?.name ?? activeMeta.label}
                </h1>
              </div>
            </div>
            {subscription.data && <SubscriptionBadge subscription={subscription.data} />}
            <div className="hidden shrink-0 text-right sm:block">
              <p className="text-sm font-semibold text-ink">{user.name}</p>
              <p className="text-xs text-muted">{user.email}</p>
            </div>
            <Button
              className="shrink-0"
              variant="secondary"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-3 py-5 sm:px-4 md:px-6">
          {subscription.isLoading && isFinancialPage ?<div className="screen-state">Verificando assinatura...</div> : shellContent}
        </main>
      </div>
    </div>
  );
}

function SidebarNavigation({
  pages: navPages,
  activePage,
  navigate,
}: {
  pages: typeof pages;
  activePage: PageKey;
  navigate: (page: PageKey) => void;
}) {
  return (
    <>
      <div className="mb-8 flex items-center justify-between">
        <BrandLogo variant="dark" />
      </div>
      <nav className="flex-1 space-y-1">
        {navPages.map((page) => {
          const Icon = page.icon;
          return (
            <button key={page.key} className={`nav-item ${activePage === page.key ?"nav-item-active" : ""}`} onClick={() => navigate(page.key)}>
              <Icon className="h-4 w-4" />
              <span>
                <span className="block">{page.label}</span>
                <span className="block text-xs font-medium opacity-70">{page.description}</span>
              </span>
            </button>
          );
        })}
      </nav>
      <SidebarContactInfo />
    </>
  );
}

function SidebarContactInfo() {
  return (
    <div className="mt-4 rounded-lg border border-white/10 bg-white/5 p-3 text-sm">
      <p className="font-semibold text-white">Precisa de ajuda?</p>
      <p className="mt-1 text-xs leading-5 text-slate-300">Para liberar ou renovar o acesso, entre em contato.</p>
      <div className="mt-3 space-y-2">
        <a className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-highlight transition hover:bg-white/10" href="https://wa.me/5562996960340" rel="noreferrer" target="_blank">
          <MessageCircle className="h-4 w-4" />
          (62) 99696-0340
        </a>
        <a className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-highlight transition hover:bg-white/10" href="mailto:lucasdealmeidabueno@gmail.com">
          <Mail className="h-4 w-4" />
          lucasdealmeidabueno@gmail.com
        </a>
      </div>
    </div>
  );
}

function AdminShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [activePage, setActivePage] = useState<"financial" | "clients" | "plans">("financial");
  const [menuOpen, setMenuOpen] = useState(false);

  const adminPages = [
    { key: "financial" as const, label: "Financeiro", description: "Receita e assinaturas", icon: CircleDollarSign },
    { key: "clients" as const, label: "Clientes", description: "Base e risco", icon: ShieldCheck },
    { key: "plans" as const, label: "Planos", description: "Valores e status", icon: CreditCard },
  ];
  const activeAdminPage = adminPages.find((page) => page.key === activePage) ?? adminPages[0];

  function navigate(page: "financial" | "clients" | "plans") {
    setActivePage(page);
    setMenuOpen(false);
  }

  const sidebar = <AdminSidebarNavigation pages={adminPages} activePage={activePage} navigate={navigate} />;

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col bg-ink p-4 text-white lg:flex">
        {sidebar}
      </aside>

      <Sheet open={menuOpen} onOpenChange={setMenuOpen}>
        <SheetContent>{sidebar}</SheetContent>
      </Sheet>

      <div className="lg:pl-72">
        <header className="sticky top-0 z-20 border-b border-line bg-white/90 px-4 py-3 backdrop-blur md:px-6">
          <div className="flex items-center justify-between gap-3">
            <div className="flex min-w-0 flex-1 items-center gap-3">
              <Button className="lg:hidden" size="icon" variant="secondary" onClick={() => setMenuOpen(true)} aria-label="Abrir navegação admin">
                <Menu className="h-4 w-4" />
              </Button>
              <div className="lg:hidden">
                <BrandLogo compact />
              </div>
              <div className="min-w-0">
                <p className="text-xs font-semibold uppercase tracking-wide text-accent">Gestivo Platform</p>
                <h1 className="truncate text-xl font-bold md:text-2xl">Administração da plataforma</h1>
                <p className="truncate text-xs text-muted">{activeAdminPage.description}</p>
              </div>
            </div>
            <div className="hidden shrink-0 text-right sm:block">
              <p className="text-sm font-semibold text-ink">{user.name}</p>
              <p className="text-xs text-muted">{user.email}</p>
            </div>
            <Button
              className="shrink-0"
              variant="secondary"
              onClick={() => {
                clearToken();
                queryClient.clear();
                onLogout();
              }}
            >
              <LogOut className="h-4 w-4" />
              <span className="hidden sm:inline">Sair</span>
            </Button>
          </div>
        </header>
        <main className="mx-auto max-w-7xl px-3 py-5 sm:px-4 md:px-6">
          {activePage === "financial" && <AdminFinancialPage />}
          {activePage === "clients" && <AdminClientsPage />}
          {activePage === "plans" && <AdminPlansPage />}
        </main>
      </div>
    </div>
  );
}

function AdminSidebarNavigation({
  pages: navPages,
  activePage,
  navigate,
}: {
  pages: Array<{
    key: "financial" | "clients" | "plans";
    label: string;
    description: string;
    icon: typeof CircleDollarSign;
  }>;
  activePage: "financial" | "clients" | "plans";
  navigate: (page: "financial" | "clients" | "plans") => void;
}) {
  return (
    <>
      <div className="mb-8">
        <BrandLogo variant="dark" />
        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Administração</p>
      </div>
      <nav className="flex-1 space-y-1">
        {navPages.map((page) => {
          const Icon = page.icon;
          return (
            <button key={page.key} className={`nav-item ${activePage === page.key ?"nav-item-active" : ""}`} onClick={() => navigate(page.key)}>
              <Icon className="h-4 w-4" />
              <span>
                <span className="block">{page.label}</span>
                <span className="block text-xs font-medium opacity-70">{page.description}</span>
              </span>
            </button>
          );
        })}
      </nav>
    </>
  );
}

function EmailVerificationScreen({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [token, setTokenValue] = useState(() => new URLSearchParams(window.location.search).get("email_verification_token") ?? "");

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
    mutationFn: () => apiFetch<{ message: string }>("/auth/email/verification/resend", { method: "POST" }),
  });

  useEffect(() => {
    if (token) confirm.mutate();
  }, []);

  return (
    <main className="min-h-screen bg-panel px-4 py-10 text-ink">
      <section className="mx-auto max-w-xl space-y-5 rounded-lg border border-line bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.10)]">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-mint p-3 text-accent">
            <MailCheck className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">Confirme seu e-mail</h1>
            <p className="text-sm text-muted">{user.email}</p>
          </div>
        </div>
        <p className="text-sm leading-6 text-muted">
          O login está liberado, mas o acesso financeiro fica bloqueado até a confirmação do e-mail. Em modo dev, o link aparece nos logs do backend.
        </p>
        <label className="field" htmlFor="verification-token">
          Token de verificação
          <input id="verification-token" value={token} onChange={(event) => setTokenValue(event.target.value)} />
        </label>
        {confirm.error && <div className="alert-error">{confirm.error.message}</div>}
        {resend.error && <div className="alert-error">{resend.error.message}</div>}
        {resend.data && <div className="alert-warning">{resend.data.message}</div>}
        <div className="flex flex-wrap gap-3">
          <Button disabled={!token || confirm.isPending} onClick={() => confirm.mutate()} variant="premium">
            <MailCheck className="h-4 w-4" />
            Confirmar
          </Button>
          <Button disabled={resend.isPending} onClick={() => resend.mutate()} variant="secondary">
            <RefreshCw className="h-4 w-4" />
            Reenviar
          </Button>
          <Button
            variant="ghost"
            onClick={() => {
              clearToken();
              queryClient.clear();
              onLogout();
            }}
          >
            Sair
          </Button>
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
  const variant = subscription.is_valid ?"success" : "warning";
  const accessDate = subscription.access_until ?new Date(subscription.access_until).toLocaleDateString("pt-BR") : null;

  return (
    <Badge className="hidden sm:inline-flex" variant={variant}>
      {subscriptionStatusText(subscription.status)}
      {accessDate ?` até ${accessDate}` : ""}
    </Badge>
  );
}

function SubscriptionBlocked({ subscription }: { subscription: Subscription }) {
  return (
    <section className="panel max-w-2xl space-y-3">
      <Badge variant="warning">{subscriptionStatusText(subscription.status)}</Badge>
      <h2 className="panel-title">Seu período gratuito terminou.</h2>
      <p className="text-sm leading-6 text-muted">Para continuar usando o sistema, realize o pagamento da assinatura.</p>
      <p className="text-sm leading-6 text-muted">Entre em contato para liberação.</p>
    </section>
  );
}

export default function App() {
  const [token, setCurrentToken] = useState(getToken());
  const me = useQuery({ queryKey: ["me", token], queryFn: () => apiFetch<User>("/auth/me"), enabled: Boolean(token) });
  const company = useQuery({
    queryKey: ["company"],
    queryFn: () => apiFetch<Company>("/companies/me"),
    enabled: Boolean(token) && Boolean(me.data?.email_verified_at) && me.data?.role === "company_admin" && !me.data?.must_change_password,
  });

  useEffect(() => {
    if (me.isError) {
      clearToken();
      setCurrentToken(null);
    }
  }, [me.isError]);

  return (
    <TooltipProvider>
      {!token ?(
        <LoginScreen onAuthenticated={setCurrentToken} />
      ) : me.isLoading ?(
        <div className="screen-state">Carregando sessão...</div>
      ) : me.isError ?(
        <LoginScreen onAuthenticated={setCurrentToken} />
      ) : me.data!.role === "platform_admin" ?(
        <AdminShell user={me.data!} onLogout={() => setCurrentToken(null)} />
      ) : !me.data!.email_verified_at ?(
        <EmailVerificationScreen user={me.data!} onLogout={() => setCurrentToken(null)} />
      ) : me.data!.must_change_password ?(
        <PasswordChangeScreen user={me.data!} onComplete={() => me.refetch()} onLogout={() => setCurrentToken(null)} />
      ) : me.data!.role === "company_admin" && company.isLoading ?(
        <div className="screen-state">Carregando empresa...</div>
      ) : me.data!.role === "company_admin" && company.isError ?(
        <div className="alert-error">{company.error.message}</div>
      ) : me.data!.role === "company_admin" && !company.data!.onboarding_completed_at ?(
        <OnboardingScreen user={me.data!} onComplete={() => company.refetch()} onLogout={() => setCurrentToken(null)} />
      ) : (
        <CompanyShell user={me.data!} onLogout={() => setCurrentToken(null)} />
      )}
    </TooltipProvider>
  );
}
