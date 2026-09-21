import type { ReactNode } from "react";
import "./Modal.css";

export default function Modal({
  title, onClose, children, width = 480,
}: { title: string; onClose: () => void; children: ReactNode; width?: number }) {
  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal-panel" style={{ maxWidth: width }} onClick={(e) => e.stopPropagation()}>
        <div className="modal-header">
          <h2 className="display modal-title">{title}</h2>
          <button className="modal-close" onClick={onClose} aria-label="Close">✕</button>
        </div>
        <div className="modal-body">{children}</div>
      </div>
    </div>
  );
}
