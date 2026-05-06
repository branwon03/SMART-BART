/**
 * Aligns with backend / EditIssueModal: LOW | MEDIUM | HIGH | CRITICAL.
 * Legacy strings (Standard, Emergency, etc.) normalize the same way as the modal.
 */

export const ISSUE_PRIORITY_LEVELS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
export type IssuePriorityLevel = (typeof ISSUE_PRIORITY_LEVELS)[number];

const PRIORITY_DOT_BASE = "h-1.5 w-10 rounded-full";

const PRIORITY_DOT_CLASSES: Record<IssuePriorityLevel, string> = {
  LOW: "bg-gray-400",
  MEDIUM: "bg-yellow-400",
  HIGH: "bg-orange-500 shadow-[0_0_8px_rgba(249,115,22,0.35)]",
  CRITICAL: "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)]",
};

/** Same rules as EditIssueModal `normalizePriority`. */
export function normalizeIssuePriority(
  p: string | number | null | undefined,
): IssuePriorityLevel {
  if (p == null) return "LOW";
  const raw = String(p).trim();
  const upper = raw.toUpperCase();
  if ((ISSUE_PRIORITY_LEVELS as readonly string[]).includes(upper)) {
    return upper as IssuePriorityLevel;
  }
  const s = raw.toLowerCase();
  if (/\b(critical)\b/.test(s) || s === "emergency" || /\b(severe)\b/.test(s)) {
    return "CRITICAL";
  }
  if (/\b(high)\b/.test(s) || /\b(urgent)\b/.test(s) || s === "1" || p === 1) {
    return "HIGH";
  }
  if (/\b(medium)\b/.test(s)) return "MEDIUM";
  if (/\b(low)\b/.test(s) || s === "standard" || s === "0" || p === 0) {
    return "LOW";
  }
  return "LOW";
}

export function issuePriorityDotClass(level: IssuePriorityLevel): string {
  return `${PRIORITY_DOT_BASE} ${PRIORITY_DOT_CLASSES[level]}`;
}

export function issuePriorityDotClassFromRaw(
  p: string | number | null | undefined,
): string {
  return issuePriorityDotClass(normalizeIssuePriority(p));
}

/** True when priority is HIGH or CRITICAL (after normalization). */
export function isHighPriority(p: string | number | null | undefined): boolean {
  const level = normalizeIssuePriority(p);
  return level === "HIGH" || level === "CRITICAL";
}
