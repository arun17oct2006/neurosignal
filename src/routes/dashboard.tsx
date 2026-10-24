import { createFileRoute, Link, redirect, useNavigate } from "@tanstack/react-router";
import { useEffect, useState } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import { analyzeDataset, fetchAnalysis, fetchPersonalization, recordInteraction } from "@/services/api";
import { getSession, type StoredSession } from "@/services/session";
import type { AnalysisResponse } from "@/types/market";
import { KpiTape } from "@/components/KpiTape";
import { StockChart } from "@/components/StockChart";
import { SignalCard } from "@/components/SignalCard";
import { DatasetUploader } from "@/components/DatasetUploader";
import { QuantChatbot } from "@/components/QuantChatbot";
import { UserMenu } from "@/components/UserMenu";
import { ModelPanel } from "@/components/ModelPanel";
import { TrendingStocks, TRENDING_SYMBOLS } from "@/components/TrendingStocks";
import { TrendingWorldwide } from "@/components/TrendingWorldwide";

export const Route = createFileRoute("/dashboard")({
  // Sign-in is mandatory: no session means back to the landing page.
  // Checked only in the browser, because localStorage does not exist on the server.
  beforeLoad: () => {
    if (typeof window !== "undefined" && !getSession()) {
      throw redirect({ to: "/" });
    }
  },
  head: () => ({
    meta: [
      { title: "Dashboard — neurosignal" },
      { name: "description", content: "ML-driven stock trend signals, RSI analytics and a quant research assistant." },
      { property: "og:title", content: "Dashboard — neurosignal" },
      { property: "og:description", content: "ML-driven stock trend signals, RSI analytics and a quant research assistant." },
      { property: "og:type", content: "website" },
      { name: "twitter:card", content: "summary_large_image" },
    ],
  }),
  component: Dashboard,
});

