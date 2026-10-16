import { useEffect, useState } from "react";
import { Link } from "react-router-dom";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import { Badge, ErrorBanner, Field } from "@/components/ui";

interface Demo {
  id: string;
  feature: string;
  title: string;
  prompt: string;
  response: string;
}

export function Dashboard() {
  const { me, refresh } = useAuth();
  const [message, setMessage] = useState("");
  const [requested, setRequested] = useState(false);
  const [error, setError] = useState<unknown>(null);
  const [demos, setDemos] = useState<Demo[]>([]);

  useEffect(() => {
    api<Demo[]>("/demos").then(setDemos).catch(() => undefined);
  }, []);

  if (!me) return null;
  const { access, user } = me;

  async function requestAccess(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/access-requests", { method: "POST", body: { message } });
      setRequested(true);
      await refresh();
    } catch (err) {
      setError(err);
    }
  }

  return (
    <div className="mx-auto max-w-3xl space-y-6">
      <div>
        <h1 className="text-2xl font-semibold">Welcome</h1>
        <p className="text-sm text-muted">{user.email}</p>
      </div>

      {access.has_access ? (
        <div className="card">
          <div className="mb-2 flex items-center gap-2">
            <Badge tone="ok">Access active</Badge>
          </div>
          <p className="text-sm text-muted">
            You have access through: {access.cohorts.map((c) => c.name).join(", ")}.
          </p>
          <div className="mt-3 flex flex-wrap gap-2">
            <Link to="/playground" className="btn-primary">
              Open Playground
            </Link>
            <Link to="/skills-lab" className="btn-ghost">
              Skills Lab
            </Link>
          </div>
        </div>
      ) : (
        <div className="card">
          <div className="mb-2">
            <Badge tone="warn">No access yet</Badge>
          </div>
          <p className="mb-3 text-sm text-muted">
            This playground is for course participants. You can read the Learn section and preview
            the demos below, but running prompts needs access.
          </p>
          {access.pending_request || requested ? (
            <p className="text-sm text-accent">Your access request is pending review.</p>
          ) : (
            <form onSubmit={requestAccess}>
              <Field label="Request access" hint="Tell the instructor which course or group you're in.">
                <textarea className="input" rows={2} value={message} onChange={(e) => setMessage(e.target.value)} />
              </Field>
              <ErrorBanner error={error} />
              <button className="btn-primary mt-2">Request access</button>
            </form>
          )}
        </div>
      )}

      <div>
        <div className="mb-2 flex items-center justify-between">
          <h2 className="text-lg font-semibold">Previews</h2>
          <Link to="/learn" className="text-sm text-accent hover:underline">
            Learn the concepts →
          </Link>
        </div>
        <div className="grid gap-3 sm:grid-cols-2">
          {demos.map((demo) => (
            <div key={demo.id} className="card">
              <div className="mb-1 text-sm font-medium">{demo.title}</div>
              <pre className="mb-2 whitespace-pre-wrap rounded bg-bg p-2 font-mono text-xs text-muted">
                {demo.prompt}
              </pre>
              <p className="text-sm">{demo.response}</p>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
