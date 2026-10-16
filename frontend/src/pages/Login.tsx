import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { ApiError, api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { ErrorBanner, Field } from "@/components/ui";
import { AuthLayout, BotCheck } from "@/pages/authLayout";

export function Login() {
  const navigate = useNavigate();
  const { refresh } = useAuth();
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [totp, setTotp] = useState("");
  const [needsTotp, setNeedsTotp] = useState(false);
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/login", {
        method: "POST",
        body: {
          email,
          password,
          turnstile_token: token,
          totp_code: needsTotp ? totp : null,
        },
      });
      await refresh();
      navigate("/");
    } catch (err) {
      if (err instanceof ApiError && err.code === "totp_required") {
        setNeedsTotp(true);
      } else {
        setError(err);
      }
    } finally {
      setBusy(false);
    }
  }

  return (
    <AuthLayout title="Sign in">
      <form onSubmit={submit}>
        <Field label="E-mail" htmlFor="email">
          <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="password">
          <input id="password" className="input" type="password" autoComplete="current-password" required value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        {needsTotp && (
          <Field label="Authenticator code" hint="6-digit code from your app">
            <input className="input" inputMode="numeric" pattern="\d{6}" value={totp} onChange={(e) => setTotp(e.target.value)} />
          </Field>
        )}
        <BotCheck onToken={setToken} />
        <ErrorBanner error={error} />
        <button className="btn-primary mt-3 w-full" disabled={busy}>
          {busy ? "Signing in…" : "Sign in"}
        </button>
      </form>
      <div className="mt-4 flex justify-between text-sm text-muted">
        <Link to="/register" className="hover:text-fg">
          Create account
        </Link>
        <Link to="/forgot-password" className="hover:text-fg">
          Forgot password?
        </Link>
      </div>
    </AuthLayout>
  );
}
