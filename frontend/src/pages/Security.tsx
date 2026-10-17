import { QRCodeSVG } from "qrcode.react";
import { useState } from "react";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Badge, ErrorBanner, Field } from "@/components/ui";

interface TotpSetup {
  secret: string;
  otpauth_uri: string;
}

export function Security() {
  const { me, refresh } = useAuth();
  const enabled = me?.user.totp_enabled ?? false;
  const [setup, setSetup] = useState<TotpSetup | null>(null);
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  async function start() {
    setBusy(true);
    setError(null);
    try {
      setSetup(await api<TotpSetup>("/me/totp/setup", { method: "POST" }));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  async function enable(e: React.FormEvent) {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      await api("/me/totp/enable", { method: "POST", body: { code } });
      setSetup(null);
      setCode("");
      await refresh();
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  return (
    <div className="mx-auto max-w-xl">
      <h1 className="mb-1 text-2xl font-semibold">Security</h1>
      <p className="mb-4 text-sm text-muted">
        Two-factor authentication protects your account with a code from an authenticator app.
        Staff accounts must enable it to use the Admin tools.
      </p>

      <div className="card">
        <div className="mb-3 flex items-center justify-between">
          <span className="font-medium">Two-factor authentication</span>
          <Badge tone={enabled ? "ok" : "warn"}>{enabled ? "On" : "Off"}</Badge>
        </div>

        {enabled && (
          <p className="text-sm text-muted">
            It&apos;s on. You&apos;ll be asked for a 6-digit code every time you sign in.
          </p>
        )}

        {!enabled && !setup && (
          <>
            <ErrorBanner error={error} />
            <button className="btn-primary mt-2" onClick={() => void start()} disabled={busy}>
              {busy ? "Starting…" : "Set up two-factor"}
            </button>
          </>
        )}

        {!enabled && setup && (
          <form onSubmit={enable}>
            <ol className="mb-4 list-decimal space-y-1 pl-5 text-sm text-muted">
              <li>Open an authenticator app (Google Authenticator, Authy, 1Password…).</li>
              <li>Scan the QR code, or enter the secret manually.</li>
              <li>Type the 6-digit code it shows to confirm.</li>
            </ol>
            <div className="mb-3 inline-block rounded-lg bg-white p-3">
              <QRCodeSVG value={setup.otpauth_uri} size={176} />
            </div>
            <p className="mb-3 break-all font-mono text-xs text-muted">
              Secret: <span className="select-all text-fg">{setup.secret}</span>
            </p>
            <Field label="6-digit code">
              <input
                className="input font-mono"
                inputMode="numeric"
                autoComplete="one-time-code"
                pattern="\d{6}"
                maxLength={6}
                value={code}
                onChange={(e) => setCode(e.target.value.replace(/\D/g, ""))}
                required
              />
            </Field>
            <ErrorBanner error={error} />
            <button className="btn-primary mt-2" disabled={busy || code.length !== 6}>
              {busy ? "Checking…" : "Turn on two-factor"}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
