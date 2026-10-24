import { useEffect, useRef, useState } from "react";
import { Link, useNavigate } from "@tanstack/react-router";
import { getSession } from "@/services/session";
import { signOut } from "@/services/auth";
import type { StoredSession } from "@/services/session";

export function UserMenu() {
  const [open, setOpen] = useState(false);
  const [session, setSession] = useState<StoredSession | null>(null);
  const ref = useRef<HTMLDivElement>(null);
  const navigate = useNavigate();

  // Read the session after mount so server and browser render the same HTML.
  useEffect(() => {
    setSession(getSession());
  }, []);

  useEffect(() => {
    const close = (e: MouseEvent) => {
      if (!ref.current?.contains(e.target as Node)) setOpen(false);
    };
    document.addEventListener("mousedown", close);
    return () => document.removeEventListener("mousedown", close);
  }, []);

  const handleSignOut = async () => {
    await signOut();
    setSession(null);
    setOpen(false);
    navigate({ to: "/" });
  };

  return (
    <div ref={ref} className="relative">
      <button
        onClick={() => setOpen((o) => !o)}
        aria-label="Account menu"
        className="flex h-8 w-8 items-center justify-center overflow-hidden rounded-full border bg-card text-muted-foreground transition hover:border-control hover:text-foreground"
      >
        {session?.picture ? (
          <img src={session.picture} alt="" className="h-full w-full object-cover" referrerPolicy="no-referrer" />
        ) : (
          <svg viewBox="0 0 24 24" className="h-4 w-4" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="8" r="4" />
            <path d="M4 20c1.5-3.5 4.5-5 8-5s6.5 1.5 8 5" />
          </svg>
        )}
      </button>

      {open && (
        <div className="panel absolute right-0 top-11 z-50 w-56 overflow-hidden py-1 text-sm">
          {session ? (
            <>
              <div className="border-b px-4 py-2.5">
                <p className="truncate font-medium">{session.name || "Signed in"}</p>
                <p className="truncate text-[11px] text-muted-foreground">{session.email}</p>
              </div>
              <button
                onClick={handleSignOut}
                className="block w-full px-4 py-2.5 text-left text-sell transition hover:bg-accent"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
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
            </>
          )}
        </div>
      )}
    </div>
  );
}