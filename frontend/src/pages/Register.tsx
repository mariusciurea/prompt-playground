import { useState } from "react";
import { Link, useSearchParams } from "react-router-dom";

import { api } from "@/api/client";
import { ErrorBanner, Field } from "@/components/ui";
import { AuthLayout, BotCheck } from "@/pages/authLayout";

export function Register() {
  const [params] = useSearchParams();
  // Invitations link to /register#email=... so the field is pre-filled.
  const invited = new URLSearchParams(window.location.hash.slice(1)).get("email");
  const [email, setEmail] = useState(invited ?? params.get("email") ?? "");
  const [password, setPassword] = useState("");
  const [token, setToken] = useState<string | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [done, setDone] = useState(false);
  const [busy, setBusy] = useState(false);

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/auth/register", {
        method: "POST",
        body: { email, password, turnstile_token: token },
      });
      setDone(true);
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  if (done) {
    return (
      <AuthLayout title="Check your inbox">
        <p className="text-sm text-muted">
          If the address can be used, we&apos;ve sent a confirmation link. Open it to activate your
          account, then sign in.
        </p>
        <Link to="/login" className="btn-primary mt-4 w-full">
          Back to sign in
        </Link>
      </AuthLayout>
    );
  }

  return (
    <AuthLayout title="Create account">
      <form onSubmit={submit}>
        <Field label="E-mail" htmlFor="email">
          <input id="email" className="input" type="email" autoComplete="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
        </Field>
        <Field label="Password" htmlFor="password" hint="At least 12 characters.">
          <input id="password" className="input" type="password" autoComplete="new-password" required minLength={12} value={password} onChange={(e) => setPassword(e.target.value)} />
        </Field>
        <BotCheck onToken={setToken} />
        <ErrorBanner error={error} />
        <button className="btn-primary mt-3 w-full" disabled={busy}>
          {busy ? "Creating…" : "Create account"}
        </button>
      </form>
      <p className="mt-4 text-sm text-muted">
        Already have an account?{" "}
        <Link to="/login" className="hover:text-fg">
          Sign in
        </Link>
      </p>
    </AuthLayout>
  );
}
