import { getPlatformBranding } from "../api/tenants";

export const DEFAULT_THEME_COLOR = "#E3A635";

// Set once fetched, read by BusinessContext as the fallback for any
// business that hasn't picked its own branding color — so "no custom
// color yet" means "inherit the admin's universal default", not a
// hardcoded brand gold that ignores whatever the admin configured.
let cachedUniversalColor: string = DEFAULT_THEME_COLOR;
export function getCachedUniversalColor(): string {
  return cachedUniversalColor;
}

// A simple, dependency-free darken — used to derive the "pressed/hover"
// shade from whatever accent color is active, the same way --gold-600
// relates to --gold-500 in the default palette.
export function darkenHex(hex: string, amount: number): string {
  const m = /^#([0-9a-f]{6})$/i.exec(hex);
  if (!m) return hex;
  const num = parseInt(m[1], 16);
  const channel = (shift: number) => Math.max(0, Math.round(((num >> shift) & 0xff) * (1 - amount)));
  const r = channel(16), g = channel(8), b = channel(0);
  return `#${((1 << 24) + (r << 16) + (g << 8) + b).toString(16).slice(1)}`;
}

export function applyAccentColor(hex: string) {
  const color = /^#[0-9a-f]{6}$/i.test(hex) ? hex : DEFAULT_THEME_COLOR;
  document.documentElement.style.setProperty("--gold-500", color);
  document.documentElement.style.setProperty("--gold-600", darkenHex(color, 0.15));
}

// Called once at app boot (see main.tsx) — applies immediately so the
// login screen itself reflects it, before any business is loaded.
export async function initUniversalColor() {
  try {
    const { universal_color } = await getPlatformBranding();
    if (universal_color) {
      cachedUniversalColor = universal_color;
      applyAccentColor(universal_color);
    }
  } catch {
    // No network yet, or a fresh install with no PlatformSettings —
    // the hardcoded default already applied via CSS, nothing to do.
  }
}
