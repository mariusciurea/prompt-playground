/** Centered card layout and Turnstile widget for the public auth pages. */

import { Turnstile } from "@marsidev/react-turnstile";
import type { ReactNode } from "react";

const SITE_KEY = import.meta.env.VITE_TURNSTILE_SITE_KEY as string | undefined;

export function AuthLayout({ title, children }: { title: string; children: ReactNode }) {
  return (
    <div className="flex min-h-full items-center justify-center p-4">
      <div className="w-full max-w-md">
        <div className="mb-6 text-center">
          <div className="font-mono text-2xl text-accent">▚ AI Playground</div>
          <p className="mt-1 text-sm text-muted">Prompt engineering & AI security lab</p>
        </div>
        <div className="card">
          <h1 className="mb-4 text-lg font-semibold">{title}</h1>
          {children}
        </div>
      </div>
    </div>
  );
}

/** Renders the Turnstile challenge when configured; otherwise a no-op (dev). */
export function BotCheck({ onToken }: { onToken: (token: string | null) => void }) {
  if (!SITE_KEY) return null;
  return (
    <div className="mb-3">
      <Turnstile siteKey={SITE_KEY} onSuccess={onToken} onExpire={() => onToken(null)} />
    </div>
  );
}
