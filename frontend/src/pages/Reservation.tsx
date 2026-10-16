import { useState } from "react";

import { useAgentChat } from "@/hooks/useAgentChat";
import { ToolTimeline } from "@/components/ToolTimeline";
import { ErrorBanner, SafeMarkdown } from "@/components/ui";

export function Reservation() {
  const chat = useAgentChat("/reservation/session", "/reservation/message");
  const [input, setInput] = useState("");

  async function submit(e: React.FormEvent) {
    e.preventDefault();
    const text = input;
    setInput("");
    await chat.send(text);
  }

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-1 text-2xl font-semibold">Reservation</h1>
      <p className="mb-4 text-sm text-muted">
        A cinema agent with tools. Ask it to find or book movies, or to read stored data — and
        watch which tools it calls. (It can read more than it should: that&apos;s the lesson.)
      </p>

      <div className="grid gap-6 lg:grid-cols-[1fr_20rem]">
        <div>
          <div className="card mb-3 min-h-[20rem] space-y-3">
            {chat.turns.length === 0 && (
              <p className="text-sm text-muted">Try: &quot;What movies are on tonight at 8pm?&quot;</p>
            )}
            {chat.turns.map((turn, i) => (
              <div key={i} className={turn.role === "user" ? "text-right" : ""}>
                <div
                  className={`inline-block max-w-[85%] rounded-lg px-3 py-2 text-left text-sm ${turn.role === "user" ? "bg-accent/15" : "bg-bg"}`}
                >
                  {turn.role === "assistant" ? (
                    <SafeMarkdown>{turn.text || "…"}</SafeMarkdown>
                  ) : (
                    turn.text
                  )}
                </div>
              </div>
            ))}
          </div>
          <ErrorBanner error={chat.error} />
          <form onSubmit={submit} className="mt-2 flex gap-2">
            <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="Message the agent…" />
            <button className="btn-primary" disabled={chat.busy || !input.trim()}>
              Send
            </button>
          </form>
        </div>

        <div>
          <div className="mb-2 text-sm font-medium text-muted">Tools used</div>
          <div className="card">
            <ToolTimeline calls={chat.tools} />
          </div>
        </div>
      </div>
    </div>
  );
}
