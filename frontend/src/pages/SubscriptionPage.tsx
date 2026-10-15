import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api";
import { SubscriptionCheckout } from "../components/SubscriptionCheckout";
import type { Plan, Subscription } from "../types";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";

const planOrder: Record<Plan["slug"], number> = {
  basic: 0,
  intermediate: 1,
  advanced: 2,
  pro: 3,
};

type Props = {
  subscription: Subscription;
  canManage: boolean;
};

export function SubscriptionPage({ subscription, canManage }: Props) {
  const plans = useQuery({
    queryKey: ["public-plans"],
    queryFn: () => apiFetch<Plan[]>("/plans"),
  });
  const upgrade = useMutation({
    mutationFn: (planSlug: Plan["slug"]) =>
      apiFetch<{ url: string }>("/subscription/upgrade", {
        method: "POST",
        body: JSON.stringify({ plan_slug: planSlug }),
      }),
    onSuccess: ({ url }) => window.location.assign(url),
  });

  if (subscription.status !== "active") {
    return (
      <section className="panel max-w-5xl space-y-4">
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-accent">CONTA E COBRANÇA</p>
          <h2 className="panel-title">Planos e assinatura</h2>
        </div>
        <div className="rounded-lg border border-line bg-white p-4">
          <Badge variant={subscription.status === "blocked" ? "warning" : "outline"}>
            {subscriptionStatusLabel(subscription.status)}
          </Badge>
          <p className="mt-3 text-sm leading-6 text-muted">
            {subscription.status === "trialing"
              ? `Seu teste gratuito está ativo${subscription.access_until ? ` até ${formatDate(subscription.access_until)}` : ""}. Você poderá escolher um plano quando ele terminar.`
              : subscription.status === "blocked"
                ? "A assinatura foi bloqueada pela administração da plataforma. Entre em contato com o suporte."
                : "Escolha um plano mensal para contratar ou reativar sua assinatura pelo Checkout seguro do Stripe."}
          </p>
        </div>
        {subscription.status !== "blocked" && subscription.status !== "trialing" && (
          <SubscriptionCheckout canManage={canManage} />
        )}
        {!canManage && (
          <p className="rounded-md border border-line bg-panel p-3 text-sm text-muted">
            Apenas o administrador da empresa pode contratar ou alterar o plano.
          </p>
        )}
      </section>
    );
  }

  const currentPlan = plans.data?.find((plan) => plan.slug === subscription.plan_slug);
  const currentRank = currentPlan ? planOrder[currentPlan.slug] : -1;
  const upgradeOptions = (plans.data ?? []).filter((plan) => planOrder[plan.slug] > currentRank);
  const canUpgrade = canManage && subscription.can_manage_billing && currentRank >= 0;

  return (
    <section className="space-y-5">
      <header>
        <p className="text-xs font-semibold uppercase tracking-wide text-accent">CONTA E COBRANÇA</p>
        <h2 className="section-title">Planos e assinatura</h2>
        <p className="section-subtitle">Consulte seu plano e escolha outro nível quando precisar de mais recursos.</p>
      </header>

      <section className="panel space-y-4">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-muted">Plano atual</p>
            <h3 className="mt-1 text-xl font-bold text-ink">{subscription.plan_name ?? currentPlan?.name ?? "Assinatura ativa"}</h3>
          </div>
          <Badge variant="success">Ativa</Badge>
        </div>
        {currentPlan && (
          <div className="flex flex-wrap items-baseline gap-x-2 gap-y-1">
            <span className="text-2xl font-bold text-ink">{formatBRL(currentPlan.price)}</span>
            <span className="text-sm text-muted">por mês</span>
          </div>
        )}
        <p className="text-sm leading-6 text-muted">
          {currentPlan?.description ?? "A cobrança é mensal e processada pelo Stripe."}
        </p>
        {subscription.access_until && (
          <p className="text-sm text-muted">Acesso atual até {formatDate(subscription.access_until)}.</p>
        )}
      </section>

      <section className="space-y-3">
        <div>
          <h3 className="panel-title">Faça upgrade</h3>
          <p className="mt-1 text-sm leading-6 text-muted">
            A alteração será apresentada para confirmação no Stripe. O Gestivo atualiza os recursos após receber a confirmação da assinatura.
          </p>
        </div>

        {plans.isLoading && <p className="text-sm text-muted">Carregando planos...</p>}
        {plans.isError && <p className="alert-error">{plans.error.message}</p>}
        {upgrade.error && <p className="alert-error">{upgrade.error.message}</p>}
        {!canUpgrade && (
          <p className="rounded-md border border-line bg-white p-3 text-sm text-muted">
            {canManage
              ? "Não foi possível identificar o vínculo de cobrança Stripe desta assinatura. Entre em contato com o suporte para continuar."
              : "Apenas o administrador da empresa pode alterar o plano."}
          </p>
        )}
        {plans.data && upgradeOptions.length === 0 && currentRank >= 0 && (
          <p className="rounded-md border border-line bg-white p-4 text-sm text-muted">
            Você já está no plano mais completo disponível.
          </p>
        )}
        {upgradeOptions.length > 0 && (
          <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
            {upgradeOptions.map((plan) => (
              <article key={plan.id} className="flex flex-col rounded-lg border border-line bg-white p-4">
                <div className="flex-1">
                  <h4 className="font-bold text-ink">{plan.name}</h4>
                  <p className="mt-2 text-sm leading-5 text-muted">{plan.description}</p>
                  <p className="mt-4 text-xl font-bold text-accent">
                    {formatBRL(plan.price)} <span className="text-sm font-medium text-muted">/ mês</span>
                  </p>
                  <p className="mt-2 text-xs text-muted">{aiLimitText(plan.ai_daily_limit)}</p>
                </div>
                <Button
                  className="mt-4 w-full"
                  variant="premium"
                  disabled={!canUpgrade || upgrade.isPending}
                  onClick={() => upgrade.mutate(plan.slug)}
                >
                  {upgrade.isPending ? "Abrindo confirmação..." : `Fazer upgrade para ${plan.name}`}
                </Button>
              </article>
            ))}
          </div>
        )}
      </section>
    </section>
  );
}

function subscriptionStatusLabel(status: Subscription["status"]) {
  const labels: Record<Subscription["status"], string> = {
    trialing: "Teste gratuito",
    active: "Ativa",
    pending_payment: "Pagamento pendente",
    canceled: "Cancelada",
    blocked: "Bloqueada",
  };
  return labels[status];
}

function aiLimitText(limit: number | null) {
  if (limit === null) return "Assistente financeiro sem limite diário";
  if (limit === 0) return "Sem acesso ao assistente financeiro";
  return `${limit} ${limit === 1 ? "interação" : "interações"} com a IA por dia`;
}

function formatDate(value: string) {
  return new Date(value).toLocaleDateString("pt-BR");
}

function formatBRL(value: string) {
  const [wholePart, fractionalPart = "00"] = value.split(".");
  const whole = wholePart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const fraction = fractionalPart.slice(0, 2).padEnd(2, "0");
  return `R$ ${whole},${fraction}`;
}
