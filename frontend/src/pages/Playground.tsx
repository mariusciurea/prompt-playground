import { useEffect, useRef, useState } from "react";

import { api, sse } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { QuotaOut } from "@/api/types";
import { ErrorBanner, Field, SafeMarkdown } from "@/components/ui";

interface Example {
  id: string;
  label: string;
  system_prompt: string;
  user_prompt: string;
}

export function Playground() {
  const { setQuota } = useAuth();
  const [examples, setExamples] = useState<Example[]>([]);
  const [system, setSystem] = useState("");
  const [user, setUser] = useState("");
  const [temperature, setTemperature] = useState(1);
  const [answer, setAnswer] = useState("");
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const outputRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<Example[]>("/playground/examples").then(setExamples).catch(() => undefined);
  }, []);

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!user.trim() || running) return;
    setRunning(true);
    setError(null);
    setAnswer("");
    try {
      for await (const ev of sse("/playground/run", {
        system_prompt: system,
        user_prompt: user,
        temperature,
      })) {
        if (ev.event === "quota") setQuota(ev.data as QuotaOut);
        else if (ev.event === "delta") setAnswer((a) => a + (ev.data as { text: string }).text);
        else if (ev.event === "error") setError(new Error((ev.data as { message: string }).message));
      }
    } catch (err) {
      setError(err);
    } finally {
      setRunning(false);
      outputRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-1 text-2xl font-semibold">Playground</h1>
      <p className="mb-4 text-sm text-muted">
        Shape the model with a system prompt, ask with a user prompt, and watch it stream.
      </p>

      <div className="grid gap-6 lg:grid-cols-2">
        <form onSubmit={run}>
          <div className="mb-3 flex flex-wrap gap-2">
            {examples.map((ex) => (
              <button
                key={ex.id}
                type="button"
                className="btn-ghost text-xs"
                onClick={() => {
                  setSystem(ex.system_prompt);
                  setUser(ex.user_prompt);
                }}
              >
                {ex.label}
              </button>
            ))}
          </div>
          <Field label="System prompt (optional)">
            <textarea className="input font-mono" rows={4} value={system} onChange={(e) => setSystem(e.target.value)} />
          </Field>
          <Field label="User prompt">
            <textarea className="input font-mono" rows={6} value={user} onChange={(e) => setUser(e.target.value)} placeholder="What do you want to ask?" />
          </Field>
          <Field label={`Temperature: ${temperature.toFixed(1)}`}>
            <input type="range" min={0} max={2} step={0.1} value={temperature} onChange={(e) => setTemperature(Number(e.target.value))} className="w-full" />
          </Field>
          <ErrorBanner error={error} />
          <button className="btn-primary mt-2 w-full" disabled={running || !user.trim()}>
            {running ? "Generating…" : "Run"}
          </button>
        </form>

        <div ref={outputRef}>
          <div className="mb-2 text-sm font-medium text-muted">Answer</div>
          <div className="card min-h-[12rem]">
            {answer ? (
              <SafeMarkdown>{answer}</SafeMarkdown>
            ) : (
              <p className="text-sm text-muted">The response will appear here.</p>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
