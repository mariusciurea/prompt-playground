/** Session state for the app: who is signed in, their access, and their quota. */

import { createContext, useCallback, useContext, useEffect, useState } from "react";
import type { ReactNode } from "react";

import { ApiError, api } from "@/api/client";
import type { MeOut, QuotaOut } from "@/api/types";

interface AuthValue {
  me: MeOut | null;
  loading: boolean;
  refresh: () => Promise<void>;
  setQuota: (quota: QuotaOut) => void;
  logout: () => Promise<void>;
}

const AuthContext = createContext<AuthValue | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [me, setMe] = useState<MeOut | null>(null);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    try {
      setMe(await api<MeOut>("/me"));
    } catch (err) {
      // A stale access token is expected; try one silent refresh before giving up.
      if (err instanceof ApiError && err.status === 401) {
        try {
          await api("/auth/refresh", { method: "POST" });
          setMe(await api<MeOut>("/me"));
        } catch {
          setMe(null);
        }
      } else {
        setMe(null);
      }
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    void load();
  }, [load]);

  const value: AuthValue = {
    me,
    loading,
    refresh: load,
    setQuota: (quota) => setMe((current) => (current ? { ...current, quota } : current)),
    logout: async () => {
      await api("/auth/logout", { method: "POST" }).catch(() => undefined);
      setMe(null);
    },
  };
  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthValue {
  const value = useContext(AuthContext);
  if (!value) throw new Error("useAuth must be used within AuthProvider");
  return value;
}
