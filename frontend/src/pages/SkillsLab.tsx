import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api, sse } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type {
  CatalogSkill,
  DebriefOut,
  LabStateOut,
  QuotaOut,
  ScanOut,
} from "@/api/types";
import { ToolTimeline, type ToolEvent } from "@/components/ToolTimeline";
import { Badge, ErrorBanner, SafeMarkdown } from "@/components/ui";

interface Defenses {
  scanner: boolean;
  tool_allowlist: boolean;
  egress_allowlist: boolean;
  human_approval: boolean;
}

const DEFENSE_LABELS: Record<keyof Defenses, string> = {
  scanner: "Scan skills on install",
  tool_allowlist: "Per-skill tool allowlist",
  egress_allowlist: "Egress allowlist",
  human_approval: "Require approval to send data out",
};

export function SkillsLab() {
  const { setQuota } = useAuth();
  const [catalog, setCatalog] = useState<CatalogSkill[]>([]);
  const [selected, setSelected] = useState<string[]>([]);
  const [defenses, setDefenses] = useState<Defenses>({
    scanner: false,
    tool_allowlist: false,
    egress_allowlist: false,
    human_approval: false,
  });
  const [scan, setScan] = useState<{ name: string; result: ScanOut } | null>(null);
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [installed, setInstalled] = useState<string[]>([]);
  const [blockedInstall, setBlockedInstall] = useState<string[]>([]);
  const [input, setInput] = useState("");
  const [answer, setAnswer] = useState("");
  const [tools, setTools] = useState<ToolEvent[]>([]);
  const [labState, setLabState] = useState<LabStateOut | null>(null);
  const [debrief, setDebrief] = useState<DebriefOut | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<unknown>(null);

  useEffect(() => {
    api<CatalogSkill[]>("/skills-lab/catalog").then(setCatalog).catch(() => undefined);
  }, []);

  async function runScan(name: string) {
    setScan({ name, result: await api<ScanOut>("/skills-lab/scan", { method: "POST", body: { skill_name: name } }) });
  }

  async function start() {
    setError(null);
    try {
      const res = await api<{ session_id: string; installed: string[]; blocked_by_scanner: string[] }>(
        "/skills-lab/session",
        { method: "POST", body: { catalog_skills: selected, defenses } },
      );
      setSessionId(res.session_id);
      setInstalled(res.installed);
      setBlockedInstall(res.blocked_by_scanner);
      setTools([]);
      setAnswer("");
      setLabState(null);
      setDebrief(null);
    } catch (err) {
      setError(err);
    }
  }

  async function send(e: React.FormEvent) {
    e.preventDefault();
    if (!sessionId || !input.trim() || busy) return;
    setBusy(true);
    setError(null);
    setAnswer("");
    setDebrief(null);
    const message = input;
    setInput("");
    try {
      for await (const ev of sse("/skills-lab/message", { session_id: sessionId, message })) {
        if (ev.event === "quota") setQuota(ev.data as QuotaOut);
        else if (ev.event === "delta") setAnswer((a) => a + (ev.data as { text: string }).text);
        else if (ev.event === "tool_call") setTools((p) => [...p, ev.data as ToolEvent]);
        else if (ev.event === "tool_result")
          setTools((p) => {
            const d = ev.data as ToolEvent;
            const i = p.findIndex((t) => t.id === d.id);
            if (i === -1) return [...p, d];
            const copy = [...p];
            copy[i] = { ...copy[i], result: d.result };
            return copy;
          });
        else if (ev.event === "error") setError(new Error((ev.data as { message: string }).message));
      }
      setLabState(await api<LabStateOut>(`/skills-lab/session/${sessionId}`));
      setDebrief(await api<DebriefOut>(`/skills-lab/session/${sessionId}/debrief`));
    } catch (err) {
      setError(err);
    } finally {
      setBusy(false);
    }
  }

  const toggle = (name: string) =>
    setSelected((s) => (s.includes(name) ? s.filter((x) => x !== name) : [...s, name]));

  return (
    <div className="mx-auto max-w-6xl">
      <h1 className="mb-1 text-2xl font-semibold">Skills Lab</h1>
      <p className="mb-4 text-sm text-muted">
        Install skills, then ask the assistant to use them. Some hide instructions that make it
        leak the workspace&apos;s (fake) secrets. Nothing here touches the real network or disk.{" "}
        <Link to="/learn" className="text-accent hover:underline">
          Learn how to vet skills →
        </Link>
      </p>

      {!sessionId ? (
        <div className="grid gap-6 lg:grid-cols-2">
          <div>
            <h2 className="mb-2 text-sm font-medium text-muted">1. Choose skills to install</h2>
            <div className="space-y-2">
              {catalog.map((skill) => (
                <div key={skill.name} className="card flex items-start justify-between gap-2">
                  <label className="flex-1 cursor-pointer">
                    <div className="flex items-center gap-2">
                      <input type="checkbox" checked={selected.includes(skill.name)} onChange={() => toggle(skill.name)} />
                      <span className="font-mono text-sm">{skill.name}</span>
                    </div>
                    <p className="ml-6 text-xs text-muted">{skill.description}</p>
                  </label>
                  <button className="btn-ghost text-xs" onClick={() => runScan(skill.name)}>
                    Inspect
                  </button>
                </div>
              ))}
            </div>
          </div>
          <div>
            <h2 className="mb-2 text-sm font-medium text-muted">2. Turn on defences (optional)</h2>
            <div className="card space-y-2">
              {(Object.keys(DEFENSE_LABELS) as (keyof Defenses)[]).map((key) => (
                <label key={key} className="flex items-center gap-2 text-sm">
                  <input
                    type="checkbox"
                    checked={defenses[key]}
                    onChange={() => setDefenses((d) => ({ ...d, [key]: !d[key] }))}
                  />
                  {DEFENSE_LABELS[key]}
                </label>
              ))}
            </div>
            <ErrorBanner error={error} />
            <button className="btn-primary mt-3 w-full" disabled={selected.length === 0} onClick={start}>
              Install & open workspace
            </button>
            {scan && <InspectPanel name={scan.name} result={scan.result} onClose={() => setScan(null)} />}
          </div>
        </div>
      ) : (
        <div className="space-y-4">
          <div className="flex flex-wrap items-center gap-2 text-sm">
            <span className="text-muted">Installed:</span>
            {installed.map((n) => (
              <Badge key={n} tone="info">
                {n}
              </Badge>
            ))}
            {blockedInstall.map((n) => (
              <Badge key={n} tone="danger">
                {n} blocked by scanner
              </Badge>
            ))}
            <button className="btn-ghost ml-auto text-xs" onClick={() => setSessionId(null)}>
              New session
            </button>
          </div>

          <div className="grid gap-4 lg:grid-cols-3">
            <div className="lg:col-span-1">
              <div className="mb-1 text-sm font-medium text-muted">Assistant</div>
              <div className="card min-h-[10rem]">
                {answer ? <SafeMarkdown>{answer}</SafeMarkdown> : <p className="text-sm text-muted">Ask it to use an installed skill.</p>}
              </div>
              <form onSubmit={send} className="mt-2 flex gap-2">
                <input className="input" value={input} onChange={(e) => setInput(e.target.value)} placeholder="e.g. Summarize report.txt with pdf-summarizer-pro" />
                <button className="btn-primary" disabled={busy || !input.trim()}>
                  Send
                </button>
              </form>
              <ErrorBanner error={error} />
            </div>

            <div>
              <div className="mb-1 text-sm font-medium text-muted">Tool timeline</div>
              <div className="card">
                <ToolTimeline calls={tools} />
              </div>
            </div>

            <div>
              <div className="mb-1 text-sm font-medium text-danger">Attacker server</div>
              <div className="card border-danger/40">
                {labState && labState.attacker_log.length > 0 ? (
                  labState.attacker_log.map((entry, i) => (
                    <div key={i} className="mb-2 text-xs">
                      <div className="font-mono text-danger">
                        {entry.method} {entry.url}
                      </div>
                      <pre className="whitespace-pre-wrap break-words text-muted">{entry.body}</pre>
                    </div>
                  ))
                ) : (
                  <p className="text-xs text-muted">Nothing captured.</p>
                )}
                {labState && labState.blocked_actions.length > 0 && (
                  <div className="mt-2 border-t border-border pt-2">
                    {labState.blocked_actions.map((b, i) => (
                      <div key={i} className="text-xs text-ok">
                        ✓ blocked {b.tool} ({b.defense})
                      </div>
                    ))}
                  </div>
                )}
              </div>
            </div>
          </div>

          {debrief && <Debrief debrief={debrief} />}
        </div>
      )}
    </div>
  );
}

