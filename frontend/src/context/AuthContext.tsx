import { createContext, useContext, useState, useCallback, type ReactNode } from "react";
import client from "../api/client";

export interface Membership {
  id: string;
  business: string;
  branch: string | null;
  role: string;
  role_name: string;
  role_system_role: string;
  permission_codes: string[];
}

export interface CurrentUser {
  id: string;
  email: string;
  first_name: string;
  last_name: string;
  is_staff: boolean;
  profile_photo: string | null;
  two_factor_enabled: boolean;
}

export type LoginResult =
  | { requires2FA: true; preAuthToken: string }
  | { requires2FA: false; memberships: Membership[]; isStaff: boolean };

interface AuthContextValue {
  user: CurrentUser | null;
  memberships: Membership[];
  isAuthenticated: boolean;
  login: (email: string, password: string) => Promise<LoginResult>;
  loginWithGoogle: (idToken: string) => Promise<LoginResult>;
  verifyTwoFactorLogin: (preAuthToken: string, code: string) => Promise<{ memberships: Membership[]; isStaff: boolean }>;
  register: (data: { email: string; username: string; password: string; first_name?: string; last_name?: string }) => Promise<void>;
  loadMe: () => Promise<{ memberships: Membership[]; isStaff: boolean }>;
  logout: () => void;
  setActiveBusiness: (businessId: string) => void;
  updateProfile: (data: FormData) => Promise<void>;
  hasPermission: (code: string) => boolean;
  isOwnerOrAdmin: () => boolean;
  meLoading: boolean;
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<CurrentUser | null>(null);
  const [memberships, setMemberships] = useState<Membership[]>([]);
  // Starts true whenever a token is already sitting in storage, since
  // App.tsx is about to spend a network round-trip confirming it —
  // lets the app show a loading screen instead of a flash of stale UI.
  const [meLoading, setMeLoading] = useState(() => !!localStorage.getItem("sbos_access_token"));

  const loadMe = useCallback(async () => {
    try {
      const res = await client.get("/auth/me/");
      setUser(res.data.user);
      setMemberships(res.data.memberships);
      return { memberships: res.data.memberships as Membership[], isStaff: !!res.data.user?.is_staff };
    } finally {
      setMeLoading(false);
    }
  }, []);

  // Shared by a normal login and the 2FA verify step — stores tokens,
  // loads the user, and restores which business this account belongs to.
  const _finishLogin = useCallback(async (access: string, refresh: string, sessionId?: string) => {
    localStorage.setItem("sbos_access_token", access);
    localStorage.setItem("sbos_refresh_token", refresh);
    if (sessionId) localStorage.setItem("sbos_session_id", sessionId);
    const { memberships: fetchedMemberships, isStaff } = await loadMe();
    // Restore which business this account belongs to. Without this, a
    // returning user with no sbos_business_id in localStorage (a new
    // device, or one cleared on a previous logout) looked like they had
    // no business at all, and got sent through onboarding again —
    // creating a second, empty business instead of reopening their real one.
    const storedBusinessId = localStorage.getItem("sbos_business_id");
    const stillValid = storedBusinessId && fetchedMemberships.some((m) => m.business === storedBusinessId);
    if (!stillValid && fetchedMemberships.length > 0) {
      localStorage.setItem("sbos_business_id", fetchedMemberships[0].business);
    }
    return { memberships: fetchedMemberships, isStaff };
  }, [loadMe]);

  const login = useCallback(async (email: string, password: string): Promise<LoginResult> => {
    const res = await client.post("/auth/login/", { email, password });
    if (res.data.requires_2fa) {
      return { requires2FA: true, preAuthToken: res.data.pre_auth_token };
    }
    const { memberships, isStaff } = await _finishLogin(res.data.access, res.data.refresh, res.data.session_id);
    return { requires2FA: false, memberships, isStaff };
  }, [_finishLogin]);

  const loginWithGoogle = useCallback(async (idToken: string): Promise<LoginResult> => {
    const res = await client.post("/auth/login/google/", { id_token: idToken });
    if (res.data.requires_2fa) {
      return { requires2FA: true, preAuthToken: res.data.pre_auth_token };
    }
    const { memberships, isStaff } = await _finishLogin(res.data.access, res.data.refresh, res.data.session_id);
    return { requires2FA: false, memberships, isStaff };
  }, [_finishLogin]);

  const verifyTwoFactorLogin = useCallback(async (preAuthToken: string, code: string) => {
    const res = await client.post("/auth/login/verify-2fa/", { pre_auth_token: preAuthToken, code });
    return _finishLogin(res.data.access, res.data.refresh, res.data.session_id);
  }, [_finishLogin]);

  const register = useCallback(async (data: { email: string; username: string; password: string; first_name?: string; last_name?: string }) => {
    await client.post("/auth/register/", data);
    await login(data.email, data.password);
  }, [login]);

  const logout = useCallback(() => {
    const refresh = localStorage.getItem("sbos_refresh_token");
    // Best-effort — blacklists the refresh token server-side so it can't
    // be replayed. Local state is cleared regardless of whether this
    // succeeds, so a flaky connection never traps someone mid-logout.
    if (refresh) {
      client.post("/auth/logout/", { refresh }).catch(() => {});
    }
    localStorage.removeItem("sbos_access_token");
    localStorage.removeItem("sbos_refresh_token");
    localStorage.removeItem("sbos_session_id");
    localStorage.removeItem("sbos_business_id");
    setUser(null);
    setMemberships([]);
  }, []);

  const setActiveBusiness = useCallback((businessId: string) => {
    localStorage.setItem("sbos_business_id", businessId);
  }, []);

  const updateProfile = useCallback(async (data: FormData) => {
    const res = await client.patch("/auth/me/", data);
    setUser(res.data);
  }, []);

  // Checks the permission_codes on whichever membership matches the
  // currently active business (localStorage sbos_business_id). Used
  // to hide/disable actions the backend would 403 anyway — this is a
  // UX convenience, not the actual security boundary; that's always
  // enforced server-side regardless of what this returns.
  const hasPermission = useCallback((code: string) => {
    const activeBusinessId = localStorage.getItem("sbos_business_id");
    const membership = memberships.find((m) => m.business === activeBusinessId);
    if (!membership) return false;
    return membership.permission_codes?.includes(code) ?? false;
  }, [memberships]);

  // Mirrors the backend's IsOwnerOrAdmin: owner/admin role, or a
  // membership with no branch restriction (full access). Used to hide
  // owner-level-only sections (like the audit/activity log) the same
  // way hasPermission hides permission-gated ones — a UX convenience,
  // not the security boundary.
  const isOwnerOrAdmin = useCallback(() => {
    const activeBusinessId = localStorage.getItem("sbos_business_id");
    const membership = memberships.find((m) => m.business === activeBusinessId);
    if (!membership) return false;
    // Deliberately NOT `|| membership.branch === null` — that field
    // means "this membership can see every branch's data", not "is
    // owner/admin". Those are different things: a branch-unrestricted
    // staff member on a narrow custom role should never gain
    // owner-level actions just because they aren't tied to one branch.
    return membership.role_system_role === "owner" || membership.role_system_role === "admin";
  }, [memberships]);

  const value: AuthContextValue = {
    user,
    memberships,
    isAuthenticated: !!user,
    login,
    loginWithGoogle,
    verifyTwoFactorLogin,
    register,
    loadMe,
    logout,
    setActiveBusiness,
    updateProfile,
    hasPermission,
    isOwnerOrAdmin,
    meLoading,
  };

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error("useAuth must be used within AuthProvider");
  return ctx;
}
