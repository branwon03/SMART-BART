/** Compact incident id for UI: first 8 chars + ellipsis when longer than 8. */
export function displayCompactIncidentId(incidentId: string): string {
  if (!incidentId) return "";
  if (incidentId.length <= 8) return incidentId;
  return `${incidentId.slice(0, 8)}…`;
}
