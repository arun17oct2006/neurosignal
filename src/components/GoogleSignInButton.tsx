import { useEffect, useRef, useState } from "react";
import { loginWithGoogle } from "@/services/auth";
import type { StoredSession } from "@/services/session";

const GSI_SRC = "https://accounts.google.com/gsi/client";

/** Loads the Google Identity Services script once, then resolves. */
function loadGsi(): Promise<void> {
  if (window.google?.accounts?.id) return Promise.resolve();
  return new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = GSI_SRC;
    script.async = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Could not load Google Sign-In"));
    document.head.appendChild(script);
  });
}

export function GoogleSignInButton({ onSignedIn }: { onSignedIn: (s: StoredSession) => void }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onSignedIn);
  callbackRef.current = onSignedIn;
  const [error, setError] = useState<string | null>(null);
  const clientId = import.meta.env["VITE_GOOGLE_CLIENT_ID"] as string | undefined;

  useEffect(() => {
    if (!clientId) {
      setError("VITE_GOOGLE_CLIENT_ID is not set in .env.local");
      return;
    }
    let cancelled = false;

    loadGsi()
      .then(() => {
        if (cancelled || !containerRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          auto_select: false,
          callback: async ({ credential }) => {
            try {
              const session = await loginWithGoogle(credential);
              callbackRef.current(session);
            } catch (e) {
              setError(e instanceof Error ? e.message : "Sign-in failed");
            }
          },
        });
        window.google.accounts.id.renderButton(containerRef.current, {
          theme: "outline",
          size: "large",
          text: "continue_with",
          shape: "rectangular",
          width: 280,
        });
      })
      .catch((e: unknown) => setError(e instanceof Error ? e.message : "Sign-in unavailable"));

    return () => {
      cancelled = true;
    };
  }, [clientId]);

  return (
    <div className="flex flex-col items-center gap-2">
      <div ref={containerRef} />
      {error && <p className="text-xs text-sell">{error}</p>}
    </div>
  );
}
