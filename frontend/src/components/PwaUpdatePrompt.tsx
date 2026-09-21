import { useEffect, useState } from "react";
import { registerSW } from "virtual:pwa-register";
import "./PwaUpdatePrompt.css";

/** Shows a small banner when a new version is available (the service
 * worker downloaded an update in the background) — refreshing applies
 * it. Without this, a person could keep using a stale cached version
 * indefinitely after closing and reopening the app. */
export default function PwaUpdatePrompt() {
  const [needsRefresh, setNeedsRefresh] = useState(false);
  const [updateFn, setUpdateFn] = useState<((reloadPage?: boolean) => Promise<void>) | null>(null);

  useEffect(() => {
    const update = registerSW({
      onNeedRefresh() {
        setNeedsRefresh(true);
      },
      onOfflineReady() {
        // App shell is now cached and available offline — no UI needed for this,
        // it's just a nice-to-have confirmation for anyone watching devtools.
      },
    });
    setUpdateFn(() => update);
  }, []);

  if (!needsRefresh) return null;

  return (
    <div className="pwa-update-banner">
      <span>A new version of Truvanta is available.</span>
      <button className="btn btn-primary" onClick={() => updateFn?.(true)}>
        Refresh
      </button>
    </div>
  );
}
