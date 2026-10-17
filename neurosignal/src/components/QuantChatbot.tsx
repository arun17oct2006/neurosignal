import { useEffect, useRef, useState } from "react";
import { streamChat } from "@/services/api";
import type { ChatMessage, ChatSummaryContext } from "@/types/market";

export function QuantChatbot({ context }: { context: ChatSummaryContext | undefined }) {
  const [open, setOpen] = useState(false);
  const [msgs, setMsgs] = useState<ChatMessage[]>([]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const abort = useRef<AbortController | null>(null);
  const end = useRef<HTMLDivElement>(null);

  useEffect(() => end.current?.scrollIntoView({ behavior: "smooth" }), [msgs]);

  const send = async () => {
    if (!text.trim() || !context || busy) return;
    setError(null);
    const now = new Date().toISOString();
    const aid = crypto.randomUUID();
    setMsgs((m) => [
      ...m,
      { id: crypto.randomUUID(), sender: "user", content: text, timestamp: now },
      { id: aid, sender: "assistant", content: "", timestamp: now },
    ]);
    const q = text;
    setText("");
    setBusy(true);
    abort.current = new AbortController();
    try {
      await streamChat(q, context, (tok) =>
        setMsgs((m) => m.map((x) => (x.id === aid ? { ...x, content: x.content + tok } : x))),
        abort.current.signal,
      );
    } catch (e) {
      setError(e instanceof Error ? e.message : "Chat failed");
    } finally {
      setBusy(false);
    }
  };

  return (
    <>
      <button
        onClick={() => setOpen((o) => !o)}
        className="fixed bottom-6 right-6 z-40 rounded-md border bg-primary px-4 py-2.5 text-primary-foreground hover:opacity-90 font-display text-sm font-semibold"
      >
        {open ? "Close" : "Ask Neuro"}
      </button>
      {open && (
        <aside className="panel fixed bottom-24 right-6 z-40 flex h-[520px] w-[min(380px,calc(100vw-3rem))] flex-col shadow-2xl">
          <header className="border-b px-4 py-3">
            <h3 className="text-sm font-semibold">Quant Assistant</h3>
            {context && (
              <p className="metric text-[10px] text-muted-foreground">
                ctx: {context.ticker} · RSI {context.rsi.toFixed(1)} · {context.signal} · ${context.target.toFixed(2)}
              </p>
            )}
          </header>
          <div className="flex-1 space-y-3 overflow-y-auto p-4 text-sm">
            {msgs.length === 0 && (
              <p className="text-xs text-muted-foreground">
                Ask about the current signal. Only summary metrics are sent to keep it lightweight.
              </p>
            )}
            {msgs.map((m) => (
              <div
                key={m.id}
                className={`max-w-[85%] rounded-lg px-3 py-2 ${
                  m.sender === "user" ? "ml-auto bg-control/15 text-foreground" : "bg-muted"
                }`}
              >
                {m.content || <span className="animate-pulse text-muted-foreground">▍</span>}
              </div>
            ))}
            {error && <p className="rounded-md border border-sell/50 bg-sell/10 px-3 py-2 text-xs text-sell">{error}</p>}
            <div ref={end} />
          </div>
          <form
            onSubmit={(e) => { e.preventDefault(); send(); }}
            className="flex gap-2 border-t p-3"
          >
            <input
              value={text}
              onChange={(e) => setText(e.target.value)}
              disabled={!context}
              placeholder={context ? "Is this a good entry?" : "Load a ticker first"}
              className="flex-1 rounded-md border bg-background px-3 py-2 text-sm outline-none focus:border-control"
            />
            <button disabled={busy || !context} className="rounded-md bg-control px-3 text-sm font-semibold text-primary-foreground disabled:opacity-40">
              Send
            </button>
          </form>
        </aside>
      )}
    </>
  );
}
