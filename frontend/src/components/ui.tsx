/** Small presentational helpers shared across pages. */

import Markdown from "react-markdown";
import type { ReactNode } from "react";

import { ApiError } from "@/api/client";

export function Spinner({ label }: { label?: string }) {
  return (
    <div className="flex items-center gap-2 text-sm text-muted" role="status">
      <span className="h-4 w-4 animate-spin rounded-full border-2 border-border border-t-accent" />
      {label ?? "Loading…"}
    </div>
  );
}

export function ErrorBanner({ error }: { error: unknown }) {
  if (!error) return null;
  const message = error instanceof ApiError ? error.message : "Something went wrong.";
  return (
    <div className="rounded-lg border border-danger/40 bg-danger/10 px-3 py-2 text-sm text-danger">
      {message}
    </div>
  );
}

export function Field({
  label,
  htmlFor,
  children,
  hint,
}: {
  label: string;
  htmlFor?: string;
  children: ReactNode;
  hint?: string;
}) {
  return (
    <div className="mb-3">
      <label className="label" htmlFor={htmlFor}>
        {label}
      </label>
      {children}
      {hint && <p className="mt-1 text-xs text-muted">{hint}</p>}
    </div>
  );
}

/** Render model/LLM output as Markdown with raw HTML disabled (never trust the text). */
export function SafeMarkdown({ children }: { children: string }) {
  return (
    <div className="prose-sm max-w-none whitespace-pre-wrap break-words text-sm leading-relaxed">
      <Markdown
        components={{
          a: ({ href, children: inner }) => (
            <a href={href} target="_blank" rel="noopener noreferrer nofollow" className="text-accent underline">
              {inner}
            </a>
          ),
        }}
      >
        {children}
      </Markdown>
    </div>
  );
}

export function Badge({ tone, children }: { tone: "info" | "warn" | "danger" | "ok"; children: ReactNode }) {
  const tones = {
    info: "bg-accent/15 text-accent",
    warn: "bg-warn/15 text-warn",
    danger: "bg-danger/15 text-danger",
    ok: "bg-ok/15 text-ok",
  } as const;
  return <span className={`rounded px-2 py-0.5 text-xs font-medium ${tones[tone]}`}>{children}</span>;
}
