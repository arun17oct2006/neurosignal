import { useEffect, useRef, useState } from "react";
import { loginWithGoogle } from "@/services/auth";

const CLIENT_ID = (import.meta.env.VITE_GOOGLE_CLIENT_ID as string | undefined) ?? "";
const GIS_SRC = "https://accounts.google.com/gsi/client";

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if ((window as any).google?.accounts?.id) return resolve();
    let script = document.querySelector<HTMLScriptElement>(`script[src="${GIS_SRC}"]`);
    if (!script) {
      script = document.createElement("script");
      script.src = GIS_SRC;
      script.async = true;
      script.defer = true;
      document.head.appendChild(script);
    }
    script.addEventListener("load", () => resolve());
    script.addEventListener("error", () => reject(new Error("Could not load Google sign-in script")));
  });
}

export function SingleSignOn({ onSignedIn }: { onSignedIn?: () => void }) {
  const ref = useRef<HTMLDivElement>(null);
  const callbackRef = useRef(onSignedIn);
  const [error, setError] = useState<string | null>(null);
  const [ready, setReady] = useState(false);

  useEffect(() => {
    callbackRef.current = onSignedIn;
  }, [onSignedIn]);

  useEffect(() => {
    if (!CLIENT_ID) {
      setError("VITE_GOOGLE_CLIENT_ID is missing. Add it to .env, then restart npm run dev.");
      return;
    }

    let cancelled = false;

    loadGoogleScript()
      .then(() => {
        if (cancelled || !ref.current) return;
        const gis = (window as any).google.accounts.id;

        gis.initialize({
          client_id: CLIENT_ID,
          callback: async (resp: { credential: string }) => {
            try {
              setError(null);
              await loginWithGoogle(resp.credential);
              callbackRef.current?.();
            } catch (e) {
              setError(e instanceof Error ? e.message : "Sign-in failed");
            }
          },
        });

        // Clear first so React StrictMode's double effect doesn't draw two buttons
        ref.current.innerHTML = "";
        gis.renderButton(ref.current, {
          theme: "filled_black",
          size: "large",
          text: "signin_with",
          shape: "rectangular",
          width: 280,
        });
        setReady(true);
      })
      .catch((e: Error) => setError(e.message));

    return () => {
      cancelled = true;
    };
  }, []);

  return (
    <div className="flex flex-col items-center gap-3">
      <div ref={ref} className="flex min-h-[44px] justify-center" />
      {!ready && !error && <p className="text-xs text-muted-foreground">Loading Google sign-in...</p>}
      {error && <p className="text-center text-xs text-red-400">{error}</p>}
    </div>
  );
}