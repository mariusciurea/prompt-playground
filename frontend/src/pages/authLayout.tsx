/** Centered card layout and Turnstile widget for the public auth pages. */

import { Turnstile, type TurnstileInstance } from "@marsidev/react-turnstile";
import type { ReactNode, RefObject } from "react";

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

/**
 * Renders the Turnstile challenge when configured; otherwise a no-op (dev).
 *
 * Turnstile tokens are single-use: the server's siteverify call consumes them. Callers must
 * call `widgetRef.current?.reset()` (and clear their token) after every submit attempt that
 * did not navigate away, or the next submit re-sends a spent token and fails the bot check.
 */
export function BotCheck({
  onToken,
  widgetRef,
}: {
  onToken: (token: string | null) => void;
  widgetRef: RefObject<TurnstileInstance | undefined>;
}) {
  if (!SITE_KEY) return null;
  return (
    <div className="mb-3">
      <Turnstile
        ref={widgetRef}
        siteKey={SITE_KEY}
        onSuccess={onToken}
        onExpire={() => onToken(null)}
        onError={() => onToken(null)}
      />
    </div>
  );
}