function Dashboard() {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [ticker, setTicker] = useState("");
  const [search, setSearch] = useState("");
  const [focused, setFocused] = useState(false);
  const [uploaded, setUploaded] = useState<AnalysisResponse | null>(null);
  const [session, setSession] = useState<StoredSession | null>(null);
  const [checked, setChecked] = useState(false);

  useEffect(() => {
    const s = getSession();
    if (!s) {
      navigate({ to: "/" });
      return;
    }
    setSession(s);
    setChecked(true);
  }, [navigate]);

  const q = useQuery({
    queryKey: ["analysis", ticker],
    queryFn: () => fetchAnalysis(ticker),
    enabled: !uploaded && Boolean(ticker),
  });

  const personalization = useQuery({
    queryKey: ["personalization", session?.user_id],
    queryFn: fetchPersonalization,
    enabled: Boolean(session),
    retry: false,
  });

  const interaction = useMutation({
    mutationFn: recordInteraction,
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ["personalization"] }),
  });

  const upload = useMutation({
    mutationFn: (v: { label: string; rows: { date: string; close: number }[] }) =>
      analyzeDataset(v.label, v.rows),
    onSuccess: setUploaded,
  });

  const data = uploaded ?? q.data;
  const showPicks = !uploaded && !ticker;
  const loading = upload.isPending || (!uploaded && Boolean(ticker) && q.isLoading);
  const err = upload.error ?? (!uploaded && ticker ? q.error : null);

  const saved = personalization.data?.recommended_tickers ?? [];
  const quickPicks = (saved.length ? saved : TRENDING_SYMBOLS).slice(0, 6);

  const pick = (raw: string) => {
    const selected = raw.trim().toUpperCase();
    if (!selected) return;
    setUploaded(null);
    upload.reset();
    setTicker(selected);
    if (session) interaction.mutate(selected);
  };

  const backToPicks = () => {
    setUploaded(null);
    upload.reset();
    setTicker("");
  };

  if (!checked) return null;

  return (
    <div className="min-h-screen">
      <nav className="flex flex-wrap items-center gap-6 border-b px-8 py-3.5">
        <Link to="/dashboard" className="font-display text-lg font-bold tracking-tight">
          Neuro<span className="text-control">signal</span>
        </Link>

        <div className="flex flex-1 flex-wrap items-center gap-4">
          <form
            onSubmit={(e) => {
              e.preventDefault();
              if (search.trim()) pick(search);
              setSearch("");
              setFocused(false);
            }}
            className="relative flex h-9 w-full max-w-md items-stretch overflow-hidden rounded-sm border bg-card transition focus-within:border-control"
          >
            <div className="flex flex-1 items-center gap-2 px-3">
              <svg viewBox="0 0 24 24" className="h-3.5 w-3.5 shrink-0 text-muted-foreground" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="11" cy="11" r="7" />
                <path d="m20 20-3.5-3.5" />
              </svg>
              <input
                value={search}
                onChange={(e) => setSearch(e.target.value)}
                onFocus={() => setFocused(true)}
                onBlur={() => setTimeout(() => setFocused(false), 120)}
                placeholder="Search symbol, e.g. NVDA or RELIANCE.NS"
                className="metric w-full bg-transparent text-sm uppercase outline-none placeholder:normal-case placeholder:text-muted-foreground"
              />
            </div>
            <button
              type="submit"
              disabled={!search.trim()}
              className="border-l px-4 text-xs font-semibold uppercase tracking-wider text-muted-foreground transition hover:bg-primary hover:text-primary-foreground disabled:opacity-40 disabled:hover:bg-transparent disabled:hover:text-muted-foreground"
            >
              Analyze
            </button>
            {focused && (
              <div className="absolute left-0 right-0 top-full z-50 mt-1 rounded-sm border bg-card py-1 shadow-lg">
                <p className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">
                  {saved.length ? "For you" : "Quick picks"}
                </p>
                {quickPicks
                  .filter((c) => c.includes(search.trim().toUpperCase()))
                  .map((c) => (
                    <button
                      type="button"
                      key={c}
                      onMouseDown={(e) => {
                        e.preventDefault();
                        pick(c);
                        setSearch("");
                        setFocused(false);
                      }}
                      className="metric flex w-full items-center justify-between px-3 py-1.5 text-left text-sm hover:bg-background"
                    >
                      <span>{c}</span>
                      {!uploaded && ticker === c && <span className="text-[10px] text-control">ACTIVE</span>}
                    </button>
                  ))}
              </div>
            )}
          </form>
        </div>

        <UserMenu />
      </nav>

      <main className="mx-auto max-w-[1440px] space-y-4 p-6">
        {interaction.error && (
          <div className="rounded-lg border border-sell/50 bg-sell/10 px-4 py-3 text-sm text-sell">
            Could not save this interaction: {interaction.error.message}
          </div>
        )}
        {personalization.error && (
          <div className="rounded-lg border border-neutral/50 bg-neutral/10 px-4 py-3 text-sm text-neutral">
            Could not load your saved preferences: {personalization.error.message}
          </div>
        )}
        {err && (
          <div className="flex items-center justify-between rounded-lg border border-sell/50 bg-sell/10 px-4 py-3 text-sm text-sell">
            <span>Analysis failed: {err.message}</span>
            {!uploaded && <button onClick={() => q.refetch()} className="underline">Retry</button>}
          </div>
        )}

        {showPicks ? (
          <div className="space-y-4">
            <TrendingStocks onPick={pick} />
            <TrendingWorldwide onPick={pick} />
          </div>
        ) : (
          <>
            <div className="flex items-center justify-between">
              <button onClick={backToPicks} className="text-xs text-muted-foreground transition hover:text-foreground">
                ← Top stocks
              </button>
              {data && <span className="metric text-xs text-muted-foreground">{data.ticker}</span>}
            </div>
            <KpiTape data={data} loading={loading} />
            <div className="grid gap-4 lg:grid-cols-[65fr_35fr]">
              <div className="space-y-4">
                <StockChart data={data?.chart_data} loading={loading} />
                <DatasetUploader onParsed={(label, rows) => upload.mutate({ label, rows })} />
              </div>
              <SignalCard data={data} loading={loading} />
            </div>
            <ModelPanel data={data} />
          </>
        )}
      </main>

      <QuantChatbot ticker={data?.ticker ?? (ticker || undefined)} />
    </div>
  );
}