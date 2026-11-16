// Client for the backend API (API-01..API-16 are added release by release).
// The JWT is kept in sessionStorage: it survives a page refresh and is removed when the tab closes.
// Its validity is 60 minutes on the server (SEC-03).

const BASE = "/api";
const TOKEN_KEY = "mahwar.token";
const USER_KEY = "mahwar.user";

export type RoleCode = "PROJECT_MANAGER" | "TEAM_MEMBER" | "SYSTEM_ADMIN" | "PLANNER";

export interface CurrentUser {
  user_id: number;
  username: string;
  display_alias: string;
  role_code: RoleCode;
  role_name_ar: string;
}

export interface FieldError {
  field: string;
  message: string;
}

/** Error body {code, message, fields} returned by the backend (API_Spec, Conventions). */
export class ApiError extends Error {
  constructor(
    public status: number,
    public code: string,
    message: string,
    public fields: FieldError[] = [],
  ) {
    super(message);
  }

  fieldMessage(field: string): string | undefined {
    return this.fields.find((f) => f.field === field)?.message;
  }
}

export const CONNECTION_LOST = "انقطع الاتصال بالخادم، لم تُفقد البيانات المدخلة";

let onUnauthorized: (() => void) | null = null;

export function setUnauthorizedHandler(handler: (() => void) | null): void {
  onUnauthorized = handler;
}

function safeGet(key: string): string | null {
  try {
    return sessionStorage.getItem(key);
  } catch {
    return null;
  }
}

function safeSet(key: string, value: string | null): void {
  try {
    if (value === null) sessionStorage.removeItem(key);
    else sessionStorage.setItem(key, value);
  } catch {
    // storage not available: the session simply does not survive a refresh
  }
}

export function getSession(): CurrentUser | null {
  const token = safeGet(TOKEN_KEY);
  const user = safeGet(USER_KEY);
  if (!token || !user) return null;
  try {
    return JSON.parse(user) as CurrentUser;
  } catch {
    return null;
  }
}

export function saveSession(token: string, user: CurrentUser): void {
  safeSet(TOKEN_KEY, token);
  safeSet(USER_KEY, JSON.stringify(user));
}

export function clearSession(): void {
  safeSet(TOKEN_KEY, null);
  safeSet(USER_KEY, null);
}

export async function apiRequest<T>(method: string, path: string, body?: unknown): Promise<T> {
  const token = safeGet(TOKEN_KEY);
  const headers: Record<string, string> = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  if (body !== undefined) headers["Content-Type"] = "application/json";

  let response: Response;
  try {
    response = await fetch(BASE + path, {
      method,
      headers,
      body: body === undefined ? undefined : JSON.stringify(body),
    });
  } catch {
    throw new ApiError(0, "CONNECTION_LOST", CONNECTION_LOST);
  }

  if (response.status === 204) return undefined as T;

  let data: unknown = null;
  try {
    data = await response.json();
  } catch {
    data = null;
  }

  if (!response.ok) {
    const err = (data ?? {}) as { code?: string; message?: string; fields?: FieldError[] };
    const apiError = new ApiError(
      response.status,
      err.code ?? "HTTP_ERROR",
      err.message ?? "تعذر حفظ البيانات، أعد المحاولة",
      err.fields ?? [],
    );
    if (response.status === 401 && path !== "/auth/login" && onUnauthorized) onUnauthorized();
    throw apiError;
  }
  return data as T;
}

export const apiGet = <T,>(path: string) => apiRequest<T>("GET", path);
export const apiPost = <T,>(path: string, body?: unknown) => apiRequest<T>("POST", path, body ?? {});
export const apiPatch = <T,>(path: string, body: unknown) => apiRequest<T>("PATCH", path, body);
export const apiDelete = (path: string) => apiRequest<void>("DELETE", path);
