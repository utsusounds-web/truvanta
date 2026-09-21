import type { ReactNode } from "react";
import "./PageHeader.css";

export default function PageHeader({
  title, subtitle, actions, vaultAccent,
}: { title: ReactNode; subtitle?: string; actions?: ReactNode; vaultAccent?: boolean }) {
  return (
    <div className="page-header">
      <div>
        <h1 className={`display page-title ${vaultAccent ? "page-title--vault" : ""}`}>{title}</h1>
        {subtitle && <p className="page-subtitle">{subtitle}</p>}
      </div>
      {actions && <div className="page-actions">{actions}</div>}
    </div>
  );
}
