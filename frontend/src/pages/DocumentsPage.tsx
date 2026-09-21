import { useEffect, useState } from "react";
import PageHeader from "../components/PageHeader";
import Field from "../components/Field";
import Modal from "../components/Modal";
import EmptyState from "../components/EmptyState";
import { getDocuments, uploadDocument } from "../api/resources";
import type { VaultDocument } from "../api/types";
import { extractErrorMessage, formatDate } from "../lib/format";

const CATEGORIES = [
  { value: "supplier_invoice", label: "Supplier Invoice" },
  { value: "expense_receipt", label: "Expense Receipt" },
  { value: "purchase_document", label: "Purchase Document" },
  { value: "supporting_evidence", label: "Supporting Evidence" },
  { value: "business_document", label: "Business Document" },
  { value: "other", label: "Other" },
];

export default function DocumentsPage() {
  const [documents, setDocuments] = useState<VaultDocument[]>([]);
  const [loading, setLoading] = useState(true);
  const [showUpload, setShowUpload] = useState(false);
  const [title, setTitle] = useState("");
  const [category, setCategory] = useState("other");
  const [note, setNote] = useState("");
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [submitting, setSubmitting] = useState(false);

  function refresh() {
    setLoading(true);
    getDocuments().then(setDocuments).finally(() => setLoading(false));
  }
  useEffect(refresh, []);

  async function handleUpload() {
    if (!title || !file) { setError("Title and a file are required."); return; }
    setSubmitting(true); setError(null);
    try {
      const fd = new FormData();
      fd.append("title", title);
      fd.append("category", category);
      fd.append("note", note);
      fd.append("file", file);
      await uploadDocument(fd);
      setShowUpload(false);
      setTitle(""); setCategory("other"); setNote(""); setFile(null);
      refresh();
    } catch (err: any) {
      setError(extractErrorMessage(err, "Couldn't upload the document."));
    } finally { setSubmitting(false); }
  }

  return (
    <div>
      <PageHeader
        title="Document Vault"
        subtitle="Supplier invoices, expense receipts, and other supporting evidence in one secure place."
        actions={<button className="btn btn-primary" onClick={() => setShowUpload(true)}>Upload document</button>}
      />

      <div className="card">
        {loading ? <div className="loading-row">Loading…</div> : documents.length === 0 ? (
          <div style={{ padding: 24 }}><EmptyState title="No documents yet" /></div>
        ) : (
          <table className="data-table">
            <thead><tr><th>Title</th><th>Category</th><th>Note</th><th>Uploaded</th><th></th></tr></thead>
            <tbody>
              {documents.map((d) => (
                <tr key={d.id}>
                  <td>{d.title}</td>
                  <td style={{ textTransform: "capitalize" }}>{d.category.replace(/_/g, " ")}</td>
                  <td>{d.note || "—"}</td>
                  <td>{formatDate(d.created_at)}</td>
                  <td><a className="btn btn-ghost" href={d.file} target="_blank" rel="noreferrer">Open</a></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {showUpload && (
        <Modal title="Upload document" onClose={() => setShowUpload(false)}>
          <Field label="Title" required><input className="input" value={title} onChange={(e) => setTitle(e.target.value)} /></Field>
          <Field label="Category">
            <select className="input" value={category} onChange={(e) => setCategory(e.target.value)}>
              {CATEGORIES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
          </Field>
          <Field label="Note"><input className="input" value={note} onChange={(e) => setNote(e.target.value)} /></Field>
          <Field label="File" required>
            <input className="input" type="file" onChange={(e) => setFile(e.target.files?.[0] || null)} />
          </Field>
          {error && <p className="inline-error">{error}</p>}
          <button className="btn btn-primary" style={{ width: "100%" }} onClick={handleUpload} disabled={submitting}>
            {submitting ? "Uploading…" : "Upload"}
          </button>
        </Modal>
      )}
    </div>
  );
}
