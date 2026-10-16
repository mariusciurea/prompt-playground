/** Route guards. UI gating only — the server enforces the real rules. */

import { Navigate } from "react-router-dom";
import type { ReactNode } from "react";

import { useAuth } from "@/auth/AuthContext";
import { Spinner } from "@/components/ui";

export function RequireAuth({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!me) return <Navigate to="/login" replace />;
  return <>{children}</>;
}

export function RequireAccess({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!me) return <Navigate to="/login" replace />;
  if (!me.access.has_access) return <Navigate to="/" replace />;
  return <>{children}</>;
}

export function RequireStaff({ children }: { children: ReactNode }) {
  const { me, loading } = useAuth();
  if (loading) return <Spinner />;
  if (!me) return <Navigate to="/login" replace />;
  if (me.user.role !== "admin" && me.user.role !== "instructor")
    return <Navigate to="/" replace />;
  return <>{children}</>;
}
