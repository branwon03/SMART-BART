export type Incident = {
  incident_id: string;
  status?: string | null;
  issue_priority?: string | number | null;
  discipline?: string | null;
  vlm_summary?: string | null;
  location_id?: string | null;
  created_at?: string | null;
  last_report_at?: string | null;
};

export type PhotoReport = {
  evidence_id: string;
  incident_id: string;
  image_url?: string | null;
  embedding?: string | null;
  submitted_at?: string | null;
  user_context?: string | null;
  found_priority?: string | null;
  vlm_summary?: string | null;
  photo_report_discipline?: string | null;
  reporter_name?: string | null;
  reporter_contact?: string | null;
};

export type SubmissionResult = {
  incident_id: string;
  description: string | null;
  timestamp: string;
};

