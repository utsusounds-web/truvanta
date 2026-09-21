import { useEffect, useState } from "react";
import { getPlatformBranding } from "../api/tenants";
import { isOutdated } from "../lib/appVersion";

export default function VersionGate({ children }: { children: React.ReactNode }) {
  const [blocked, setBlocked] = useState(false);

  useEffect(() => {
    getPlatformBranding()
      .then(({ minimum_client_version }) => setBlocked(isOutdated(minimum_client_version)))
      .catch(() => {}); // no network yet / fresh install — never block on a failed check
  }, []);

  if (blocked) {
    return (
      <div style={{
        position: "fixed", inset: 0, background: "var(--ink-900)", color: "var(--paper-0)",
        display: "flex", flexDirection: "column", alignItems: "center", justifyContent: "center",
        gap: 16, zIndex: 9999, textAlign: "center", padding: 24,
      }}>
        <h2 style={{ fontFamily: "var(--font-display)", margin: 0 }}>A required update is ready</h2>
        <p style={{ maxWidth: 380, opacity: 0.85, fontSize: 16 }}>
          This includes an important fix. Please refresh to continue — your work up to this point is safe.
        </p>
        <button className="btn btn-primary" onClick={() => window.location.reload()}>
          Refresh now
        </button>
      </div>
    );
  }

  return <>{children}</>;
}
