import { useEffect, useState } from "react";
import { Link, NavLink, Navigate, Route, Routes } from "react-router-dom";

import { api } from "@/api/client";
import { useAuth } from "@/auth/AuthContext";
import type { Page } from "@/api/types";
import { Badge, ErrorBanner, Field, Spinner } from "@/components/ui";

const TABS = [
  { to: "cohorts", label: "Cohorts" },
  { to: "requests", label: "Requests" },
  { to: "users", label: "Users" },
  { to: "stats", label: "Stats" },
  { to: "audit", label: "Audit", adminOnly: true },
];

export function AdminPage() {
  const { me } = useAuth();
  const isAdmin = me?.user.role === "admin";
  if (me && !me.user.totp_enabled) {
    return (
      <div className="mx-auto max-w-xl">
        <h1 className="mb-4 text-2xl font-semibold">Admin</h1>
        <div className="card">
          <p className="mb-3 text-sm text-muted">
            Staff tools require two-factor authentication. Turn it on first, then come back here.
          </p>
          <Link to="/security" className="btn-primary">
            Set up two-factor
          </Link>
        </div>
      </div>
    );
  }
  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-4 text-2xl font-semibold">Admin</h1>
      <nav className="mb-6 flex flex-wrap gap-2 border-b border-border pb-2">
        {TABS.filter((t) => !t.adminOnly || isAdmin).map((t) => (
          <NavLink
            key={t.to}
            to={t.to}
            className={({ isActive }) =>
              `rounded-lg px-3 py-1.5 text-sm ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:text-fg"}`
            }
          >
            {t.label}
          </NavLink>
        ))}
      </nav>
      <Routes>
        <Route index element={<Navigate to="cohorts" replace />} />
        <Route path="cohorts" element={<Cohorts isAdmin={isAdmin} />} />
        <Route path="requests" element={<Requests />} />
        <Route path="users" element={<Users isAdmin={isAdmin} />} />
        <Route path="stats" element={<Stats />} />
        <Route path="audit" element={<Audit />} />
      </Routes>
    </div>
  );
}

interface Cohort {
  id: string;
  name: string;
  starts_at: string;
  ends_at: string;
  member_count: number;
  is_active: boolean;
  owner_email: string | null;
}

