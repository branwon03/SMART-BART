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
  fields: {
    issue_priority?: string;
    status?: string;
    discipline?: string;
    vlm_summary?: string;
    location_id?: string | null;
  },
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

export function mergePhotos(
  targetIncidentId: string,
  evidenceIds: string[],
): Promise<{ merged_count: number }> {
  return apiFetch<{ merged_count: number }>(
    `/api/incidents/${encodeURIComponent(targetIncidentId)}/merge-photos`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ evidence_ids: evidenceIds }),
    },
  );
}
export function splitIncident(
  incidentId: string,
  params: {
    evidence_ids: string[];
    title: string;
    description?: string | null;
    discipline?: string | null;
  },
): Promise<Incident> {
  const body: {
    evidence_ids: string[];
    title: string;
    description?: string;
    discipline?: string;
  } = {
    evidence_ids: params.evidence_ids,
    title: params.title,
  };
  if (params.description !== undefined && params.description !== null && params.description.trim() !== "") {
    body.description = params.description;
  }
  if (
    params.discipline !== undefined &&
    params.discipline !== null &&
    params.discipline.trim() !== ""
  ) {
    body.discipline = params.discipline.trim();
  }

  return apiFetch<Incident>(
    `/api/incidents/${encodeURIComponent(incidentId)}/split`,
    {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(body),
    },
  );
}

