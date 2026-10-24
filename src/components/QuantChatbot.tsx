import { useEffect, useRef, useState } from "react";

type Stock = {
  ticker: string;
  name: string;
  sector?: string | null;
  industry?: string | null;
  price: number | null;
  change_pct: number | null;
  currency_symbol: string;
  summary: string;
};

type Msg = { role: "user" | "bot"; text: string; meta?: string; stock?: Stock | null };

const API_URL = import.meta.env.VITE_NEUROSIGNAL_API_URL ?? "http://localhost:8000";

function StockCard({ s }: { s: Stock }) {
  const up = (s.change_pct ?? 0) >= 0;
  return (
    <div className="mb-2 rounded-lg border border-white/10 bg-neutral-900 p-3">
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-sm font-semibold">{s.name}</p>
          <p className="text-[11px] opacity-60">
            {s.ticker}
            {s.sector ? ` · ${s.sector}` : ""}
          </p>
        </div>
        <div className="text-right">
          {s.price != null && <p className="text-sm font-semibold">{s.currency_symbol}{s.price.toFixed(2)}</p>}
          {s.change_pct != null && (
            <p className={`text-xs ${up ? "text-emerald-400" : "text-red-400"}`}>
              {up ? "+" : ""}{s.change_pct}% today
            </p>
          )}
        </div>
      </div>
      {s.summary && <p className="mt-2 text-xs leading-relaxed opacity-70">{s.summary}</p>}
    </div>
  );
}

export function QuantChatbot({ ticker }: { ticker?: string }) {
  const [input, setInput] = useState("");
  const [loading, setLoading] = useState(false);
  const [messages, setMessages] = useState<Msg[]>([
    { role: "bot", text: "Hi, I'm Neuro. Ask about any stock, like \"What is NVIDIA's outlook?\" or \"Price of Reliance\"." },
  ]);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, loading]);

  async function send() {
    const q = input.trim();
    if (!q || loading) return;
    setInput("");
    setMessages((m) => [...m, { role: "user", text: q }]);
    setLoading(true);

    try {
      const res = await fetch(`${API_URL}/chat/ask`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ question: q, ticker }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.detail ?? `Request failed (${res.status})`);

      const meta = data.cache_hit
        ? "cached"
        : data.provider
        ? [data.provider, data.model].filter(Boolean).join(" · ")
        : undefined;

      setMessages((m) => [...m, { role: "bot", text: data.answer, meta, stock: data.stock ?? null }]);
    } catch (err) {
      const reason = err instanceof Error ? err.message : "Unknown error";
      setMessages((m) => [...m, { role: "bot", text: `Sorry, I couldn't get an answer. ${reason}` }]);
    } finally {
      setLoading(false);
    }
  }

  function onKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      send();
    }
  }

  return (
    <div className="flex h-[560px] w-full max-w-2xl flex-col rounded-xl border border-white/10 bg-neutral-900 text-neutral-100">
      <div className="border-b border-white/10 px-4 py-3 font-semibold">
        Ask Neuro{ticker ? ` · ${ticker}` : ""}
      </div>

      <div className="flex-1 space-y-3 overflow-y-auto p-4">
        {messages.map((m, i) => (
          <div key={i} className={`flex ${m.role === "user" ? "justify-end" : "justify-start"}`}>
            <div
              className={`max-w-[85%] rounded-2xl px-4 py-2 text-sm leading-relaxed whitespace-pre-wrap break-words ${
                m.role === "user" ? "bg-blue-600 text-white" : "bg-neutral-800"
              }`}
            >
              {m.stock && <StockCard s={m.stock} />}
              {m.text}
              {m.meta && <div className="mt-1 text-[10px] opacity-50">{m.meta}</div>}
            </div>
          </div>
        ))}
        {loading && (
          <div className="flex justify-start">
            <div className="rounded-2xl bg-neutral-800 px-4 py-2 text-sm opacity-70">Neuro is thinking...</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      <div className="flex gap-2 border-t border-white/10 p-3">
        <textarea
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={onKeyDown}
          rows={1}
          placeholder="Ask about a stock (Enter to send)"
          className="flex-1 resize-none rounded-lg bg-neutral-800 px-3 py-2 text-sm outline-none"
        />
        <button
          onClick={send}
          disabled={loading || !input.trim()}
          className="rounded-lg bg-blue-600 px-4 text-sm font-medium text-white disabled:opacity-40"
        >
          Ask
        </button>
      </div>
    </div>
  );
}

export default QuantChatbot;