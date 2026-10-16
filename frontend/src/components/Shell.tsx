/** The authenticated app shell: sidebar navigation, quota badge, and theme toggle. */

import { NavLink, Outlet, useNavigate } from "react-router-dom";
import { useState } from "react";

import { useAuth } from "@/auth/AuthContext";

const NAV = [
  { to: "/", label: "Dashboard", end: true },
  { to: "/playground", label: "Playground", access: true },
  { to: "/engage", label: "Engage", access: true },
  { to: "/reservation", label: "Reservation", access: true },
  { to: "/skills-lab", label: "Skills Lab", access: true },
  { to: "/learn", label: "Learn" },
];

function toggleTheme() {
  const root = document.documentElement;
  const next = root.dataset.theme === "light" ? "dark" : "light";
  root.dataset.theme = next;
  try {
    localStorage.setItem("theme", next);
  } catch {
    /* ignore */
  }
}

export function Shell() {
  const { me, logout } = useAuth();
  const navigate = useNavigate();
  const [open, setOpen] = useState(false);
  const hasAccess = me?.access.has_access ?? false;
  const isStaff = me?.user.role === "admin" || me?.user.role === "instructor";
  const quota = me?.quota;

  return (
    <div className="flex min-h-full flex-col md:flex-row">
      <header className="flex items-center justify-between border-b border-border px-4 py-3 md:hidden">
        <span className="font-semibold">AI Playground</span>
        <button className="btn-ghost" onClick={() => setOpen((v) => !v)}>
          Menu
        </button>
      </header>

      <aside
        className={`${open ? "block" : "hidden"} w-full shrink-0 border-b border-border bg-surface p-4 md:block md:h-screen md:w-60 md:border-b-0 md:border-r`}
      >
        <div className="mb-6 hidden items-center gap-2 md:flex">
          <span className="font-mono text-accent">▚</span>
          <span className="font-semibold">AI Playground</span>
        </div>
        <nav className="flex flex-col gap-1">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.end}
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:bg-bg hover:text-fg"} ${item.access && !hasAccess ? "opacity-50" : ""}`
              }
            >
              {item.label}
              {item.access && !hasAccess && <span className="ml-1 text-xs">🔒</span>}
            </NavLink>
          ))}
          {isStaff && (
            <NavLink
              to="/admin"
              onClick={() => setOpen(false)}
              className={({ isActive }) =>
                `rounded-lg px-3 py-2 text-sm ${isActive ? "bg-accent/15 text-accent" : "text-muted hover:bg-bg hover:text-fg"}`
              }
            >
              Admin
            </NavLink>
          )}
        </nav>

        <div className="mt-6 space-y-2 border-t border-border pt-4 text-sm">
          {quota && quota.limit !== null && (
            <div className="font-mono text-muted">
              {quota.used}/{quota.limit} prompts today
            </div>
          )}
          {quota && quota.limit === null && <div className="font-mono text-ok">unlimited</div>}
          <div className="truncate text-xs text-muted" title={me?.user.email}>
            {me?.user.email}
          </div>
          <div className="flex gap-2">
            <button className="btn-ghost flex-1" onClick={toggleTheme}>
              Theme
            </button>
            <button
              className="btn-ghost flex-1"
              onClick={async () => {
                await logout();
                navigate("/login");
              }}
            >
              Sign out
            </button>
          </div>
        </div>
      </aside>

      <main className="flex-1 overflow-x-hidden px-4 py-6 md:px-8">
        <Outlet />
      </main>
    </div>
  );
}
