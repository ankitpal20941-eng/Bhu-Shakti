import { useSession } from "../store/session";

export const API_BASE = import.meta.env.VITE_API_BASE ?? "";

export class ApiError extends Error {
  status: number;
  code: string;
  requestId?: string;
  details?: unknown;

  constructor(status: number, message: string, code = "error", requestId?: string, details?: unknown) {
    super(message);
    this.status = status;
    this.code = code;
    this.requestId = requestId;
    this.details = details;
  }
}

type Options = Omit<RequestInit, "body"> & { json?: unknown; body?: BodyInit | null };

export async function api<T>(path: string, options: Options = {}): Promise<T> {
  const { json, headers, ...rest } = options;
  const token = useSession.getState().token;
  const finalHeaders = new Headers(headers);
  if (json !== undefined) finalHeaders.set("Content-Type", "application/json");
  if (token) finalHeaders.set("Authorization", `Bearer ${token}`);

  const response = await fetch(`${API_BASE}${path}`, {
    ...rest,
    headers: finalHeaders,
    credentials: "include",
    body: json !== undefined ? JSON.stringify(json) : rest.body,
  });

  if (response.status === 401 && !path.startsWith("/api/v1/auth/login") && !path.startsWith("/api/v1/public")) {
    useSession.getState().clear();
  }

  const contentType = response.headers.get("content-type") ?? "";
  if (!response.ok) {
    let message = response.statusText || "Request failed";
    let code = `http_${response.status}`;
    let requestId: string | undefined;
    let details: unknown;
    if (contentType.includes("application/json")) {
      const body = await response.json().catch(() => null);
      message = body?.error?.message ?? message;
      code = body?.error?.code ?? code;
      requestId = body?.request_id;
      details = body?.error?.details;
    }
    throw new ApiError(response.status, message, code, requestId, details);
  }
  if (response.status === 204) return undefined as T;
  if (contentType.includes("application/json")) return (await response.json()) as T;
  return (await response.text()) as unknown as T;
}

export async function downloadFile(path: string, filename: string): Promise<void> {
  const token = useSession.getState().token;
  const response = await fetch(`${API_BASE}${path}`, {
    credentials: "include",
    headers: token ? { Authorization: `Bearer ${token}` } : undefined,
  });
  if (!response.ok) throw new ApiError(response.status, "Export failed");
  const blob = await response.blob();
  const url = URL.createObjectURL(blob);
  const anchor = document.createElement("a");
  anchor.href = url;
  anchor.download = filename;
  anchor.click();
  URL.revokeObjectURL(url);
}

export function qs(params: Record<string, string | number | boolean | undefined | null>): string {
  const search = new URLSearchParams();
  for (const [key, value] of Object.entries(params)) {
    if (value !== undefined && value !== null && value !== "") search.set(key, String(value));
  }
  const text = search.toString();
  return text ? `?${text}` : "";
}
