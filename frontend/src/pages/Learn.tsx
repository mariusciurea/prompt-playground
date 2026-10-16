import { useEffect, useState } from "react";

import { api } from "@/api/client";
import type { LearnIndex } from "@/api/types";
import { SafeMarkdown, Spinner } from "@/components/ui";

interface Article {
  slug: string;
  title: string;
  summary: string;
  body: string;
}

export function Learn() {
  const [index, setIndex] = useState<LearnIndex | null>(null);
  const [active, setActive] = useState<Article | null>(null);

  useEffect(() => {
    api<LearnIndex>("/learn").then(setIndex).catch(() => undefined);
  }, []);

  async function open(slug: string) {
    setActive(await api<Article>(`/learn/${slug}`));
  }

  if (!index) return <Spinner />;

  return (
    <div className="mx-auto max-w-5xl">
      <h1 className="mb-1 text-2xl font-semibold">Learn</h1>
      <p className="mb-4 text-sm text-muted">
        Security best practices for prompting and AI agents.
      </p>
      <div className="grid gap-6 md:grid-cols-[18rem_1fr]">
        <nav className="space-y-2">
          {index.articles.map((a) => (
            <button
              key={a.slug}
              onClick={() => open(a.slug)}
              className={`w-full rounded-lg border border-border p-3 text-left text-sm ${active?.slug === a.slug ? "border-accent" : "hover:bg-surface"}`}
            >
              <div className="font-medium">{a.title}</div>
              <div className="text-xs text-muted">{a.summary}</div>
            </button>
          ))}
          <a
            href={index.prompting_guide_url}
            target="_blank"
            rel="noopener noreferrer"
            className="block rounded-lg border border-border p-3 text-sm text-accent hover:bg-surface"
          >
            Prompting Guide ↗
          </a>
        </nav>
        <article className="card min-h-[20rem]">
          {active ? (
            <>
              <h2 className="mb-3 text-xl font-semibold">{active.title}</h2>
              <SafeMarkdown>{active.body}</SafeMarkdown>
            </>
          ) : (
            <p className="text-sm text-muted">Pick an article to start reading.</p>
          )}
        </article>
      </div>
    </div>
  );
}
