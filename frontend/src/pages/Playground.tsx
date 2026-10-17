import { useCallback, useEffect, useRef, useState } from "react";

import { api, sse } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { Page, QuotaOut } from "@/api/types";
import { Badge, ErrorBanner, Field, SafeMarkdown, Spinner } from "@/components/ui";

interface Example {
  id: string;
  label: string;
  system_prompt: string;
  user_prompt: string;
}

interface HistoryItem {
  id: string;
  request: { system_prompt?: string; user_prompt?: string; temperature?: number };
  response: string;
  created_at: string;
}

const HISTORY_PAGE = 10;

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
  const [history, setHistory] = useState<HistoryItem[]>([]);
  const [historyTotal, setHistoryTotal] = useState(0);
  const [historyLoading, setHistoryLoading] = useState(true);
  const [activeId, setActiveId] = useState<string | null>(null);
  const [clearing, setClearing] = useState(false);

  useEffect(() => {
    api<Example[]>("/playground/examples").then(setExamples).catch(() => undefined);
  }, []);

  // offset 0 replaces the list (first load / after a run); otherwise it appends the next page.
  const loadHistory = useCallback(async (offset = 0) => {
    setHistoryLoading(true);
    try {
      const page = await api<Page<HistoryItem>>(
        `/history?feature=playground&limit=${HISTORY_PAGE}&offset=${offset}`,
      );
      setHistory((prev) => (offset === 0 ? page.items : [...prev, ...page.items]));
      setHistoryTotal(page.total);
    } catch {
      // History is a convenience; the playground still works without it.
    } finally {
      setHistoryLoading(false);
    }
  }, []);

  useEffect(() => {
    void loadHistory();
  }, [loadHistory]);

  async function clearHistory() {
    if (!window.confirm("Delete your whole Playground history? This cannot be undone.")) return;
    setClearing(true);
    try {
      await api("/history?feature=playground", { method: "DELETE" });
      setHistory([]);
      setHistoryTotal(0);
      setActiveId(null);
    } catch (err) {
      setError(err);
    } finally {
      setClearing(false);
    }
  }

  function restore(item: HistoryItem) {
    setSystem(item.request.system_prompt ?? "");
    setUser(item.request.user_prompt ?? "");
    setTemperature(item.request.temperature ?? 1);
    setAnswer(item.response);
    setActiveId(item.id);
    setError(null);
  }

  async function run(e: React.FormEvent) {
    e.preventDefault();
    if (!user.trim() || running) return;
    setRunning(true);
    setError(null);
    setAnswer("");
    setActiveId(null);
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
      void loadHistory();
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

          <div className="mb-2 mt-6 flex items-center justify-between text-sm font-medium text-muted">
            <span>History</span>
            {historyTotal > 0 && (
              <span className="flex items-center gap-3 text-xs font-normal">
                {historyTotal} saved
                <button
                  type="button"
                  className="text-danger hover:underline disabled:opacity-50"
                  onClick={() => void clearHistory()}
                  disabled={clearing || running}
                >
                  {clearing ? "Clearing…" : "Clear"}
                </button>
              </span>
            )}
          </div>
          <div className="card p-2">
            {history.length === 0 && !historyLoading && (
              <p className="p-2 text-sm text-muted">Your previous runs will appear here.</p>
            )}
            <ul className="max-h-96 space-y-1 overflow-y-auto">
              {history.map((item) => (
                <li key={item.id}>
                  <button
                    type="button"
                    onClick={() => restore(item)}
                    className={`w-full rounded-lg px-3 py-2 text-left transition hover:bg-border/40 ${
                      activeId === item.id ? "bg-accent/10 ring-1 ring-accent/40" : ""
                    }`}
                  >
                    <div className="line-clamp-2 break-words font-mono text-xs">
                      {item.request.user_prompt}
                    </div>
                    <div className="mt-1 flex items-center gap-2 text-xs text-muted">
                      <span>{new Date(item.created_at).toLocaleString()}</span>
                      {item.request.system_prompt && <Badge tone="info">system</Badge>}
                    </div>
                  </button>
                </li>
              ))}
            </ul>
            {historyLoading && (
              <div className="p-2">
                <Spinner />
              </div>
            )}
            {!historyLoading && history.length < historyTotal && (
              <button
                type="button"
                className="btn-ghost mt-1 w-full text-xs"
                onClick={() => void loadHistory(history.length)}
              >
                Load more
              </button>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}
