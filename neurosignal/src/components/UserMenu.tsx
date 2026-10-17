import { useEffect, useRef, useState } from "react";
import { Link } from "@tanstack/react-router";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const ref = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Account menu"
        className="flex h-8 w-8 items-center justify-center rounded-full border bg-card text-muted-foreground transition hover:border-control hover:text-foreground"
      >
        <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
          <circle cx="12" cy="8" r="4" />
          <path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5" />
        </svg>
      </button>

      {open && (
        <div className="panel absolute right-0 top-11 z-50 w-52 overflow-hidden py-1 text-sm">
          <p className="border-b px-4 py-2.5 text-[11px] uppercase tracking-wider text-muted-foreground">
            Guest workspace
          </p>
          <button
            onClick={() => setOpen(false)}
            className="block w-full px-4 py-2.5 text-left transition hover:bg-accent"
          >
            My dashboards
            <span className="mt-0.5 block text-[11px] text-muted-foreground">
              Sign in to save and sync workspaces
            </span>
          </button>
          <Link
            to="/"
            onClick={() => setOpen(false)}
            className="block border-t px-4 py-2.5 text-control transition hover:bg-accent"
          >
            ← Back to sign in
          </Link>
        </div>
      )}
    </div>
  );
}
