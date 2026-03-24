import { API_BASE_URL } from "./config";

export class ApiError extends Error {
  status: number;
  body?: string;

  constructor(message: string, status: number, body?: string) {
    super(message);
    this.name = "ApiError";
    this.status = status;
    this.body = body;
  }
}

export async function apiFetch<T>(
  path: string,
  init?: RequestInit,
): Promise<T> {
  const url = path.startsWith("http") ? path : `${API_BASE_URL}${path}`;
  const res = await fetch(url, init);

  if (!res.ok) {
    const body = await res.text().catch(() => undefined);
    throw new ApiError(`Request failed: ${res.status}`, res.status, body);
  }

  // FastAPI returns JSON for these endpoints
  return (await res.json()) as T;
}

