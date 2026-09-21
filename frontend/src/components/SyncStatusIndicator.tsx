import { useEffect, useState } from "react";
import { subscribeSyncStatus, processOutbox, getManualOfflineMode, setManualOfflineMode, type SyncStatus } from "../offline/sync";
import "./SyncStatusIndicator.css";

export default function SyncStatusIndicator() {
  const [status, setStatus] = useState<SyncStatus>("online");
  const [pending, setPending] = useState(0);
  const [lastSync, setLastSync] = useState<string | null>(null);
  const [manualOffline, setManualOffline] = useState(getManualOfflineMode());

  useEffect(() => subscribeSyncStatus((s, count, last) => {
    setStatus(s); setPending(count); setLastSync(last);
  }), []);

  const label = status === "syncing" ? "Syncing…" : status === "offline" ? (manualOffline ? "Working offline" : "Offline") : pending > 0 ? `${pending} pending` : "Online";
  const dotClass = status === "offline" ? "sync-dot--offline" : status === "syncing" || pending > 0 ? "sync-dot--syncing" : "sync-dot--online";

  function toggleManualOffline() {
    const next = !manualOffline;
    setManualOffline(next);
    setManualOfflineMode(next);
  }

  return (
    <div className="sync-indicator-group">
      <button
        className="sync-indicator"
        onClick={() => processOutbox()}
        title={lastSync ? `Last synced ${new Date(lastSync).toLocaleTimeString()} — click to sync now` : "Not synced yet — click to try now"}
      >
        <span className={`sync-dot ${dotClass}`} />
        {label}
      </button>
      <button
        className="sync-offline-toggle"
        onClick={toggleManualOffline}
        title={manualOffline ? "You're deliberately working offline — click to reconnect" : "Work offline on purpose, even with a connection — click to control when the app syncs"}
      >
        {manualOffline ? "Go online" : "Work offline"}
      </button>
    </div>
  );
}
