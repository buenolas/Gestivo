import { type FormEvent, useCallback, useEffect, useMemo, useState } from "react";
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
  PackagePlus,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  UsersRound,
  X,
} from "lucide-react";
import { apiFetch, clearToken, getToken, setToken } from "./api";
import type { Company, Subscription, User } from "./types";
import { DashboardPage } from "./pages/DashboardPage";
import { landingDashboard } from "./landingDashboard";
import { PublicInfoPage } from "./pages/PublicInfoPage";
import { CashFlowPage } from "./pages/CashFlowPage";
import { ProductOutputsPage } from "./pages/ProductOutputsPage";
import { CategoriesPage } from "./pages/CategoriesPage";
import { ContactsPage } from "./pages/ContactsPage";
import { TransactionsPage } from "./pages/TransactionsPage";
import { AccountViewPage } from "./pages/AccountViewPage";
import { ImportsPage } from "./pages/ImportsPage";
import { AdminClientsPage } from "./pages/AdminClientsPage";
import { AdminPlansPage } from "./pages/AdminPlansPage";
import { AdminFinancialPage } from "./pages/AdminFinancialPage";
import { AdminStripeRiskEventsPage } from "./pages/AdminStripeRiskEventsPage";
import { EmployeesPage } from "./pages/EmployeesPage";
import { CompanyUsersPage } from "./pages/CompanyUsersPage";
import { FinancialAssistantPage } from "./pages/FinancialAssistantPage";
import { SubscriptionPage } from "./pages/SubscriptionPage";
import { SubscriptionCheckout } from "./components/SubscriptionCheckout";
import { brandAssets } from "./assets/brand";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { Sheet, SheetContent } from "@/components/ui/sheet";
import { TooltipProvider } from "@/components/ui/tooltip";

type PageKey =
  | "dashboard"
  | "assistant"
  | "cashflow"
  | "productOutputs"
  | "categories"
  | "contacts"
  | "employees"
  | "users"
  | "transactions"
  | "payables"
  | "receivables"
  | "imports"
  | "plans";

type AdminPageKey = "financial" | "clients" | "plans" | "stripe-risk";

const pages: Array<{
  key: PageKey;
  label: string;
  description: string;
  icon: typeof LayoutDashboard;
}> = [
  { key: "dashboard", label: "Visão geral", description: "Indicadores do mês", icon: LayoutDashboard },
  { key: "assistant", label: "Assistente financeiro", description: "Pergunte sobre seu negócio", icon: Sparkles },
  { key: "cashflow", label: "Fluxo de caixa", description: "Caixa realizado", icon: CircleDollarSign },
  { key: "productOutputs", label: "Saída de produtos", description: "Valores a receber", icon: PackagePlus },
  { key: "transactions", label: "Lançamentos", description: "Entradas e saídas", icon: ReceiptText },
  { key: "payables", label: "A pagar", description: "Compromissos", icon: ArrowDownCircle },
  { key: "receivables", label: "A receber", description: "Recebimentos", icon: ArrowUpCircle },
  { key: "categories", label: "Categorias", description: "Plano financeiro", icon: FolderTree },
  { key: "imports", label: "Importação", description: "CSV e XLSX", icon: FileSpreadsheet },
  { key: "employees", label: "Funcionários", description: "Despesas salariais", icon: UsersRound },
  { key: "users", label: "Usuários", description: "Acesso da empresa", icon: UsersRound },
  { key: "contacts", label: "Contatos", description: "Contrapartes", icon: Building2 },
  { key: "plans", label: "Plano e assinatura", description: "Upgrade e cobrança", icon: CreditCard },
];

const sidebarSections: Array<{
  label: string;
  pageKeys: PageKey[];
}> = [
  { label: "Principal", pageKeys: ["dashboard", "assistant", "cashflow"] },
  { label: "Financeiro", pageKeys: ["transactions", "payables", "receivables", "categories"] },
  { label: "Operação", pageKeys: ["productOutputs", "imports"] },
  { label: "Administração", pageKeys: ["employees", "users", "contacts"] },
  { label: "Conta", pageKeys: ["plans"] },
];

const financialPages = new Set<PageKey>([
  "dashboard",
  "assistant",
  "cashflow",
  "productOutputs",
  "categories",
  "employees",
  "users",
  "transactions",
  "payables",
  "receivables",
  "imports",
  "contacts",
]);

