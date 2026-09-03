// fetch-обёртка над API zarabotok.
// Prod: панель отдаётся с http://127.0.0.1:8766, поэтому можно ходить same-origin,
// но база задаётся явно (ТЗ). Dev: Vite proxy проксирует /api на 8766.

export class ApiError extends Error {
  status: number;
  path?: string;

  constructor(message: string, status: number, path?: string) {
    super(message);
    this.status = status;
    this.path = path;
  }
}

export const API_BASE: string =
  (import.meta.env.VITE_API_BASE as string | undefined) ??
  (import.meta.env.DEV ? '' : 'http://127.0.0.1:8766');

async function readBody(res: Response): Promise<unknown> {
  const ct = res.headers.get('content-type') || '';
  if (res.status === 204) return {};
  if (ct.includes('application/json')) {
    try {
      return await res.json();
    } catch {
      return null;
    }
  }
  try {
    return await res.text();
  } catch {
    return null;
  }
}

export async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: { 'Content-Type': 'application/json', ...(init?.headers || {}) },
  });
  const data = await readBody(res);
  if (!res.ok) {
    const msg =
      data && typeof data === 'object' && 'error' in (data as Record<string, unknown>)
        ? String((data as Record<string, unknown>).error)
        : `HTTP ${res.status}`;
    throw new ApiError(msg, res.status, (data as { path?: string })?.path);
  }
  return data as T;
}

export function get<T>(path: string): Promise<T> {
  return request<T>(path);
}

export function post<T>(path: string, body?: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: body !== undefined ? JSON.stringify(body) : undefined });
}

export function patch<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'PATCH', body: JSON.stringify(body) });
}