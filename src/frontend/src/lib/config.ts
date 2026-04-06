// Empty = same-origin /api/* (see rewrites in next.config). Override for a direct API host (e.g. Docker).
export const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_BASE_URL?.replace(/\/+$/, "") ?? "";

