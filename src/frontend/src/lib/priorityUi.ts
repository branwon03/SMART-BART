/**
 * Backend stores VLM-derived priority as text (e.g. "Standard") or occasionally numeric-like strings.
 * Use this for traffic-light styling instead of comparing to the number 1 only.
 */
export function isHighPriority(p: string | number | null | undefined): boolean {
  if (p === 1) return true;
  if (p == null) return false;
  const s = String(p).trim().toLowerCase();
  if (s === "1") return true;
  return /\b(emergency|critical|severe|urgent|high)\b/.test(s);
}
