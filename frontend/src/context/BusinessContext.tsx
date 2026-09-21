import { createContext, useContext, useState, useCallback, useEffect, type ReactNode } from "react";
import { getBranches } from "../api/resources";
import { getBusiness } from "../api/tenants";
import type { Branch } from "../api/types";
import { useAuth } from "./AuthContext";
import { refreshOfflineCache } from "../offline/sync";
import { applyAccentColor, getCachedUniversalColor } from "../lib/accentColor";

interface BusinessContextValue {
  branches: Branch[];
  activeBranchId: string | null;
  setActiveBranchId: (id: string) => void;
  activeBranch: Branch | null;
  loading: boolean;
  refresh: () => Promise<void>;
  businessName: string | null;
  businessLogoUrl: string | null;
  businessThemeColor: string;
  profileLoading: boolean;
  refreshBusinessProfile: () => Promise<void>;
}

const BusinessContext = createContext<BusinessContextValue | undefined>(undefined);

export function BusinessProvider({ children }: { children: ReactNode }) {
  const { isAuthenticated, memberships } = useAuth();
  const [branches, setBranches] = useState<Branch[]>([]);
  const [activeBranchId, setActiveBranchIdState] = useState<string | null>(
    localStorage.getItem("sbos_branch_id")
  );
  const [loading, setLoading] = useState(false);
  const [businessName, setBusinessName] = useState<string | null>(null);
  const [businessLogoUrl, setBusinessLogoUrl] = useState<string | null>(null);
  const [businessThemeColor, setBusinessThemeColor] = useState<string>(getCachedUniversalColor());
  const [profileLoading, setProfileLoading] = useState(false);

  const refresh = useCallback(async () => {
    const businessId = localStorage.getItem("sbos_business_id");
    if (!businessId) return;
    setLoading(true);
    try {
      const data = await getBranches();
      setBranches(data);
      const stored = localStorage.getItem("sbos_branch_id");
      const stillValid = stored && data.some((b) => b.id === stored);
      if (!stillValid && data.length > 0) {
        // The real distinction isn't "which branch is oldest" — it's
        // "does MY OWN membership actually specify one". A staff
        // member scoped to a specific branch should always land
        // there. An owner/admin (or anyone with a branch-unrestricted
        // membership) has no single "right" branch, so — and only
        // then — earliest-created is used as a reasonable starting
        // view, not as a stand-in for "their" branch.
        const myMembership = memberships.find((m) => m.business === businessId);
        const assigned = myMembership?.branch && data.some((b) => b.id === myMembership.branch)
          ? data.find((b) => b.id === myMembership.branch)
          : null;
        const fallback = assigned || [...data].sort(
          (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime()
        )[0];
        setActiveBranchIdState(fallback.id);
        localStorage.setItem("sbos_branch_id", fallback.id);
      }
      refreshOfflineCache();
    } finally {
      setLoading(false);
    }
  }, []);

  // Name + logo for the sidebar mark and the branded loading screen —
  // kept in context (rather than each page fetching it separately) so
  // a logo saved in Settings updates everywhere immediately.
  const refreshBusinessProfile = useCallback(async () => {
    const businessId = localStorage.getItem("sbos_business_id");
    if (!businessId) return;
    setProfileLoading(true);
    try {
      const b = await getBusiness(businessId);
      setBusinessName(b.name);
      setBusinessLogoUrl(b.logo_url);
      // A business with no color of its own inherits the admin's
      // universal default, not a hardcoded brand gold.
      const color = b.theme_color || getCachedUniversalColor();
      setBusinessThemeColor(color);
      applyAccentColor(color);
    } finally {
      setProfileLoading(false);
    }
  }, []);

  useEffect(() => {
    if (isAuthenticated) {
      refresh();
      refreshBusinessProfile();
    } else {
      setBusinessName(null);
      setBusinessLogoUrl(null);
      setBusinessThemeColor(getCachedUniversalColor());
      applyAccentColor(getCachedUniversalColor());
    }
  }, [isAuthenticated, refresh, refreshBusinessProfile]);

  const setActiveBranchId = useCallback((id: string) => {
    localStorage.setItem("sbos_branch_id", id);
    setActiveBranchIdState(id);
  }, []);

  const activeBranch = branches.find((b) => b.id === activeBranchId) || null;

  return (
    <BusinessContext.Provider
      value={{
        branches, activeBranchId, setActiveBranchId, activeBranch, loading, refresh,
        businessName, businessLogoUrl, businessThemeColor, profileLoading, refreshBusinessProfile,
      }}
    >
      {children}
    </BusinessContext.Provider>
  );
}

export function useBusiness() {
  const ctx = useContext(BusinessContext);
  if (!ctx) throw new Error("useBusiness must be used within BusinessProvider");
  return ctx;
}
