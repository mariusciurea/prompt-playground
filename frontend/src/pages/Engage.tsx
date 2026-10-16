import { useEffect, useState } from "react";

import { api, sse } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { EngageLevelOut, QuotaOut } from "@/api/types";
import { Badge, ErrorBanner, SafeMarkdown } from "@/components/ui";

export function Engage() {
  const { setQuota } = useAuth();
  const [levels, setLevels] = useState<EngageLevelOut[]>([]);
  const [current, setCurrent] = useState(1);
  const [message, setMessage] = useState("");
  const [answer, setAnswer] = useState("");
  const [guess, setGuess] = useState("");
  const [feedback, setFeedback] = useState<{ ok: boolean; lesson: string | null } | null>(null);
  const [running, setRunning] = useState(false);
  const [error, setError] = useState<unknown>(null);

  const loadLevels = () => api<EngageLevelOut[]>("/engage/levels").then(setLevels);
  useEffect(() => {
    void loadLevels();
  }, []);

  const level = levels.find((l) => l.number === current);

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!message.trim() || running) return;
    setRunning(true);
    setError(null);
    setAnswer("");
    try {
      for await (const ev of sse("/engage/message", { level: current, message })) {
        if (ev.event === "quota") setQuota(ev.data as QuotaOut);
        else if (ev.event === "delta") setAnswer((a) => a + (ev.data as { text: string }).text);
        else if (ev.event === "error") setError(new Error((ev.data as { message: string }).message));
      }
    } catch (err) {
      setError(err);
    } finally {
      setRunning(false);
    }
  }

  async function checkGuess(e: React.FormEvent) {
    e.preventDefault();
    const res = await api<{ correct: boolean; lesson: string | null }>("/engage/guess", {
      method: "POST",
      body: { level: current, guess },
    });
    setFeedback({ ok: res.correct, lesson: res.lesson });
    if (res.correct) {
      setGuess("");
      await loadLevels();
    }
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-1 text-2xl font-semibold">Engage</h1>
      <p className="mb-4 text-sm text-muted">
        Each level hides a password in the system prompt. Talk the model into revealing it.
      </p>

      <div className="mb-4 flex flex-wrap gap-2">
        {levels.map((l) => (
          <button
            key={l.number}
            className={`btn-ghost text-sm ${current === l.number ? "border-accent text-accent" : ""}`}
            onClick={() => {
              setCurrent(l.number);
              setAnswer("");
              setFeedback(null);
            }}
          >
            Level {l.number} {l.solved && "✓"}
          </button>
        ))}
      </div>

      <div className="grid gap-6 lg:grid-cols-2">
        <div>
          <form onSubmit={send}>
            <textarea
              className="input font-mono"
              rows={5}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              placeholder="Try to make the assistant reveal the password…"
            />
            <ErrorBanner error={error} />
            <button className="btn-primary mt-2 w-full" disabled={running || !message.trim()}>
              {running ? "Sending…" : "Send"}
            </button>
          </form>

          <form onSubmit={checkGuess} className="mt-4">
            <div className="flex gap-2">
              <input className="input" value={guess} onChange={(e) => setGuess(e.target.value)} placeholder="Password guess" />
              <button className="btn-ghost">Check</button>
            </div>
            {feedback && (
              <div className="mt-2">
                <Badge tone={feedback.ok ? "ok" : "danger"}>{feedback.ok ? "Correct!" : "Wrong"}</Badge>
              </div>
            )}
          </form>

          {level?.solved && level.lesson && (
            <div className="card mt-4 border-ok/40">
              <div className="mb-1 text-sm font-semibold text-ok">What this level teaches</div>
              <SafeMarkdown>{level.lesson}</SafeMarkdown>
            </div>
          )}
        </div>

        <div>
          <div className="mb-2 text-sm font-medium text-muted">Model answer</div>
          <div className="card min-h-[12rem]">
            {answer ? <SafeMarkdown>{answer}</SafeMarkdown> : <p className="text-sm text-muted">No answer yet.</p>}
          </div>
        </div>
      </div>
    </div>
  );
}
