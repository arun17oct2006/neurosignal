import { createFileRoute, Link } from "@tanstack/react-router";
import { useState } from "react";
import { useMutation, useQuery } from "@tanstack/react-query";
import { analyzeDataset, fetchAnalysis } from "@/services/api";
import type { AnalysisResponse } from "@/types/market";
import { KpiTape } from "@/components/KpiTape";
import { StockChart } from "@/components/StockChart";
import { SignalCard } from "@/components/SignalCard";
import { DatasetUploader } from "@/components/DatasetUploader";
import { QuantChatbot } from "@/components/QuantChatbot";
import { UserMenu } from "@/components/UserMenu";

export const Route = createFileRoute("/dashboard")({
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

const CHIPS = ["AAPL", "MSFT", "TSLA", "GOOGL"];

function Dashboard() {
  const [ticker, setTicker] = useState("AAPL");
  const [search, setSearch] = useState("");
  const [focused, setFocused] = useState(false);
  const [uploaded, setUploaded] = useState<AnalysisResponse | null>(null);

  const q = useQuery({
    queryKey: ["analysis", ticker],
    queryFn: () => fetchAnalysis(ticker),
    enabled: !uploaded,
  });
  const upload = useMutation({
    mutationFn: (v: { label: string; rows: { date: string; close: number }[] }) => analyzeDataset(v.label, v.rows),
    onSuccess: setUploaded,
  });

  const data = uploaded ?? q.data;
  const loading = upload.isPending || (!uploaded && q.isLoading);
  const err = upload.error ?? (!uploaded ? q.error : null);

  const pick = (t: string) => { setUploaded(null); upload.reset(); setTicker(t.toUpperCase()); };

  return (
    <div className="min-h-screen">
      <nav className="flex flex-wrap items-center gap-6 border-b px-8 py-3.5">
        <Link to="/" className="font-display text-lg font-bold tracking-tight">
          Neuro<span className="text-control">signal</span>
        </Link>

        <div className="flex flex-1 flex-wrap items-center gap-4">
          <form
            onSubmit={(e) => { e.preventDefault(); if (search.trim()) pick(search); setSearch(""); setFocused(false); }}
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
                placeholder="Search symbol, e.g. NVDA"
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
                <p className="px-3 py-1.5 text-[10px] uppercase tracking-wider text-muted-foreground">Quick picks</p>
                {CHIPS.filter((c) => c.includes(search.trim().toUpperCase())).map((c) => (
                  <button
                    type="button"
                    key={c}
                    onMouseDown={(e) => { e.preventDefault(); pick(c); setSearch(""); setFocused(false); }}
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
        {err && (
          <div className="flex items-center justify-between rounded-lg border border-sell/50 bg-sell/10 px-4 py-3 text-sm text-sell">
            <span>Analysis failed: {err.message}</span>
            {!uploaded && <button onClick={() => q.refetch()} className="underline">Retry</button>}
          </div>
        )}
        <KpiTape data={data} loading={loading} />
        <div className="grid gap-4 lg:grid-cols-[65fr_35fr]">
          <div className="space-y-4">
            <StockChart data={data?.chart_data} loading={loading} />
            <DatasetUploader onParsed={(label, rows) => upload.mutate({ label, rows })} />
          </div>
          <SignalCard data={data} loading={loading} />
        </div>
      </main>

      <QuantChatbot
        context={data ? { ticker: data.ticker, rsi: data.rsi_now, signal: data.signal, target: data.target_price } : undefined}
      />
    </div>
  );
}
