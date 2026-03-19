import { apiFetch } from "./apiClient";
import type { SubmissionResult } from "../types/api";

export async function createSubmission(params: {
  files: File[];
  description?: string;
}): Promise<SubmissionResult> {
  const form = new FormData();
  if (params.description?.trim()) form.append("description", params.description.trim());
  for (const f of params.files) form.append("media", f);

  return apiFetch<SubmissionResult>("/submissions", {
    method: "POST",
    body: form,
  });
}

