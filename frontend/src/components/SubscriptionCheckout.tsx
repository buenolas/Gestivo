import { useMutation, useQuery } from "@tanstack/react-query";
import { apiFetch } from "../api";
import type { Plan } from "../types";
import { Button } from "@/components/ui/button";

type Props = {
  canManage: boolean;
};

export function SubscriptionCheckout({ canManage }: Props) {
  const plans = useQuery({
    queryKey: ["public-plans"],
    queryFn: () => apiFetch<Plan[]>("/plans"),
  });
  const checkout = useMutation({
    mutationFn: (planSlug: string) =>
      apiFetch<{ url: string }>("/subscription/checkout", {
        method: "POST",
        body: JSON.stringify({ plan_slug: planSlug }),
      }),
    onSuccess: ({ url }) => window.location.assign(url),
  });

  return (
    <section className="mt-5 space-y-4">
      <div>
        <h3 className="text-lg font-bold text-ink">Escolha seu plano mensal</h3>
        <p className="mt-1 text-sm leading-6 text-muted">
          Pagamento e renovação recorrentes são processados no Checkout seguro do Stripe.
        </p>
      </div>

      {plans.isLoading && <p className="text-sm text-muted">Carregando planos...</p>}
      {plans.isError && <p className="alert-error">{plans.error.message}</p>}
      {checkout.error && <p className="alert-error">{checkout.error.message}</p>}
      {!canManage && (
        <p className="rounded-md border border-line bg-panel p-3 text-sm text-muted">
          Peça ao administrador da empresa para escolher e contratar um plano.
        </p>
      )}

      {plans.data && (
        <div className="grid gap-3 sm:grid-cols-2">
          {plans.data.map((plan) => (
            <article key={plan.id} className="flex flex-col rounded-lg border border-line bg-white p-4">
              <div className="flex-1">
                <h4 className="font-bold text-ink">{plan.name}</h4>
                {plan.description && <p className="mt-1 text-sm leading-5 text-muted">{plan.description}</p>}
                <p className="mt-4 text-xl font-bold text-accent">
                  {formatBRL(plan.price)} <span className="text-sm font-medium text-muted">/ mês</span>
                </p>
              </div>
              <Button
                className="mt-4 w-full"
                variant="premium"
                disabled={!canManage || checkout.isPending}
                onClick={() => checkout.mutate(plan.slug)}
              >
                {checkout.isPending ? "Abrindo Checkout..." : `Assinar ${plan.name}`}
              </Button>
            </article>
          ))}
        </div>
      )}
    </section>
  );
}

function formatBRL(value: string) {
  const [wholePart, fractionalPart = "00"] = value.split(".");
  const whole = wholePart.replace(/\B(?=(\d{3})+(?!\d))/g, ".");
  const fraction = fractionalPart.slice(0, 2).padEnd(2, "0");
  return `R$ ${whole},${fraction}`;
}