function Cohorts({ isAdmin }: { isAdmin: boolean }) {
  const [cohorts, setCohorts] = useState<Cohort[] | null>(null);
  const [name, setName] = useState("");
  const [start, setStart] = useState("");
  const [end, setEnd] = useState("");
  const [error, setError] = useState<unknown>(null);
  const [open, setOpen] = useState<Cohort | null>(null);

  const load = () => api<Cohort[]>("/admin/cohorts").then(setCohorts);
  useEffect(() => {
    void load();
  }, []);

  async function create(e: React.FormEvent) {
    e.preventDefault();
    setError(null);
    try {
      await api("/admin/cohorts", {
        method: "POST",
        body: { name, starts_at: new Date(start).toISOString(), ends_at: new Date(end).toISOString() },
      });
      setName("");
      await load();
    } catch (err) {
      setError(err);
    }
  }

  if (!cohorts) return <Spinner />;
  if (open) return <CohortMembers cohort={open} onBack={() => setOpen(null)} />;

  return (
    <div className="space-y-4">
      {isAdmin && (
        <form onSubmit={create} className="card grid gap-2 sm:grid-cols-4 sm:items-end">
          <Field label="Name">
            <input className="input" value={name} onChange={(e) => setName(e.target.value)} required />
          </Field>
          <Field label="Starts">
            <input className="input" type="datetime-local" value={start} onChange={(e) => setStart(e.target.value)} required />
          </Field>
          <Field label="Ends">
            <input className="input" type="datetime-local" value={end} onChange={(e) => setEnd(e.target.value)} required />
          </Field>
          <button className="btn-primary">Create</button>
        </form>
      )}
      <ErrorBanner error={error} />
      <div className="space-y-2">
        {cohorts.map((c) => (
          <div key={c.id} className="card flex items-center justify-between">
            <div>
              <div className="flex items-center gap-2 font-medium">
                {c.name} {c.is_active ? <Badge tone="ok">active</Badge> : <Badge tone="warn">inactive</Badge>}
              </div>
              <div className="text-xs text-muted">
                {c.member_count} members · ends {new Date(c.ends_at).toLocaleDateString()}
                {c.owner_email && ` · ${c.owner_email}`}
              </div>
            </div>
            <button className="btn-ghost text-sm" onClick={() => setOpen(c)}>
              Members
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}

interface Preview {
  new: string[];
  already_members: string[];
  duplicates: string[];
  invalid: { row: number; value: string; reason: string }[];
}

function CohortMembers({ cohort, onBack }: { cohort: Cohort; onBack: () => void }) {
  const [text, setText] = useState("");
  const [preview, setPreview] = useState<Preview | null>(null);
  const [error, setError] = useState<unknown>(null);
  const [message, setMessage] = useState("");

  async function doPreview() {
    setError(null);
    try {
      setPreview(await api<Preview>(`/admin/cohorts/${cohort.id}/import/preview-text`, { method: "POST", body: { text } }));
    } catch (err) {
      setError(err);
    }
  }

  async function confirm() {
    if (!preview) return;
    const emails = [...preview.new, ...preview.already_members];
    await api(`/admin/cohorts/${cohort.id}/members`, {
      method: "POST",
      body: { emails, send_invitations: true },
    });
    setMessage(`Added/invited ${emails.length} address(es).`);
    setPreview(null);
    setText("");
  }

  return (
    <div className="space-y-4">
      <button className="text-sm text-accent hover:underline" onClick={onBack}>
        ← Back to cohorts
      </button>
      <h2 className="text-lg font-semibold">{cohort.name} — add members</h2>
      <div className="card">
        <Field label="Paste e-mails" hint="Separated by lines, commas, or spaces. Or import a CSV/XLSX from a cohort's member list.">
          <textarea className="input font-mono" rows={5} value={text} onChange={(e) => setText(e.target.value)} />
        </Field>
        <button className="btn-ghost" onClick={doPreview}>
          Preview
        </button>
        <ErrorBanner error={error} />
        {message && <p className="mt-2 text-sm text-ok">{message}</p>}
        {preview && (
          <div className="mt-3 space-y-1 text-sm">
            <p>
              <Badge tone="ok">{preview.new.length} new</Badge>{" "}
              <Badge tone="info">{preview.already_members.length} already</Badge>{" "}
              <Badge tone="warn">{preview.duplicates.length} duplicate</Badge>{" "}
              <Badge tone="danger">{preview.invalid.length} invalid</Badge>
            </p>
            {preview.invalid.length > 0 && (
              <ul className="text-xs text-danger">
                {preview.invalid.map((i) => (
                  <li key={i.row}>
                    row {i.row}: {i.value} — {i.reason}
                  </li>
                ))}
              </ul>
            )}
            <button className="btn-primary mt-2" onClick={confirm} disabled={preview.new.length + preview.already_members.length === 0}>
              Confirm & invite
            </button>
          </div>
        )}
      </div>
    </div>
  );
}

interface AccessRequest {
  id: string;
  user_email: string;
  message: string;
  status: string;
  created_at: string;
}

function Requests() {
  const [data, setData] = useState<Page<AccessRequest> | null>(null);
  const [cohorts, setCohorts] = useState<Cohort[]>([]);
  const [choice, setChoice] = useState<Record<string, string>>({});
  const [error, setError] = useState<unknown>(null);

  const load = () => api<Page<AccessRequest>>("/admin/access-requests").then(setData);
  useEffect(() => {
    void load();
    api<Cohort[]>("/admin/cohorts").then(setCohorts);
  }, []);

  async function review(id: string, approve: boolean) {
    setError(null);
    try {
      await api(`/admin/access-requests/${id}/review`, {
        method: "POST",
        body: { approve, cohort_id: approve ? choice[id] : null },
      });
      await load();
    } catch (err) {
      setError(err);
    }
  }

  if (!data) return <Spinner />;
  return (
    <div className="space-y-3">
      <ErrorBanner error={error} />
      {data.items.length === 0 && <p className="text-sm text-muted">No pending requests.</p>}
      {data.items.map((r) => (
        <div key={r.id} className="card">
          <div className="font-medium">{r.user_email}</div>
          {r.message && <p className="text-sm text-muted">{r.message}</p>}
          <div className="mt-2 flex flex-wrap items-center gap-2">
            <select className="input max-w-xs" value={choice[r.id] ?? ""} onChange={(e) => setChoice((c) => ({ ...c, [r.id]: e.target.value }))}>
              <option value="">Choose cohort…</option>
              {cohorts.map((c) => (
                <option key={c.id} value={c.id}>
                  {c.name}
                </option>
              ))}
            </select>
            <button className="btn-primary" disabled={!choice[r.id]} onClick={() => review(r.id, true)}>
              Approve
            </button>
            <button className="btn-ghost" onClick={() => review(r.id, false)}>
              Reject
            </button>
          </div>
        </div>
      ))}
    </div>
  );
}

interface AdminUser {
  id: string;
  email: string;
  role: string;
  is_active: boolean;
  totp_enabled: boolean;
  prompts_today: number;
}

function Users({ isAdmin }: { isAdmin: boolean }) {
  const [data, setData] = useState<Page<AdminUser> | null>(null);
  const [search, setSearch] = useState("");

  const load = (q: string) =>
    api<Page<AdminUser>>(`/admin/users${q ? `?search=${encodeURIComponent(q)}` : ""}`).then(setData);
  useEffect(() => {
    void load("");
  }, []);

  async function setRole(id: string, role: string) {
    await api(`/admin/users/${id}`, { method: "PATCH", body: { role } });
    await load(search);
  }
  async function setActive(id: string, is_active: boolean) {
    await api(`/admin/users/${id}`, { method: "PATCH", body: { is_active } });
    await load(search);
  }

  if (!data) return <Spinner />;
  return (
    <div className="space-y-3">
      <form
        onSubmit={(e) => {
          e.preventDefault();
          void load(search);
        }}
        className="flex gap-2"
      >
        <input className="input" placeholder="Search e-mail…" value={search} onChange={(e) => setSearch(e.target.value)} />
        <button className="btn-ghost">Search</button>
      </form>
      <div className="space-y-2">
        {data.items.map((u) => (
          <div key={u.id} className="card flex flex-wrap items-center justify-between gap-2">
            <div>
              <div className="font-medium">{u.email}</div>
              <div className="text-xs text-muted">
                {u.role} · {u.prompts_today} prompts today {u.is_active ? "" : "· disabled"}
              </div>
            </div>
            {isAdmin && (
              <div className="flex items-center gap-2">
                <select className="input" value={u.role} onChange={(e) => setRole(u.id, e.target.value)}>
                  <option value="student">student</option>
                  <option value="instructor">instructor</option>
                  <option value="admin">admin</option>
                </select>
                <button className="btn-ghost text-sm" onClick={() => setActive(u.id, !u.is_active)}>
                  {u.is_active ? "Disable" : "Enable"}
                </button>
              </div>
            )}
          </div>
        ))}
      </div>
    </div>
  );
}

interface StatsOut {
  users: number;
  users_with_access: number;
  prompts_today: number;
  prompts_by_day: { day: string; count: number }[];
  prompts_by_feature: Record<string, number>;
}

function Stats() {
  const [stats, setStats] = useState<StatsOut | null>(null);
  useEffect(() => {
    api<StatsOut>("/admin/stats").then(setStats).catch(() => undefined);
  }, []);
  if (!stats) return <Spinner />;
  const max = Math.max(1, ...stats.prompts_by_day.map((d) => d.count));
  return (
    <div className="space-y-4">
      <div className="grid gap-3 sm:grid-cols-3">
        <Stat label="Users" value={stats.users} />
        <Stat label="With access" value={stats.users_with_access} />
        <Stat label="Prompts today" value={stats.prompts_today} />
      </div>
      <div className="card">
        <div className="mb-2 text-sm font-medium text-muted">Prompts per day</div>
        <div className="flex h-32 items-end gap-1">
          {stats.prompts_by_day.map((d) => (
            <div key={d.day} className="flex flex-1 flex-col items-center gap-1" title={`${d.day}: ${d.count}`}>
              <div className="w-full rounded-t bg-accent" style={{ height: `${(d.count / max) * 100}%` }} />
              <span className="text-[10px] text-muted">{d.day.slice(5)}</span>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}

function Stat({ label, value }: { label: string; value: number }) {
  return (
    <div className="card">
      <div className="text-2xl font-semibold">{value}</div>
      <div className="text-sm text-muted">{label}</div>
    </div>
  );
}

interface AuditEntry {
  id: string;
  actor_email: string | null;
  action: string;
  target: string | null;
  created_at: string;
}

function Audit() {
  const [data, setData] = useState<Page<AuditEntry> | null>(null);
  useEffect(() => {
    api<Page<AuditEntry>>("/admin/audit").then(setData).catch(() => undefined);
  }, []);
  if (!data) return <Spinner />;
  return (
    <div className="space-y-1 text-sm">
      {data.items.map((e) => (
        <div key={e.id} className="flex flex-wrap gap-2 border-b border-border py-1.5">
          <span className="text-muted">{new Date(e.created_at).toLocaleString()}</span>
          <span className="font-mono">{e.action}</span>
          <span>{e.actor_email ?? "—"}</span>
          {e.target && <span className="text-muted">→ {e.target}</span>}
        </div>
      ))}
    </div>
  );
}
