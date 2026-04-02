/**
 * Posted time for evidence rows: D/M/YY and 12-hour clock, e.g. 1/1/26 12:32PM
 */
export function formatPostedAt(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return "—";

  const day = d.getDate();
  const month = d.getMonth() + 1;
  const yy = (d.getFullYear() % 100).toString().padStart(2, "0");

  let hours = d.getHours();
  const minutes = d.getMinutes();
  const ampm = hours >= 12 ? "PM" : "AM";
  hours = hours % 12;
  if (hours === 0) hours = 12;
  const mm = minutes.toString().padStart(2, "0");

  return `${month}/${day}/${yy} @ ${hours}:${mm}${ampm}`;
}
