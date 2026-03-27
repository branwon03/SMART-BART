import {
  differenceInHours,
  differenceInMilliseconds,
  differenceInMinutes,
} from "date-fns";

const MS_DAY = 24 * 60 * 60 * 1000;

/**
 * Human-readable elapsed time from an ISO timestamp to a reference instant.
 * Tiers: minutes (<60m) → hours (1–23 hr) → days (1–6 days) → weeks (≥7d & <30d) → months (<365d) → years.
 *
 * Day counts use exact 24h periods (`floor(ms / MS_DAY)`), not `differenceInDays`, so buckets match
 * wall-clock duration and stay consistent across DST (date-fns `differenceInDays` is calendar-based).
 */
export function formatElapsedSince(
  isoString: string | null | undefined,
  referenceTime: Date,
): string {
  if (!isoString) return "0m";
  const start = new Date(isoString);
  if (Number.isNaN(start.getTime())) return "0m";

  const ms = differenceInMilliseconds(referenceTime, start);
  if (ms <= 0) return "0m";

  const totalMinutes = differenceInMinutes(referenceTime, start);
  const totalHours = differenceInHours(referenceTime, start);
  const totalDays = Math.floor(ms / MS_DAY);

  if (totalMinutes < 60) {
    return `${totalMinutes}m`;
  }
  if (totalHours < 24) {
    return `${totalHours} hr`;
  }
  if (totalDays < 7) {
    return totalDays === 1 ? "1 day" : `${totalDays} days`;
  }
  if (totalDays < 30) {
    const weeks = Math.floor(totalDays / 7);
    return weeks === 1 ? "1 week" : `${weeks} weeks`;
  }
  if (totalDays < 365) {
    const months = Math.floor(totalDays / 30);
    return months === 1 ? "1 month" : `${months} months`;
  }
  const years = Math.floor(totalDays / 365);
  return years === 1 ? "1 year" : `${years} years`;
}
