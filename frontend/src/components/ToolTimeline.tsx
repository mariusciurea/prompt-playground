/** A live timeline of agent tool calls, coloured by how risky the tool is. */

import { Badge } from "@/components/ui";

export interface ToolEvent {
  id: string;
  name: string;
  args: Record<string, unknown>;
  result?: unknown;
}

const RISKY = new Set(["http_request", "send_email", "read_from_disc", "read_file"]);

export function ToolTimeline({ calls }: { calls: ToolEvent[] }) {
  if (calls.length === 0) {
    return <p className="text-sm text-muted">No tools called yet.</p>;
  }
  return (
    <ol className="space-y-2">
      {calls.map((call) => (
        <li key={call.id} className="rounded-lg border border-border bg-bg p-2 text-xs">
          <div className="mb-1 flex items-center gap-2">
            <span className="font-mono font-medium">{call.name}</span>
            {RISKY.has(call.name) ? <Badge tone="danger">sensitive</Badge> : <Badge tone="info">tool</Badge>}
          </div>
          <pre className="whitespace-pre-wrap break-words font-mono text-muted">
            {JSON.stringify(call.args, null, 2)}
          </pre>
          {call.result !== undefined && (
            <details className="mt-1">
              <summary className="cursor-pointer text-muted">result</summary>
              <pre className="whitespace-pre-wrap break-words font-mono text-muted">
                {JSON.stringify(call.result, null, 2)}
              </pre>
            </details>
          )}
        </li>
      ))}
    </ol>
  );
}
