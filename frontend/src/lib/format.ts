export function formatMoney(value: string | number, currency = "NGN"): string {
  const n = typeof value === "string" ? parseFloat(value) : value;
  const symbol = currency === "NGN" ? "₦" : currency === "USD" ? "$" : currency === "GBP" ? "£" : currency === "EUR" ? "€" : `${currency} `;
  return `${symbol}${n.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}`;
}

export function formatDate(iso: string): string {
  return new Date(iso).toLocaleString(undefined, { dateStyle: "medium", timeStyle: "short" });
}

// Turns a backend field name like "selling_price" into "Selling price" —
// so a validation error reads like something a person wrote, not a
// database column name. Used only for the fallback path below; any
// error message that already reads as a full sentence (from `detail`,
// or a plain string) is left exactly as the backend wrote it.
function humanizeFieldName(field: string): string {
  const spaced = field.replace(/_/g, " ");
  return spaced.charAt(0).toUpperCase() + spaced.slice(1);
}

export function extractErrorMessage(err: any, fallback: string): string {
  // No response at all means the request never reached the server —
  // wrong API URL, CORS blocking it, or the backend isn't running.
  // This is a completely different problem from "wrong password" and
  // telling the user to "check your details" here is actively misleading.
  if (!err?.response) {
    if (err?.code === "ECONNABORTED" || err?.message?.includes("timeout")) {
      return "The server took too long to respond. Check your connection and try again.";
    }
    if (err?.code === "ERR_NETWORK" || err?.message === "Network Error") {
      // Deliberately no raw URL here — a business owner has no way to
      // act on a technical address, and it reads like something is
      // more broken than "check your internet connection".
      return "Can't reach Truvanta right now. Check your internet connection and try again.";
    }
    return fallback;
  }
  const data = err.response.data;
  if (!data) return fallback;
  if (typeof data === "string") return data;
  if (data.detail) return data.detail;
  const firstKey = Object.keys(data)[0];
  if (firstKey) {
    const val = data[firstKey];
    const message = Array.isArray(val) ? val[0] : String(val);
    // "non_field_errors" is Django's own catch-all bucket, not a real
    // field a person filled in — showing its literal name would be
    // more confusing than showing no field name at all.
    if (firstKey === "non_field_errors" || firstKey === "__all__") return message;
    return `${humanizeFieldName(firstKey)}: ${message}`;
  }
  return fallback;
}
