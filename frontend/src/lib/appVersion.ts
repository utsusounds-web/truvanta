// Bump this on every deploy that includes a change important enough to
// force everyone onto it immediately (e.g. a fix to ledger math) —
// paired with raising Admin → Universal colour card's "Minimum client
// version" field to the same value. Most releases don't need either.
export const APP_VERSION = "1.0.0";

// Simple semver-ish comparator: 0 if equal, negative if a < b, positive
// if a > b. Missing/non-numeric segments count as 0, so "1.2" == "1.2.0".
export function compareVersions(a: string, b: string): number {
  const pa = a.split(".").map((n) => parseInt(n, 10) || 0);
  const pb = b.split(".").map((n) => parseInt(n, 10) || 0);
  const len = Math.max(pa.length, pb.length);
  for (let i = 0; i < len; i++) {
    const diff = (pa[i] || 0) - (pb[i] || 0);
    if (diff !== 0) return diff;
  }
  return 0;
}

export function isOutdated(minimumVersion: string): boolean {
  if (!minimumVersion) return false;
  return compareVersions(APP_VERSION, minimumVersion) < 0;
}
