import { apiFetch } from "./apiClient";
import type { Incident, PhotoReport } from "../types/api";

export function getIncidents(): Promise<Incident[]> {
  return apiFetch<Incident[]>("/api/incidents");
}

export function getPhotoReports(incidentId: string): Promise<PhotoReport[]> {
  return apiFetch<PhotoReport[]>(`/api/photo-reports/${encodeURIComponent(incidentId)}`);
}

