import { apiFetch } from "./apiClient";
import type { Incident, PhotoReport } from "../types/api";

export function getIncidents(): Promise<Incident[]> {
  return apiFetch<Incident[]>("/api/incidents");
}

export function getPhotoReports(incidentId: string): Promise<PhotoReport[]> {
  return apiFetch<PhotoReport[]>(`/api/photo-reports/${encodeURIComponent(incidentId)}`);
}

export function updateIncident(
  incidentId: string,
  fields: { issue_priority?: string; status?: string; discipline?: string },
): Promise<Incident> {
  return apiFetch<Incident>(
    `/api/incidents/${encodeURIComponent(incidentId)}`,
    {
      method: "PUT",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(fields),
    },
  );
}

export function deleteIncident(
  incidentId: string,
): Promise<{ deleted_incident_id: string }> {
  return apiFetch<{ deleted_incident_id: string }>(
    `/api/incidents/${encodeURIComponent(incidentId)}`,
    { method: "DELETE" },
  );
}

