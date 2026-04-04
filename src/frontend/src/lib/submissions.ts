import { API_BASE_URL } from "./config";
import type { SubmissionResult } from "../types/api";

/**
 * Convert a data URL string (e.g. from canvas.toDataURL()) to a File object
 * that can be appended to FormData.
 */
export function dataUrlToFile(dataUrl: string, filename: string): File {
  const [header, data] = dataUrl.split(",");
  const mime = header.match(/:(.*?);/)?.[1] ?? "image/jpeg";
  const bytes = atob(data);
  const buffer = new Uint8Array(bytes.length);
  for (let i = 0; i < bytes.length; i++) {
    buffer[i] = bytes.charCodeAt(i);
  }
  return new File([buffer], filename, { type: mime });
}

/**
 * Submit an incident report to POST /submissions.
 *
 * Images must be data-URL strings (as stored in ReportContext.images).
 * Priority must be one of the frontend labels: "low" | "high" | "emergency" | "unknown".
 */
export async function submitReport(params: {
  images: string[];
  description: string;
  priority: string;
}): Promise<SubmissionResult> {
  const form = new FormData();

  params.images.forEach((dataUrl, i) => {
    form.append("media", dataUrlToFile(dataUrl, `image-${i}.jpg`));
  });

  form.append("description", params.description);

  if (params.priority) {
    form.append("user_priority", params.priority);
  }

  const res = await fetch(`${API_BASE_URL}/submissions`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => undefined);
    throw new Error(`Submission failed (${res.status}): ${body ?? ""}`);
  }

  return res.json() as Promise<SubmissionResult>;
}
