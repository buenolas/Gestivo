import { brandAssets } from "../assets/brand";

const teamMembers = [
  {
    name: "Fundador do Gestivo",
    role: null,
    image: "/images/team/founder.png",
    imageAlt: "Retrato do fundador do Gestivo",
    description:
      "A experiência trabalhando próximo de comércios mostrou como o controle em planilhas e papel podia complicar a rotina financeira.",
  },
  {
    name: "Ester",
    role: "Diretora Comercial",
    image: "/images/team/ester.png",
    imageAlt: "Retrato de Ester, diretora comercial do Gestivo",
    description:
      "No comercial, Ester aproxima o Gestivo das empresas e das pessoas que buscam mais organização e clareza financeira.",
  },
];

export function PublicInfoPage({ page }: { page: "sobre" | "contato" }) {
  const isAbout = page === "sobre";

  return (
    <main className="min-h-screen bg-[#f7f9f7] text-ink">
      <header className="mx-auto flex max-w-6xl items-center justify-between gap-4 px-6 py-6">
        <a href="/" aria-label="Gestivo, início">
          <img className="h-11 w-auto" src={brandAssets.logoPrimary} alt="Gestivo" />
        </a>
        <a href="/" className="whitespace-nowrap text-sm font-semibold text-emerald-700">
          ← Voltar para o início
        </a>
      </header>

      {isAbout ? (
        <article className="mx-auto max-w-6xl px-6 pb-20 pt-12 sm:pb-28 sm:pt-16">
          <div className="mx-auto max-w-4xl">
            <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-600">
              Sobre o Gestivo
            </p>
            <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-6xl">
              Mais clareza para quem faz o negócio acontecer.
            </h1>
            <p className="mt-6 max-w-2xl text-lg leading-8 text-slate-600">
              O Gestivo é uma plataforma de gestão financeira para empresas que querem organizar
              seus números e tomar decisões com mais clareza.
            </p>
          </div>

          <section className="mt-14 grid gap-8 rounded-3xl border border-slate-100 bg-white p-6 sm:p-10 lg:grid-cols-[0.8fr_1.2fr] lg:gap-14">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-600">
                Nossa origem
              </p>
              <h2 className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                Uma necessidade real, vista de perto.
              </h2>
            </div>
            <div className="space-y-5 text-base leading-7 text-slate-600 sm:text-lg sm:leading-8">
              <p>
                A ideia do Gestivo nasceu de uma necessidade que encontrei em comércios onde
                trabalhei e com os quais tive contato: organizar o financeiro do dia a dia.
              </p>
              <p>
                Em muitos deles, as informações ficavam espalhadas entre planilhas complicadas e
                anotações em papel. Reunir entradas, saídas e compromissos exigia esforço, e nem
                sempre era fácil ter uma visão clara do caixa.
              </p>
              <p>
                O Gestivo surgiu para tornar esse acompanhamento mais simples e visual, reunindo
                os números importantes em um só lugar para apoiar decisões com mais segurança.
              </p>
            </div>
          </section>

          <section className="mt-20" aria-labelledby="team-title">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
              <div>
                <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-600">
                  Quem faz acontecer
                </p>
                <h2 id="team-title" className="mt-4 text-3xl font-bold tracking-tight sm:text-4xl">
                  Pessoas por trás do Gestivo.
                </h2>
              </div>
              <p className="max-w-md text-base leading-7 text-slate-600">
                Uma equipe próxima da realidade das empresas e comprometida em deixar a gestão
                financeira mais clara.
              </p>
            </div>

            <div className="mt-8 grid gap-6 sm:grid-cols-2">
              {teamMembers.map((member) => (
                <figure
                  key={member.name}
                  className="overflow-hidden rounded-3xl border border-slate-100 bg-white shadow-sm"
                >
                  <div className="aspect-[4/3] overflow-hidden bg-slate-100">
                    <img
                      className="h-full w-full object-cover object-center"
                      src={member.image}
                      alt={member.imageAlt}
                      loading="lazy"
                    />
                  </div>
                  <figcaption className="p-6 sm:p-7">
                    <h3 className="text-xl font-bold tracking-tight sm:text-2xl">{member.name}</h3>
                    {member.role && (
                      <p className="mt-1 text-sm font-semibold text-emerald-700">{member.role}</p>
                    )}
                    <p className="mt-4 text-sm leading-6 text-slate-600 sm:text-base sm:leading-7">
                      {member.description}
                    </p>
                  </figcaption>
                </figure>
              ))}
            </div>
          </section>

          <section className="mt-20 flex flex-col gap-6 rounded-3xl bg-ink p-7 text-white sm:p-10 md:flex-row md:items-center md:justify-between">
            <div>
              <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-300">
                Vamos conversar?
              </p>
              <h2 className="mt-3 max-w-2xl text-2xl font-bold tracking-tight sm:text-3xl">
                Conte para a gente como você organiza o financeiro da sua empresa.
              </h2>
            </div>
            <a
              href="/?pagina=contato"
              className="inline-flex shrink-0 items-center justify-center rounded-full bg-highlight px-6 py-3 text-sm font-bold text-ink hover:bg-lime-300"
            >
              Fale com a gente
            </a>
          </section>
        </article>
      ) : (
        <article className="mx-auto max-w-4xl px-6 py-16 sm:py-24">
          <p className="text-xs font-bold uppercase tracking-[0.18em] text-emerald-600">
            Fale com a gente
          </p>
          <h1 className="mt-5 text-4xl font-bold tracking-tight sm:text-6xl">Vamos conversar?</h1>
          <div className="mt-8 max-w-2xl text-lg leading-8 text-slate-600">
            <p>Quer conhecer o Gestivo ou tirar uma dúvida? Nossa equipe está disponível pelos canais abaixo.</p>
            <div className="mt-8 grid gap-4 sm:grid-cols-2">
              <a
                className="break-all rounded-2xl border border-slate-200 bg-white p-6 text-base font-semibold text-ink"
                href="mailto:gestivo@bubassoftware.com.br"
              >
                <span className="block text-sm font-normal text-slate-500">E-mail</span>
                gestivo@bubassoftware.com.br
              </a>
              <a
                className="rounded-2xl border border-slate-200 bg-white p-6 text-base font-semibold text-ink"
                href="tel:+556231901862"
              >
                <span className="block text-sm font-normal text-slate-500">Telefone</span>
                (62) 3190-1862
              </a>
            </div>
          </div>
        </article>
      )}
    </main>
  );
}
