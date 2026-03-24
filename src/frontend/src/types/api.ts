export type Incident = {
  incident_id: string;
  status?: string | null;
  issue_priority?: string | number | null;
  discipline?: string | null;
  vlm_summary?: string | null;
  location_id?: string | null;
  created_at?: string | null;
};

export type PhotoReport = {
  evidence_id: string;
  submission_id?: string | null;
  incident_id: string;
  image_url?: string | null;
  embedding?: string | null;
  submitted_at?: string | null;
  user_context?: string | null;
  found_priority?: string | null;
};

export type SubmissionResult = {
  incident_id: string;
  submission_id: string;
  discipline: string;
  description: string | null;
  num_images: number;
  timestamp: string;
};

