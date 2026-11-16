// Small client for the backend API (API-01..API-16 are added during implementation).

const BASE = "/api";
let token: string | null = null;

export function setToken(value: string | null): void {
  token = value;
}

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(BASE + path, {
    headers: token ? { Authorization: `Bearer ${token}` } : {},
  });
  if (!response.ok) {
    throw new Error(`HTTP ${response.status}`);
  }
  return (await response.json()) as T;
}
