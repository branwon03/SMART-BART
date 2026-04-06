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
  let res: Response;
  try {
    res = await fetch(url, init);
  } catch (err) {
    const target = url.startsWith("http") ? url : `${typeof window !== "undefined" ? window.location.origin : ""}${url}`;
    const hint =
      API_BASE_URL === ""
        ? " Start the FastAPI app on port 8000 (Next.js proxies /api to it)."
        : " Check NEXT_PUBLIC_API_BASE_URL and that the API is reachable.";
    throw new Error(`Failed to fetch ${target}.${hint}`, { cause: err });
  }

  if (!res.ok) {
    const body = await res.text().catch(() => undefined);
    throw new ApiError(`Request failed: ${res.status}`, res.status, body);
  }

  // FastAPI returns JSON for these endpoints
  return (await res.json()) as T;
}

