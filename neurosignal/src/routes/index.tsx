import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";

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

function GoogleMark() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4" aria-hidden>
      <path fill="#EA4335" d="M12 5.04c1.7 0 3.22.58 4.42 1.73l3.3-3.3C17.74 1.5 15.1.5 12 .5 7.4.5 3.44 3.13 1.53 6.7l3.86 3C6.35 7.1 8.93 5.04 12 5.04Z" />
      <path fill="#4285F4" d="M23.5 12.27c0-.85-.08-1.66-.22-2.45H12v4.64h6.45a5.52 5.52 0 0 1-2.39 3.62l3.7 2.87c2.17-2 3.74-4.95 3.74-8.68Z" />
      <path fill="#FBBC05" d="M5.4 14.3a7.06 7.06 0 0 1 0-4.6l-3.87-3A11.5 11.5 0 0 0 .5 12c0 1.85.44 3.6 1.03 5.16L5.4 14.3Z" />
      <path fill="#34A853" d="M12 23.5c3.1 0 5.7-1.02 7.6-2.78l-3.7-2.87c-1.03.7-2.35 1.1-3.9 1.1-3.07 0-5.65-2.06-6.6-4.8l-3.87 3C3.44 20.87 7.4 23.5 12 23.5Z" />
    </svg>
  );
}

function Landing() {
  const [mode, setMode] = useState<"signin" | "signup">("signin");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [note, setNote] = useState<string | null>(null);

  return (
    <div className="flex min-h-screen flex-col">
      <header className="flex items-center justify-between border-b px-8 py-4">
        <span className="font-display text-lg font-bold tracking-tight">
          neuro<span className="text-control">signal</span>
        </span>
        <Link to="/dashboard" className="text-xs text-muted-foreground transition hover:text-foreground">
          Live demo →
        </Link>
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
            neurosignal scores equities with gradient-boosted models, momentum analytics and a
            research assistant that reads the tape with you — in one focused workspace.
          </p>
          <dl className="mt-10 grid max-w-md grid-cols-3 gap-6 border-t pt-8">
            {[
              ["2", "ML models ensembled"],
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
          <div className="grid grid-cols-2 gap-1 rounded-sm border bg-background p-1 text-sm">
            {(["signin", "signup"] as const).map((m) => (
              <button
                key={m}
                type="button"
                onClick={() => { setMode(m); setNote(null); }}
                className={`rounded-sm py-1.5 font-medium transition ${
                  mode === m ? "bg-primary text-primary-foreground" : "text-muted-foreground hover:text-foreground"
                }`}
              >
                {m === "signin" ? "Sign in" : "Sign up"}
              </button>
            ))}
          </div>

          <p className="mt-4 text-xs text-muted-foreground">
            {mode === "signin" ? "Access your research workspace." : "Create your research workspace."}
          </p>

          <button
            type="button"
            onClick={() => setNote("Google sign-in isn't connected yet — coming soon.")}
            className="mt-4 flex w-full items-center justify-center gap-3 rounded-sm border bg-background px-4 py-2.5 text-sm font-medium transition hover:border-control"
          >
            <GoogleMark />
            {mode === "signin" ? "Continue with Google" : "Sign up with Google"}
          </button>

          <div className="my-5 flex items-center gap-3 text-[10px] uppercase tracking-widest text-muted-foreground">
            <span className="h-px flex-1 bg-border" /> or <span className="h-px flex-1 bg-border" />
          </div>

          <form
            onSubmit={(e) => {
              e.preventDefault();
              setNote(
                mode === "signin"
                  ? "Email sign-in will be enabled once the backend is connected."
                  : "Account creation will be enabled once the backend is connected.",
              );
            }}
            className="space-y-3"
          >
            {mode === "signup" && (
              <input
                required
                value={name}
                onChange={(e) => setName(e.target.value)}
                placeholder="Full name"
                className="w-full rounded-sm border bg-background px-3 py-2.5 text-sm outline-none transition focus:border-control"
              />
            )}
            <input
              type="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              placeholder="you@fund.com"
              className="w-full rounded-sm border bg-background px-3 py-2.5 text-sm outline-none transition focus:border-control"
            />
            <button className="w-full rounded-sm bg-primary py-2.5 text-sm font-semibold text-primary-foreground transition hover:opacity-90">
              {mode === "signin" ? "Continue with email" : "Create account"}
            </button>
          </form>

          {note && <p className="mt-4 rounded-sm border border-neutral/40 bg-neutral/10 px-3 py-2 text-xs text-neutral">{note}</p>}

          <p className="mt-6 text-center text-[11px] text-muted-foreground">
            Just exploring?{" "}
            <Link to="/dashboard" className="text-control underline-offset-2 hover:underline">
              Open the dashboard
            </Link>
          </p>
        </section>
      </main>

      <footer className="border-t px-8 py-4 text-center text-[11px] text-muted-foreground">
        neurosignal — analytics for research purposes only. Not investment advice.
      </footer>
    </div>
  );
}