const pageFeatureCodes: Record<PageKey, string> = {
  dashboard: "dashboard",
  assistant: "assistant",
  cashflow: "cashflow",
  productOutputs: "product_outputs",
  categories: "categories",
  contacts: "contacts",
  employees: "employees",
  users: "users",
  transactions: "transactions",
  payables: "payables",
  receivables: "receivables",
  imports: "imports",
  plans: "",
};

const GOOGLE_CLIENT_ID = import.meta.env.VITE_GOOGLE_CLIENT_ID;

declare global {
  interface Window {
    fbq?: (...args: unknown[]) => void;
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

function trackMetaEvent(eventName: string) {
  if (typeof window.fbq === "function") {
    window.fbq("track", eventName);
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
  const [mode, setMode] = useState<"login" | "register" | "forgot-password">("login");
  const [resetStep, setResetStep] = useState<"request" | "confirm">("request");
  const [resetMessage, setResetMessage] = useState("");
  const [googleReady, setGoogleReady] = useState(false);
  const [form, setForm] = useState({ email: "", password: "" });
  const [passwordResetForm, setPasswordResetForm] = useState({ code: "", new_password: "" });

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
    onSuccess: () => {
      // The API creates the company's 30-day trial during registration.
      trackMetaEvent("StartTrial");
      login.mutate();
    },
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

  const requestPasswordReset = useMutation({
    mutationFn: async () =>
      apiFetch<{ message: string }>("/auth/password/forgot", {
        method: "POST",
        body: JSON.stringify({ email: form.email }),
      }),
    onSuccess: (data) => {
      setResetMessage(data.message);
      setResetStep("confirm");
    },
  });

  const confirmPasswordReset = useMutation({
    mutationFn: async () =>
      apiFetch<{ message: string }>("/auth/password/reset", {
        method: "POST",
        body: JSON.stringify({
          email: form.email,
          code: passwordResetForm.code,
          new_password: passwordResetForm.new_password,
        }),
      }),
    onSuccess: (data) => {
      setMode("login");
      setResetStep("request");
      setResetMessage(data.message);
      setPasswordResetForm({ code: "", new_password: "" });
      setForm((currentForm) => ({ ...currentForm, password: "" }));
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
        width: Math.max(120, Math.min(element.clientWidth || 360, 400)),
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

  const error =
    login.error?.message ??
    register.error?.message ??
    googleLogin.error?.message ??
    requestPasswordReset.error?.message ??
    confirmPasswordReset.error?.message;
  const isSubmitting = login.isPending || register.isPending || requestPasswordReset.isPending || confirmPasswordReset.isPending;
  const isAuthMode = mode === "login" || mode === "register";

  function switchMode(nextMode: "login" | "register" | "forgot-password") {
    setMode(nextMode);
    setResetStep("request");
    setResetMessage("");
    setPasswordResetForm({ code: "", new_password: "" });
  }

  return (
    <main className="min-h-screen bg-[#f7f9f7] text-ink">
      <header className="mx-auto flex max-w-7xl flex-wrap items-center justify-between gap-x-2 gap-y-4 px-6 py-5 sm:gap-x-4 sm:py-6 lg:px-10">
        <BrandLogo />
        <nav aria-label="Navegação principal" className="order-last flex w-full items-center justify-between gap-3 text-xs font-medium text-slate-600 sm:justify-start sm:gap-6 sm:text-sm md:order-none md:w-auto md:gap-8">
          <a className="hover:text-ink" href="#recursos">O que você encontra</a>
          <a className="hover:text-ink" href="#assistente">Assistente financeiro</a>
        </nav>
        <div className="flex items-center gap-2 sm:gap-3">
          <a className="whitespace-nowrap text-xs font-semibold text-ink hover:text-emerald-700 sm:text-sm" href="#acesso" onClick={() => switchMode("login")}>Entrar</a>
          <a className="whitespace-nowrap rounded-full bg-ink px-2 py-2.5 text-xs font-semibold text-white hover:bg-slate-700 sm:px-5 sm:py-3 sm:text-sm" href="#acesso" onClick={() => switchMode("register")}>Criar conta <span className="hidden sm:inline" aria-hidden="true">↗</span></a>
        </div>
      </header>

      <section className="mx-auto grid max-w-7xl items-center gap-14 px-6 pb-20 pt-12 lg:grid-cols-[0.9fr_1.1fr] lg:px-10 lg:pb-28 lg:pt-20">
        <div>
          <h1 className="mt-7 max-w-2xl text-5xl font-bold leading-[1.04] tracking-[-0.04em] text-ink sm:text-6xl xl:text-7xl">Seu financeiro, com clareza para ir <span className="text-emerald-600">mais longe.</span></h1>
          <p className="mt-7 max-w-xl text-lg leading-8 text-slate-600">Saiba de onde vem e para onde vai o dinheiro da sua empresa. Organize o dia a dia, acompanhe o caixa e tome decisões com mais segurança.</p>
          <div className="mt-9 flex flex-wrap items-center gap-5">
            <a className="rounded-full bg-ink px-7 py-4 text-sm font-bold text-white shadow-lg shadow-slate-900/10 hover:bg-slate-700" href="#acesso" onClick={() => switchMode("register")}>Começar gratuitamente <span aria-hidden="true">↗</span></a>
            <a className="text-sm font-semibold text-ink underline decoration-emerald-400 underline-offset-4" href="#recursos">Conhecer o Gestivo</a>
          </div>
          <p className="mt-5 text-sm text-slate-500">30 dias de teste gratuito · Comece com sua planilha</p>
        </div>
        <div className="rounded-[2rem] bg-[#dceee4] p-4 sm:p-7">
          <div className="overflow-hidden rounded-2xl border border-white/80 bg-panel shadow-[0_25px_70px_rgba(20,55,40,0.17)]">
            <div className="flex items-center justify-between border-b border-slate-200 bg-white px-5 py-3"><span className="text-sm font-bold">Gestivo <span className="ml-2 font-normal text-slate-400">/ Visão geral</span></span><span className="text-xs text-emerald-700">Demonstração</span></div>
            <div className="h-[430px] overflow-hidden" inert aria-hidden="true"><div className="w-[200%] origin-top-left scale-50 p-8"><DashboardPage previewData={landingDashboard} /></div></div>
          </div>
          <p className="mt-4 text-right text-xs text-emerald-900/60">Interface do Gestivo · dados de demonstração</p>
        </div>
      </section>

      <section id="recursos" className="bg-white px-6 py-20 lg:px-10 lg:py-28"><div className="mx-auto max-w-7xl"><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-600">Tudo em perspectiva</p><div className="mt-4 grid gap-6 md:grid-cols-2"><h2 className="max-w-xl text-4xl font-bold tracking-tight sm:text-5xl">Mais controle para o presente. Mais confiança para o futuro.</h2><p className="max-w-lg self-start text-lg leading-8 text-slate-500">O Gestivo reúne as informações financeiras da sua empresa em um lugar simples de acompanhar.</p></div><div className="mt-14 grid gap-5 md:grid-cols-3">{[[LayoutDashboard, "Uma visão clara do caixa", "Acompanhe entradas, saídas, saldo e resultados em um painel visual."], [ReceiptText, "Contas sob controle", "Organize lançamentos, compromissos a pagar e valores a receber."], [FileSpreadsheet, "Sua planilha tem lugar aqui", "Importe dados em CSV ou XLSX e comece com as informações que você já tem."]].map(([Icon, title, description]) => { const FeatureIcon = Icon as typeof LayoutDashboard; return <article key={title as string} className="rounded-2xl border border-slate-100 bg-[#f8faf9] p-7"><FeatureIcon className="h-6 w-6 text-emerald-600" /><h3 className="mt-8 text-xl font-bold">{title as string}</h3><p className="mt-3 text-sm leading-7 text-slate-500">{description as string}</p></article>; })}</div></div></section>

      <section id="assistente" className="bg-ink px-6 py-20 text-white lg:px-10 lg:py-28"><div className="mx-auto grid max-w-7xl items-center gap-12 md:grid-cols-2"><div><p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">Inteligência para suas decisões</p><h2 className="mt-5 max-w-xl text-4xl font-bold tracking-tight sm:text-5xl">Converse com os números do seu negócio.</h2><p className="mt-6 max-w-lg text-lg leading-8 text-slate-300">O assistente financeiro com IA ajuda você a entender suas movimentações, receitas e despesas com perguntas em linguagem simples.</p><p className="mt-5 text-sm text-slate-400">Disponibilidade e limites conforme o plano contratado.</p></div><div className="rounded-2xl border border-white/10 bg-white/5 p-6 sm:p-8"><div className="flex items-center gap-3 text-sm font-semibold"><Sparkles className="h-5 w-5 text-emerald-300" /> Assistente financeiro</div><div className="ml-auto mt-8 max-w-sm rounded-2xl rounded-br-sm bg-white/10 p-4 text-sm leading-6">Onde minha empresa mais gastou neste mês?</div><div className="mr-auto mt-4 max-w-sm rounded-2xl rounded-bl-sm bg-emerald-100 p-4 text-sm leading-6 text-emerald-950">Neste mês, suas maiores despesas foram com fornecedores (R$ 8.400), seguidas de salários (R$ 5.200) e aluguel (R$ 2.000). Fornecedores representam cerca de 46% das saídas. Vale acompanhar essa categoria para identificar oportunidades de economia.</div><p className="mt-5 text-xs text-slate-400">Exemplo ilustrativo</p></div></div></section>

      <section id="acesso" className="grid w-full overflow-hidden bg-ink text-white lg:grid-cols-[1.2fr_1fr]">
        <div className="relative flex min-w-0 min-h-[420px] flex-col justify-between overflow-hidden bg-ink p-6 text-white sm:p-8 md:p-12 lg:min-h-[560px]">
          <div className="relative z-10">
            <BrandLogo variant="dark" />
            <Badge className="mt-10 bg-white/10 text-white" variant="outline">
              SaaS financeiro B2B
            </Badge>
            <h1 className="mt-6 max-w-2xl text-4xl font-bold leading-[1.05] tracking-tight sm:text-5xl md:text-6xl">
              Comece a enxergar seu financeiro com mais clareza.
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
          className="mx-auto flex min-w-0 w-full max-w-[480px] flex-col justify-center space-y-5 p-6 text-white md:p-10 lg:py-16"
          onSubmit={(event) => {
            event.preventDefault();
            if (mode === "login") login.mutate();
            else if (mode === "register") register.mutate();
            else if (resetStep === "request") requestPasswordReset.mutate();
            else confirmPasswordReset.mutate();
          }}
        >
          <div>
            <p className="text-sm font-semibold text-lime-300">
              {mode === "login" ?"Acessar plataforma" : mode === "register" ?"Começar agora" : "Recuperar acesso"}
            </p>
            <h2 className="mt-2 text-3xl font-bold tracking-tight text-white">
              {mode === "login" ?"Entre na sua conta" : mode === "register" ?"Crie sua empresa" : "Redefina sua senha"}
            </h2>
            <p className="mt-2 text-sm leading-6 text-slate-300">
              {mode === "login"
                ?"Use seu e-mail e senha para continuar."
                : mode === "register"
                  ?"Informe e-mail e senha para iniciar o trial."
                  : resetStep === "request"
                    ?"Informe seu e-mail para receber um código de verificação."
                    :"Digite o código recebido e escolha uma nova senha."}
            </p>
          </div>

          <label className="field !text-white" htmlFor="email">
            E-mail
            <input id="email" required type="email" value={form.email} onChange={(event) => setForm({ ...form, email: event.target.value })} />
          </label>
          {isAuthMode && (
            <label className="field !text-white" htmlFor="password">
              Senha
              <input id="password" required type="password" value={form.password} onChange={(event) => setForm({ ...form, password: event.target.value })} />
            </label>
          )}
          {mode === "forgot-password" && resetStep === "confirm" && (
            <>
              <label className="field !text-white" htmlFor="password-reset-code">
                Código de verificação
                <input
                  id="password-reset-code"
                  inputMode="numeric"
                  maxLength={6}
                  minLength={6}
                  pattern="\d{6}"
                  required
                  value={passwordResetForm.code}
                  onChange={(event) => setPasswordResetForm({ ...passwordResetForm, code: event.target.value.replace(/\D/g, "").slice(0, 6) })}
                />
              </label>
              <label className="field !text-white" htmlFor="new-password">
                Nova senha
                <input
                  id="new-password"
                  minLength={8}
                  required
                  type="password"
                  value={passwordResetForm.new_password}
                  onChange={(event) => setPasswordResetForm({ ...passwordResetForm, new_password: event.target.value })}
                />
              </label>
            </>
          )}

          {error && <div className="alert-error">{error}</div>}
          {resetMessage && <div className="alert-warning">{resetMessage}</div>}

          <Button className="w-full" disabled={isSubmitting} size="lg" variant="premium">
            {mode === "forgot-password" ?<KeyRound className="h-4 w-4" /> : <Sparkles className="h-4 w-4" />}
            {mode === "login"
              ?"Entrar"
              : mode === "register"
                ?"Criar conta"
                : resetStep === "request"
                  ?"Enviar código"
                  :"Redefinir senha"}
          </Button>
          {mode === "login" && (
            <Button className="w-full !text-slate-100 hover:!bg-white/10" type="button" variant="ghost" onClick={() => switchMode("forgot-password")}>
              Esqueci minha senha
            </Button>
          )}
          {isAuthMode && GOOGLE_CLIENT_ID && (
            <GoogleSignInButton disabled={!googleReady || googleLogin.isPending} onClickContainer={renderGoogleButton} />
          )}
          <Button className="w-full !text-slate-100 hover:!bg-white/10" type="button" variant="ghost" onClick={() => switchMode(mode === "login" ?"register" : "login")}>
            {mode === "login" ?"Criar uma empresa" : "Já tenho conta"}
          </Button>
        </form>
      </section>
      <footer className="border-t border-slate-200 bg-[#f7f9f7] px-6 py-14 lg:px-10"><div className="mx-auto grid max-w-7xl gap-10 sm:grid-cols-2 lg:grid-cols-[2fr_1fr_1.5fr]"><div><BrandLogo /><p className="mt-4 max-w-sm text-sm leading-6 text-slate-500">Gestão financeira para empresas que querem acompanhar seus números e crescer com clareza.</p></div><div className="space-y-3 text-sm"><h2 className="font-bold text-ink">Conheça o Gestivo</h2><a className="block text-slate-600 hover:text-emerald-700" href="/?pagina=sobre">Quem somos</a><a className="block text-slate-600 hover:text-emerald-700" href="/?pagina=contato">Contato</a><a className="block text-slate-600 hover:text-emerald-700" href="#recursos">Funcionalidades</a></div><div className="space-y-3 text-sm"><h2 className="font-bold text-ink">Fale com a gente</h2><a className="block break-all text-slate-600 hover:text-emerald-700" href="mailto:gestivo@bubassoftware.com.br">gestivo@bubassoftware.com.br</a><a className="block text-slate-600 hover:text-emerald-700" href="tel:+556231901862">(62) 3190-1862</a></div></div><div className="mx-auto mt-12 max-w-7xl border-t border-slate-200 pt-6 text-xs text-slate-500">Gestivo · Gestão financeira para seu negócio</div></footer>
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
    const render = () => {
      container.innerHTML = "";
      onClickContainer(container);
    };

    render();
    let renderedWidth = container.clientWidth;
    const observer = new ResizeObserver(() => {
      const nextWidth = container.clientWidth;
      if (nextWidth === renderedWidth) return;
      renderedWidth = nextWidth;
      render();
    });
    observer.observe(container);

    return () => observer.disconnect();
  }, [container, disabled, onClickContainer]);

  return (
    <div className="min-h-11 min-w-0 w-full overflow-hidden">
      {disabled && (
        <Button className="w-full" disabled type="button" variant="secondary">
          <Chrome className="h-4 w-4" />
          Google
        </Button>
      )}
      <div className={`${disabled ? "hidden" : ""} min-w-0 w-full overflow-hidden`} ref={setContainer} />
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
  const [checkoutReturn] = useState<"success" | "cancelled" | null>(() => {
    const result = new URLSearchParams(window.location.search).get("checkout");
    return result === "success" || result === "cancelled" ? result : null;
  });
  const [checkoutPollExpired, setCheckoutPollExpired] = useState(false);
  const subscription = useQuery({
    queryKey: ["subscription-status"],
    queryFn: () => apiFetch<Subscription>("/subscription/status"),
    refetchInterval: (query) =>
      checkoutReturn === "success" && !query.state.data?.is_valid && !checkoutPollExpired ? 3000 : false,
  });
  const company = useQuery({ queryKey: ["company"], queryFn: () => apiFetch<Company>("/companies/me") });
  const billingPortal = useMutation({
    mutationFn: () =>
      apiFetch<{ url: string }>("/subscription/billing-portal", {
        method: "POST",
      }),
    onSuccess: ({ url }) => window.location.assign(url),
  });

  useEffect(() => {
    if (!checkoutReturn) return;
    const url = new URL(window.location.href);
    url.searchParams.delete("checkout");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
  }, [checkoutReturn]);

  useEffect(() => {
    if (checkoutReturn !== "success" || subscription.data?.is_valid) return;
    const timeout = window.setTimeout(() => setCheckoutPollExpired(true), 120_000);
    return () => window.clearTimeout(timeout);
  }, [checkoutReturn, subscription.data?.is_valid]);
  const visiblePages = useMemo(
    () => {
      const rolePages = isAdmin
        ? pages
        : pages.filter((page) =>
            ["assistant", "cashflow", "productOutputs", "transactions", "categories", "contacts"].includes(page.key),
          );
      const features = subscription.data?.feature_codes;
      return features
        ? rolePages.filter((page) => page.key === "plans" || features.includes(pageFeatureCodes[page.key]))
        : rolePages;
    },
    [isAdmin, subscription.data?.feature_codes],
  );

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
    assistant: <FinancialAssistantPage />,
    cashflow: <CashFlowPage user={user} />,
    productOutputs: <ProductOutputsPage user={user} />,
    categories: <CategoriesPage canManage={isAdmin} />,
    contacts: <ContactsPage canManage={isAdmin} />,
    employees: <EmployeesPage />,
    users: <CompanyUsersPage />,
    transactions: <TransactionsPage canManageAll={isAdmin} />,
    payables: <AccountViewPage kind="payables" />,
    receivables: <AccountViewPage kind="receivables" />,
    imports: <ImportsPage />,
    plans: subscription.data
      ? <SubscriptionPage subscription={subscription.data} canManage={isAdmin} />
      : <div className="screen-state">Verificando assinatura...</div>,
  }[activePage];
  const isFinancialPage = financialPages.has(activePage);
  const shouldBlockFinancialPage = isFinancialPage && subscription.data !== undefined && !subscription.data.is_valid;
  const shellContent = shouldBlockFinancialPage
    ? <SubscriptionBlocked subscription={subscription.data!} canManage={isAdmin} />
    : content;

  function navigate(page: PageKey) {
    window.location.hash = `/${page}`;
    setActivePage(page);
    setMenuOpen(false);
  }

  const sidebar = <SidebarNavigation pages={visiblePages} activePage={activePage} navigate={navigate} />;

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col overflow-hidden bg-ink p-4 text-white lg:flex">
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
            {isAdmin && subscription.data?.can_manage_billing && (
              <Button
                className="shrink-0"
                size="sm"
                variant="secondary"
                disabled={billingPortal.isPending}
                onClick={() => billingPortal.mutate()}
              >
                {billingPortal.isPending ? "Abrindo..." : "Faturas e pagamento"}
              </Button>
            )}
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
          {checkoutReturn && (
            <div className="mb-4 rounded-lg border border-line bg-white p-4 text-sm leading-6 text-ink" role="status">
              {checkoutReturn === "cancelled"
                ? "Checkout cancelado. Nenhuma cobrança foi confirmada."
                : subscription.data?.is_valid
                  ? "A assinatura foi confirmada pelo Gestivo e o acesso está liberado."
                  : checkoutPollExpired
                    ? "Ainda aguardamos a confirmação do Stripe. Atualize esta página em instantes."
                    : "Recebemos seu retorno do Checkout. Aguardando a confirmação segura do Stripe..."}
            </div>
          )}
          {billingPortal.error && <div className="alert-error mb-4">{billingPortal.error.message}</div>}
          {subscription.isError && activePage === "plans"
            ? <div className="alert-error">{subscription.error.message}</div>
            : subscription.isLoading && (isFinancialPage || activePage === "plans")
              ? <div className="screen-state">Verificando assinatura...</div>
              : shellContent}
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
  const visibleSections = sidebarSections
    .map((section) => ({
      ...section,
      pages: section.pageKeys
        .map((pageKey) => navPages.find((page) => page.key === pageKey))
        .filter((page): page is (typeof pages)[number] => Boolean(page)),
    }))
    .filter((section) => section.pages.length > 0);

  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 pb-6">
        <BrandLogo variant="dark" />
      </div>
      <nav className="sidebar-scroll min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        {visibleSections.map((section) => (
          <section key={section.label} className="space-y-1.5">
            <p className="px-3 text-[0.68rem] font-bold uppercase tracking-wider text-slate-500">{section.label}</p>
            <div className="space-y-1">
              {section.pages.map((page) => {
                const Icon = page.icon;
                return (
                  <button key={page.key} className={`nav-item ${activePage === page.key ?"nav-item-active" : ""}`} onClick={() => navigate(page.key)}>
                    <Icon className="h-4 w-4 shrink-0" />
                    <span className="min-w-0">
                      <span className="block truncate">{page.label}</span>
                      <span className="block truncate text-xs font-medium opacity-70">{page.description}</span>
                    </span>
                  </button>
                );
              })}
            </div>
          </section>
        ))}
      </nav>
      <div className="shrink-0 pt-4">
        <SidebarContactInfo />
      </div>
    </div>
  );
}

function SidebarContactInfo() {
  return (
    <div className="rounded-lg border border-white/10 bg-white/5 p-3 text-sm">
      <p className="font-semibold text-white">Precisa de ajuda?</p>
      <p className="mt-1 text-xs leading-5 text-slate-300">Para liberar ou renovar o acesso, entre em contato.</p>
      <div className="mt-3 space-y-2">
        <a className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-highlight transition hover:bg-white/10" href="https://wa.me/5562996960340" rel="noreferrer" target="_blank">
          <MessageCircle className="h-4 w-4" />
          (62) 99696-0340
        </a>
        <a className="flex items-center gap-2 rounded-md px-2 py-1.5 font-medium text-highlight transition hover:bg-white/10" href="mailto:gestivo@bubassoftware.com.br">
          <Mail className="h-4 w-4 shrink-0" />
          gestivo@bubassoftware.com.br
        </a>
      </div>
    </div>
  );
}

function AdminShell({ user, onLogout }: { user: User; onLogout: () => void }) {
  const queryClient = useQueryClient();
  const [activePage, setActivePage] = useState<AdminPageKey>(() =>
    window.location.pathname === "/admin/stripe/risk-events" ? "stripe-risk" : "financial",
  );
  const [menuOpen, setMenuOpen] = useState(false);

  const adminPages = [
    { key: "financial" as const, label: "Financeiro", description: "Receita e assinaturas", icon: CircleDollarSign },
    { key: "clients" as const, label: "Clientes", description: "Base e risco", icon: ShieldCheck },
    { key: "plans" as const, label: "Planos", description: "Valores e status", icon: CreditCard },
    { key: "stripe-risk" as const, label: "Alertas Stripe", description: "Revisão de pagamentos", icon: ShieldAlert },
  ];
  const activeAdminPage = adminPages.find((page) => page.key === activePage) ?? adminPages[0];

  function navigate(page: AdminPageKey) {
    setActivePage(page);
    setMenuOpen(false);
    const targetPath = page === "stripe-risk" ? "/admin/stripe/risk-events" : "/";
    if (window.location.pathname !== targetPath) {
      window.history.replaceState({}, "", `${targetPath}${window.location.search}`);
    }
  }

  const sidebar = <AdminSidebarNavigation pages={adminPages} activePage={activePage} navigate={navigate} />;

  return (
    <div className="min-h-screen bg-panel text-ink">
      <aside className="fixed inset-y-0 left-0 z-30 hidden w-72 flex-col overflow-hidden bg-ink p-4 text-white lg:flex">
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
          {activePage === "stripe-risk" && <AdminStripeRiskEventsPage />}
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
    key: AdminPageKey;
    label: string;
    description: string;
    icon: typeof CircleDollarSign;
  }>;
  activePage: AdminPageKey;
  navigate: (page: AdminPageKey) => void;
}) {
  return (
    <div className="flex h-full min-h-0 flex-col">
      <div className="shrink-0 pb-6">
        <BrandLogo variant="dark" />
        <p className="mt-3 text-xs font-semibold uppercase tracking-wide text-slate-400">Administração</p>
      </div>
      <nav className="sidebar-scroll min-h-0 flex-1 space-y-5 overflow-y-auto pr-1">
        <section className="space-y-1.5">
          <p className="px-3 text-[0.68rem] font-bold uppercase tracking-wider text-slate-500">Plataforma</p>
          <div className="space-y-1">
            {navPages.map((page) => {
              const Icon = page.icon;
              return (
                <button key={page.key} className={`nav-item ${activePage === page.key ?"nav-item-active" : ""}`} onClick={() => navigate(page.key)}>
                  <Icon className="h-4 w-4 shrink-0" />
                  <span className="min-w-0">
                    <span className="block truncate">{page.label}</span>
                    <span className="block truncate text-xs font-medium opacity-70">{page.description}</span>
                  </span>
                </button>
              );
            })}
          </div>
        </section>
      </nav>
    </div>
  );
}

function CompanyUserInvitationScreen({
  invitationToken,
  onContinueToLogin,
}: {
  invitationToken: string;
  onContinueToLogin: () => void;
}) {
  const [password, setPassword] = useState("");
  const [passwordConfirmation, setPasswordConfirmation] = useState("");
  const [passwordError, setPasswordError] = useState("");
  const [accepted, setAccepted] = useState(false);

  const acceptInvitation = useMutation({
    mutationFn: () =>
      apiFetch<{ message: string }>("/company-users/accept-invitation", {
        method: "POST",
        body: JSON.stringify({ token: invitationToken, new_password: password }),
      }),
    onSuccess: () => {
      const url = new URL(window.location.href);
      url.searchParams.delete("company_invite_token");
      window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
      setAccepted(true);
    },
  });

  function submit(event: FormEvent) {
    event.preventDefault();
    setPasswordError("");
    if (password !== passwordConfirmation) {
      setPasswordError("As senhas não conferem.");
      return;
    }
    acceptInvitation.mutate();
  }

  return (
    <main className="min-h-screen bg-panel px-4 py-10 text-ink">
      <section className="mx-auto max-w-xl space-y-5 rounded-lg border border-line bg-white p-6 shadow-[0_30px_90px_rgba(15,23,42,0.10)]">
        <div className="flex items-center gap-3">
          <div className="rounded-md bg-mint p-3 text-accent">
            <MailCheck className="h-5 w-5" />
          </div>
          <div>
            <h1 className="text-xl font-bold">{accepted ? "Convite aceito" : "Confirme seu e-mail"}</h1>
            <p className="text-sm text-muted">Acesso à empresa no Gestivo</p>
          </div>
        </div>

        {accepted ? (
          <>
            <p className="text-sm leading-6 text-muted">Seu e-mail foi confirmado e o acesso está ativo. Entre usando seu e-mail e a senha que acabou de criar.</p>
            <Button onClick={onContinueToLogin} variant="premium">Ir para o login</Button>
          </>
        ) : (
          <form className="space-y-4" onSubmit={submit}>
            <p className="text-sm leading-6 text-muted">Confirme que você recebeu este convite criando sua senha. O acesso só será liberado depois desta etapa.</p>
            <label className="field" htmlFor="invitation-password">
              Criar senha
              <input id="invitation-password" required minLength={8} maxLength={72} type="password" autoComplete="new-password" value={password} onChange={(event) => setPassword(event.target.value)} />
            </label>
            <label className="field" htmlFor="invitation-password-confirmation">
              Confirmar senha
              <input id="invitation-password-confirmation" required minLength={8} maxLength={72} type="password" autoComplete="new-password" value={passwordConfirmation} onChange={(event) => setPasswordConfirmation(event.target.value)} />
            </label>
            {passwordError && <div className="alert-error" role="alert">{passwordError}</div>}
            {acceptInvitation.error && (
              <div className="alert-error" role="alert">
                {acceptInvitation.error.message} Se o link expirou, peça um novo convite ao administrador da empresa.
              </div>
            )}
            <Button className="w-full" disabled={acceptInvitation.isPending} variant="premium">
              {acceptInvitation.isPending ? "Confirmando..." : "Confirmar e ativar acesso"}
            </Button>
          </form>
        )}
      </section>
    </main>
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
          O login está liberado, mas o acesso financeiro fica bloqueado até a confirmação do e-mail. Confira sua caixa de entrada ou solicite um novo envio.
        </p>
        <label className="field" htmlFor="verification-token">
          Código de verificação
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

function SubscriptionBlocked({ subscription, canManage }: { subscription: Subscription; canManage: boolean }) {
  return (
    <section className="panel max-w-4xl space-y-3">
      <Badge variant="warning">{subscriptionStatusText(subscription.status)}</Badge>
      <h2 className="panel-title">
        {subscription.status === "trialing" ? "Seu período gratuito terminou." : "A assinatura não está ativa."}
      </h2>
      <p className="text-sm leading-6 text-muted">
        {subscription.status === "blocked"
          ? "O acesso foi bloqueado pelo administrador da plataforma. Entre em contato com o suporte."
          : "Para continuar usando as áreas financeiras, escolha um plano mensal."}
      </p>
      {subscription.status !== "blocked" && <SubscriptionCheckout canManage={canManage} />}
    </section>
  );
}

export default function App() {
  const [token, setCurrentToken] = useState(getToken());
  const [invitationToken, setInvitationToken] = useState<string | null>(
    () => new URLSearchParams(window.location.search).get("company_invite_token"),
  );
  const queryClient = useQueryClient();
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

  const continueToLogin = useCallback(() => {
    const url = new URL(window.location.href);
    url.searchParams.delete("company_invite_token");
    window.history.replaceState({}, "", `${url.pathname}${url.search}${url.hash}`);
    clearToken();
    queryClient.clear();
    setCurrentToken(null);
    setInvitationToken(null);
  }, [queryClient]);

  const publicPage = new URLSearchParams(window.location.search).get("pagina");
  if (publicPage === "sobre" || publicPage === "contato") {
    return <PublicInfoPage page={publicPage} />;
  }

  return (
    <TooltipProvider>
      {invitationToken ? (
        <CompanyUserInvitationScreen invitationToken={invitationToken} onContinueToLogin={continueToLogin} />
      ) : !token ?(
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
