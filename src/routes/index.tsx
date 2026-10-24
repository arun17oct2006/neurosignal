import { createFileRoute, useNavigate } from "@tanstack/react-router";
import { SingleSignOn } from "@/components/SingleSignOn";

export const Route = createFileRoute("/")({
  head: () => ({
    meta: [
      { title: "neurosignal — Quantitative Trend Intelligence" },
      { name: "description", content: "Machine-learning stock trend signals, RSI analytics and a quant research assistant." },
      { property: "og:title", content: "neurosignal — Quantitative Trend Intelligence" },
      { property: "og:description", content: "Machine-learning stock trend signals, RSI analytics and a quant research assistant." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Landing,
});

function Landing() {
  const navigate = useNavigate();

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-8 py-4">
        <span className="font-display text-lg font-bold tracking-tight">
          neuro<span className="text-control">signal</span>
        </span>
      </header>

      <main className="mx-auto grid w-full max-w-6xl flex-1 items-center gap-16 px-8 py-16 lg:grid-cols-2">
        <section>
          <p className="metric text-[11px] uppercase tracking-[0.3em] text-control">Quantitative research platform</p>
          <h1 className="mt-5 font-display text-5xl font-bold leading-[1.05] tracking-tight">
            Signal over noise.
            <br />
            <span className="text-muted-foreground">Decisions over guesses.</span>
          </h1>
          <p className="mt-6 max-w-md text-sm leading-relaxed text-muted-foreground">
            neurosignal scores stocks with gradient-boosted and deep learning models, momentum analytics
            and a research assistant that reads the tape with you, in one focused workspace.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-6 border-t pt-8">
            {[
              ["4", "ML models ensembled"],
              ["14d", "RSI momentum window"],
              ["<1s", "signal latency"],
            ].map(([v, l]) => (
              <div key={l}>
                <dt className="metric text-2xl font-semibold text-foreground">{v}</dt>
                <dd className="mt-1 text-[11px] uppercase tracking-wider text-muted-foreground">{l}</dd>
              </div>
            ))}
          </dl>
        </section>

        <section className="panel mx-auto w-full max-w-sm p-8">
          <h2 className="font-display text-xl font-semibold">Sign in</h2>
          <p className="mt-2 text-xs text-muted-foreground">
            Sign in with Google to open your research workspace.
          </p>
          <div className="mt-6">
            <SingleSignOn onSignedIn={() => navigate({ to: "/dashboard" })} />
          </div>
        </section>
      </main>

      <footer className="border-t px-8 py-4 text-center text-[11px] text-muted-foreground">
        neurosignal — analytics for research purposes only. Not investment advice.
      </footer>
    </div>
  );
}