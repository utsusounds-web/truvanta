import { useEffect, useRef, useState } from "react";

// Google's own recommended integration is a script tag + global
// `google.accounts.id`, not an npm package — this avoids adding a new
// dependency just for one button. Minimal ambient typing below rather
// than pulling in @types/google.accounts for the same reason.
declare global {
  interface Window {
    google?: {
      accounts: {
        id: {
          initialize: (config: { client_id: string; callback: (response: { credential: string }) => void }) => void;
          renderButton: (element: HTMLElement, options: Record<string, unknown>) => void;
        };
      };
    };
  }
}

const SCRIPT_SRC = "https://accounts.google.com/gsi/client";

function loadGoogleScript(): Promise<void> {
  return new Promise((resolve, reject) => {
    if (window.google?.accounts?.id) { resolve(); return; }
    const existing = document.querySelector(`script[src="${SCRIPT_SRC}"]`);
    if (existing) {
      existing.addEventListener("load", () => resolve());
      existing.addEventListener("error", () => reject(new Error("Failed to load Google Sign-In script.")));
      return;
    }
    const script = document.createElement("script");
    script.src = SCRIPT_SRC;
    script.async = true;
    script.defer = true;
    script.onload = () => resolve();
    script.onerror = () => reject(new Error("Failed to load Google Sign-In script."));
    document.head.appendChild(script);
  });
}

interface GoogleSignInButtonProps {
  clientId: string;
  onToken: (idToken: string) => void;
}

export default function GoogleSignInButton({ clientId, onToken }: GoogleSignInButtonProps) {
  const buttonRef = useRef<HTMLDivElement>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;
    loadGoogleScript()
      .then(() => {
        if (cancelled || !buttonRef.current || !window.google) return;
        window.google.accounts.id.initialize({
          client_id: clientId,
          callback: (response) => onToken(response.credential),
        });
        window.google.accounts.id.renderButton(buttonRef.current, {
          type: "standard", theme: "outline", size: "large", width: 320, text: "continue_with",
        });
      })
      .catch(() => { if (!cancelled) setFailed(true); });
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [clientId]);

  if (failed) {
    // Fails closed and quietly — email/password sign-in right below
    // this still works either way, so a Google outage or a network
    // that blocks Google's script never blocks sign-in entirely.
    return null;
  }

  return <div ref={buttonRef} style={{ display: "flex", justifyContent: "center" }} />;
}
