/** Drive an agent conversation over SSE: messages, streaming reply, and tool timeline. */

import { useCallback, useRef, useState } from "react";

import { api, sse } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { QuotaOut } from "@/api/types";
import type { ToolEvent } from "@/components/ToolTimeline";

export interface ChatTurn {
  role: "user" | "assistant";
  text: string;
}

export function useAgentChat(startPath: string, messagePath: string) {
  const { setQuota } = useAuth();
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [turns, setTurns] = useState<ChatTurn[]>([]);
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const startingRef = useRef(false);

  const ensureSession = useCallback(async (): Promise<string> => {
    if (sessionId) return sessionId;
    const res = await api<{ session_id: string }>(startPath, { method: "POST" });
    setSessionId(res.session_id);
    return res.session_id;
  }, [sessionId, startPath]);

  const send = useCallback(
    async (message: string) => {
      if (busy || !message.trim()) return;
      setBusy(true);
      setError(null);
      setTurns((t) => [...t, { role: "user", text: message }, { role: "assistant", text: "" }]);
      try {
        const id = startingRef.current ? sessionId! : await ensureSession();
        for await (const ev of sse(messagePath, { session_id: id, message })) {
          if (ev.event === "quota") setQuota(ev.data as QuotaOut);
          else if (ev.event === "delta")
            setTurns((t) => updateLast(t, (ev.data as { text: string }).text));
          else if (ev.event === "tool_call")
            setTools((prev) => [...prev, ev.data as ToolEvent]);
          else if (ev.event === "tool_result")
            setTools((prev) => mergeResult(prev, ev.data as ToolEvent));
          else if (ev.event === "error")
            setError(new Error((ev.data as { message: string }).message));
        }
      } catch (err) {
        setError(err);
      } finally {
        setBusy(false);
      }
    },
    [busy, ensureSession, messagePath, sessionId, setQuota],
  );

  const reset = useCallback(() => {
    setSessionId(null);
    setTurns([]);
    setTools([]);
    setError(null);
  }, []);

  return { sessionId, turns, tools, busy, error, send, reset, setSessionId };
}

function updateLast(turns: ChatTurn[], chunk: string): ChatTurn[] {
  const copy = [...turns];
  const last = copy[copy.length - 1];
  if (last?.role === "assistant") copy[copy.length - 1] = { ...last, text: last.text + chunk };
  return copy;
}

function mergeResult(tools: ToolEvent[], done: ToolEvent): ToolEvent[] {
  const index = tools.findIndex((t) => t.id === done.id);
  if (index === -1) return [...tools, done];
  const copy = [...tools];
  copy[index] = { ...copy[index], result: done.result };
  return copy;
}
