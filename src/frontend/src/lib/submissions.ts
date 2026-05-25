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
 * Submit an incident report to POST /api/submissions.
 *
 * Images must be data-URL strings (as stored in ReportContext.images).
 * Priority is accepted but not sent — the processor determines priority via Gemini.
 */
export async function submitReport(params: {
  images: string[];
  rawFiles?: File[];
  description: string;
  priority: string;
  location: string;
  fullName: string;
  contact: string;
}): Promise<SubmissionResult> {
  const form = new FormData();
  const useRawFiles =
    params.location === "Assign-Me-Via-Geolocation" &&
    params.rawFiles &&
    params.rawFiles.length > 0;

  if (useRawFiles) {
    params.rawFiles!.forEach((file) => {
      form.append("media", file, file.name);
    });
  } else {
    params.images.forEach((dataUrl, i) => {
      form.append("media", dataUrlToFile(dataUrl, `image-${i}.jpg`));
    });
  }

  form.append("description", params.description);
  form.append("photo_location_id", params.location);
  form.append("reporter_name", params.fullName);
  form.append("reporter_contact", params.contact);

  const res = await fetch(`${API_BASE_URL}/api/submissions`, {
    method: "POST",
    body: form,
  });

  if (!res.ok) {
    const body = await res.text().catch(() => undefined);
    throw new Error(`Submission failed (${res.status}): ${body ?? ""}`);
  }

  return res.json() as Promise<SubmissionResult>;
}
