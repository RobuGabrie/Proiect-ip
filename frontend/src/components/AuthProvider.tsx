"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState, type ReactNode } from "react";
import { apiFetch, SIGNED_OUT_EVENT, type User } from "@/lib/api";
import { clearToken, getToken } from "@/lib/session";

type AuthState = {
  user: User | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setUser: (user: User) => void;
  signOut: () => void;
};

const AuthContext = createContext<AuthState | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [loading, setLoading] = useState(true);

  const refresh = useCallback(async () => {
    try {
      setUser(getToken() ? await apiFetch<User>("/users/me") : null);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    let active = true;
    const load = async () => {
      if (active) await refresh();
    };
    void load();
    const handleSignedOut = () => setUser(null);
    window.addEventListener(SIGNED_OUT_EVENT, handleSignedOut);
    return () => {
      active = false;
      window.removeEventListener(SIGNED_OUT_EVENT, handleSignedOut);
    };
  }, [refresh]);

  const value = useMemo<AuthState>(
    () => ({
      user,
      loading,
      refresh,
      setUser,
      signOut: () => {
        clearToken();
        setUser(null);
      },
    }),
    [user, loading, refresh],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthState {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth trebuie folosit în interiorul AuthProvider.");
  }
  return context;
}

export function homePath(user: User): string {
  return user.role === "ADMIN" ? "/admin/aprobari" : "/sali";
}
