import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import { api } from "@/api/client";
import { ErrorBanner, Field } from "@/components/ui";
import { AuthLayout, BotCheck } from "@/pages/authLayout";

export function ForgotPassword() {
  const [email, setEmail] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/auth/forgot-password", {
        method: "POST",
        body: { email, turnstile_token: token },
      });
      setDone(true);
    } catch (err) {
      setError(err);
    }
  }

  return (
    <AuthLayout title="Reset password">
      {done ? (
        <p className="text-sm text-muted">
          If the address has an account, we&apos;ve sent a reset link. Check your inbox.
        </p>
      ) : (
        <form onSubmit={submit}>
          <Field label="E-mail" htmlFor="email">
            <input id="email" className="input" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          </Field>
          <BotCheck onToken={setToken} />
          <ErrorBanner error={error} />
          <button className="btn-primary mt-3 w-full">Send reset link</button>
        </form>
      )}
      <Link to="/login" className="mt-4 block text-sm text-muted hover:text-fg">
        Back to sign in
      </Link>
    </AuthLayout>
  );
}

export function ResetPassword() {
  const navigate = useNavigate();
  const [password, setPassword] = useState("");
  const [error, setError] = useState<unknown>(null);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    const token = new URLSearchParams(window.location.hash.slice(1)).get("token");
    try {
      await api("/auth/reset-password", {
        method: "POST",
        body: { token, new_password: password },
      });
      navigate("/login");
    } catch (err) {
      setError(err);
    }
  }

  return (
    <AuthLayout title="Choose a new password">
      <form onSubmit={submit}>
        <Field label="New password" htmlFor="pw" hint="At least 12 characters.">
          <input id="pw" className="input" type="password" required minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <ErrorBanner error={error} />
        <button className="btn-primary mt-3 w-full">Set password</button>
      </form>
    </AuthLayout>
  );
}
