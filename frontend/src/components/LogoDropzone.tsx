import { useCallback, useRef, useState } from "react";
import "./LogoDropzone.css";

const ACCEPTED = ["image/png", "image/jpeg", "image/webp", "image/svg+xml"];
const MAX_BYTES = 5 * 1024 * 1024;

export default function LogoDropzone({
  previewUrl, onSelect, onClear, error,
}: { previewUrl: string | null; onSelect: (file: File) => void; onClear: () => void; error?: string }) {
  const [isDragging, setIsDragging] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  const handleFile = useCallback((file: File | undefined) => {
    if (!file) return;
    if (!ACCEPTED.includes(file.type)) return;
    if (file.size > MAX_BYTES) return;
    onSelect(file);
  }, [onSelect]);

  return (
    <div>
      <div
        className={`dropzone ${isDragging ? "dropzone--active" : ""} ${previewUrl ? "dropzone--filled" : ""}`}
        onDragOver={(e) => { e.preventDefault(); setIsDragging(true); }}
        onDragLeave={() => setIsDragging(false)}
        onDrop={(e) => {
          e.preventDefault();
          setIsDragging(false);
          handleFile(e.dataTransfer.files[0]);
        }}
        onClick={() => inputRef.current?.click()}
        role="button"
        tabIndex={0}
        onKeyDown={(e) => { if (e.key === "Enter" || e.key === " ") inputRef.current?.click(); }}
      >
        {previewUrl ? (
          <>
            <img src={previewUrl} alt="Logo preview" className="dropzone-image" />
            <button
              type="button"
              className="dropzone-clear"
              onClick={(e) => { e.stopPropagation(); onClear(); }}
            >
              Remove logo
            </button>
          </>
        ) : (
          <div className="dropzone-empty">
            <span className="dropzone-icon">⇧</span>
            <span className="dropzone-title">Drop your logo here, or click to browse</span>
            <span className="dropzone-sub">PNG, JPG, WEBP or SVG — up to 5MB</span>
          </div>
        )}
        <input
          ref={inputRef}
          type="file"
          accept={ACCEPTED.join(",")}
          hidden
          onChange={(e) => handleFile(e.target.files?.[0])}
        />
      </div>
      {error && <span className="field-error">{error}</span>}
    </div>
  );
}
