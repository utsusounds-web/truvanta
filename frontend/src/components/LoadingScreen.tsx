import "./LoadingScreen.css";

interface LoadingScreenProps {
  /** Business logo to show, once known. Falls back to the Truvanta mark. */
  logoUrl?: string | null;
  /** Small line under the spinner, e.g. "Loading your business…" */
  label?: string;
}

// Full-page loading state shown whenever the app doesn't yet have
// enough to render real content — initial auth check, first business
// load after login, etc. Shows the business's own logo once it's
// known so the app feels branded even while waiting, not just blank.
export default function LoadingScreen({ logoUrl, label }: LoadingScreenProps) {
  return (
    <div className="loading-screen">
      <div className="loading-screen-mark">
        {logoUrl ? (
          <img src={logoUrl} alt="" className="loading-screen-logo" />
        ) : (
          <svg viewBox="0 0 32 32" className="loading-screen-logo loading-screen-logo--default">
            <rect width="32" height="32" rx="7" fill="#10263B" />
            <path d="M9 20.5 L14 11 L18 17 L23 9" stroke="#E3A635" strokeWidth="2.4" fill="none" strokeLinecap="round" strokeLinejoin="round" />
          </svg>
        )}
        <span className="loading-screen-spinner" aria-hidden="true" />
      </div>
      <p className="loading-screen-label">{label || "Loading…"}</p>
    </div>
  );
}