function InspectPanel({ name, result, onClose }: { name: string; result: ScanOut; onClose: () => void }) {
  return (
    <div className="card mt-3 border-accent/40">
      <div className="mb-2 flex items-center justify-between">
        <span className="font-mono text-sm">{name}</span>
        <button className="text-xs text-muted hover:text-fg" onClick={onClose}>
          close
        </button>
      </div>
      <div className="mb-2">
        {result.suspicious ? (
          <Badge tone="danger">suspicious ({result.max_severity})</Badge>
        ) : (
          <Badge tone="ok">looks clean</Badge>
        )}
      </div>
      <ul className="mb-3 space-y-1 text-xs">
        {result.findings.map((f, i) => (
          <li key={i}>
            <span className="font-medium">{f.kind}:</span> {f.message}
            {f.excerpt && <div className="font-mono text-muted">{f.excerpt}</div>}
          </li>
        ))}
      </ul>
      <details className="text-xs">
        <summary className="cursor-pointer text-muted">As the model reads it</summary>
        <pre className="mt-1 whitespace-pre-wrap break-words rounded bg-bg p-2 font-mono">
          {result.as_model_reads}
        </pre>
      </details>
    </div>
  );
}

function Debrief({ debrief }: { debrief: DebriefOut }) {
  return (
    <div className={`card ${debrief.exfiltrated ? "border-danger/50" : "border-ok/50"}`}>
      <div className="mb-2 flex items-center gap-2">
        <span className="text-sm font-semibold">What just happened</span>
        {debrief.exfiltrated ? <Badge tone="danger">data exfiltrated</Badge> : debrief.attacked ? <Badge tone="ok">attack blocked</Badge> : <Badge tone="ok">benign</Badge>}
      </div>
      <ol className="mb-2 list-decimal space-y-1 pl-5 text-sm">
        {debrief.steps.map((step, i) => (
          <li key={i}>{step}</li>
        ))}
      </ol>
      {debrief.technique && <p className="text-sm text-muted">{debrief.technique}</p>}
      <Link to="/learn" className="mt-2 inline-block text-sm text-accent hover:underline">
        Read: Before you install a skill →
      </Link>
    </div>
  );
}
