/** Typed fetch wrapper: one origin, CSRF header on unsafe calls, friendly errors, SSE. */

const CSRF_COOKIE = "csrf_token";
const CSRF_HEADER = "X-CSRF-Token";
const SAFE = new Set(["GET", "HEAD", "OPTIONS"]);

export class ApiError extends Error {
  constructor(
    readonly status: number,
    readonly code: string,
    message: string,
  ) {
    super(message);
  }
}

function readCookie(name: string): string | null {
  const match = document.cookie.match(new RegExp(`(?:^|; )${name}=([^;]*)`));
  return match ? decodeURIComponent(match[1]) : null;
}

async function ensureCsrf(): Promise<string> {
  const existing = readCookie(CSRF_COOKIE);
  if (existing) return existing;
  const res = await fetch("/api/auth/csrf", { credentials: "same-origin" });
  const data = (await res.json()) as { csrf_token: string };
  return data.csrf_token;
}

async function toError(res: Response): Promise<ApiError> {
  let code = "error";
  let message = `Request failed (${res.status}).`;
  try {
    const body = (await res.json()) as { error?: { code: string; message: string } };
    if (body.error) {
      code = body.error.code;
      message = body.error.message;
    }
  } catch {
    /* non-JSON error body */
  }
  return new ApiError(res.status, code, message);
}

export async function api<T>(
  path: string,
  options: { method?: string; body?: unknown; signal?: AbortSignal } = {},
): Promise<T> {
  const method = options.method ?? "GET";
  const headers: Record<string, string> = {};
  let body: BodyInit | undefined;
  if (options.body instanceof FormData) {
    body = options.body;
  } else if (options.body !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(options.body);
  }
  if (!SAFE.has(method)) headers[CSRF_HEADER] = await ensureCsrf();

  const res = await fetch(`/api${path}`, {
    method,
    headers,
    body,
    credentials: "same-origin",
    signal: options.signal,
  });
  if (!res.ok) throw await toError(res);
  if (res.status === 204) return undefined as T;
  return (await res.json()) as T;
}

export interface SseEvent {
  event: string;
  data: unknown;
}

/** POST a request and yield parsed server-sent events as they arrive. */
export async function* sse(
  path: string,
  body: unknown,
  signal?: AbortSignal,
): AsyncGenerator<SseEvent> {
  const res = await fetch(`/api${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json", [CSRF_HEADER]: await ensureCsrf() },
    body: JSON.stringify(body),
    credentials: "same-origin",
    signal,
  });
  if (!res.ok) throw await toError(res);
  if (!res.body) return;

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";
  while (true) {
    const { value, done } = await reader.read();
    if (done) break;
    buffer += decoder.decode(value, { stream: true });
    const blocks = buffer.split("\n\n");
    buffer = blocks.pop() ?? "";
    for (const block of blocks) {
      let event = "message";
      let data = "";
      for (const line of block.split("\n")) {
        if (line.startsWith("event: ")) event = line.slice(7);
        else if (line.startsWith("data: ")) data = line.slice(6);
      }
      if (data) yield { event, data: JSON.parse(data) as unknown };
    }
  }
}
