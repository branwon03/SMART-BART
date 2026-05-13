/** Local calendar: M/D/YY (e.g. 5/12/26). */
export function formatShortDate(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return "—";
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const y = String(d.getFullYear()).slice(-2);
  return `${m}/${day}/${y}`;
}

/** Local calendar + 12h time: M/D/YY h:mm AM/PM. */
export function formatDateTime(isoString: string | null | undefined): string {
  if (!isoString) return "—";
  const d = new Date(isoString);
  if (Number.isNaN(d.getTime())) return "—";
  const m = d.getMonth() + 1;
  const day = d.getDate();
  const y = String(d.getFullYear()).slice(-2);
  const hours = d.getHours();
  const mins = String(d.getMinutes()).padStart(2, "0");
  const ampm = hours >= 12 ? "PM" : "AM";
  const h12 = hours % 12 || 12;
  return `${m}/${day}/${y} ${h12}:${mins} ${ampm}`;
}
