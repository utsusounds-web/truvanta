import { useEffect, useRef, useState } from "react";
import { useNavigate } from "react-router-dom";
import { globalSearch } from "../api/resources";
import type { SearchResult } from "../api/types";

const TYPE_LABELS: Record<SearchResult["type"], string> = {
  product: "Product",
  customer: "Customer",
  supplier: "Supplier",
  sale: "Sale",
};

export default function GlobalSearch() {
  const navigate = useNavigate();
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [loading, setLoading] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (query.trim().length < 2) {
      setResults([]);
      setOpen(false);
      return;
    }
    // Debounced: waits for a pause in typing rather than firing a
    // request on every keystroke — a business with a large catalogue
    // is exactly the case this needs to stay responsive for.
    const handle = setTimeout(() => {
      setLoading(true);
      globalSearch(query.trim())
        .then((r) => { setResults(r); setOpen(true); })
        .catch(() => { setResults([]); })
        .finally(() => setLoading(false));
    }, 250);
    return () => clearTimeout(handle);
  }, [query]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  function handleSelect(result: SearchResult) {
    setOpen(false);
    setQuery("");
    navigate(result.path);
  }

  return (
    <div ref={containerRef} style={{ position: "relative", width: 320, maxWidth: "40vw" }}>
      <input
        className="input"
        placeholder="Search products, customers, suppliers, sales…"
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onFocus={() => { if (results.length > 0) setOpen(true); }}
        style={{ width: "100%" }}
      />
      {open && (
        <div
          className="card"
          style={{
            position: "absolute", top: "calc(100% + 4px)", left: 0, right: 0,
            zIndex: 50, maxHeight: 340, overflowY: "auto", padding: 4,
          }}
        >
          {loading ? (
            <div style={{ padding: 12, fontSize: 15, color: "var(--ink-300)" }}>Searching…</div>
          ) : results.length === 0 ? (
            <div style={{ padding: 12, fontSize: 15, color: "var(--ink-300)" }}>No matches for "{query}"</div>
          ) : (
            results.map((r) => (
              <button
                key={`${r.type}-${r.id}`}
                onClick={() => handleSelect(r)}
                style={{
                  display: "flex", justifyContent: "space-between", alignItems: "center",
                  width: "100%", textAlign: "left", padding: "10px 12px", background: "none",
                  border: "none", cursor: "pointer", borderRadius: 8, fontSize: 15.5,
                }}
                onMouseDown={(e) => e.preventDefault()}
              >
                <span>
                  <span style={{ fontWeight: 600 }}>{r.label}</span>
                  {r.sublabel && <span style={{ color: "var(--ink-300)", marginLeft: 6 }}>{r.sublabel}</span>}
                </span>
                <span className="badge badge--neutral" style={{ fontSize: 13 }}>{TYPE_LABELS[r.type]}</span>
              </button>
            ))
          )}
        </div>
      )}
    </div>
  );
}
