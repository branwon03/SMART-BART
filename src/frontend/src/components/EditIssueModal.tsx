"use client";

import { useMemo, useState } from "react";
import type { Incident } from "../types/api";
import { MAINTENANCE_DISCIPLINES } from "../lib/disciplines";
import { updateIncident } from "../lib/incidents";

const PRIORITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
type IssuePriority = (typeof PRIORITY_OPTIONS)[number];
const STATUS_OPTIONS = ["New", "In Progress", "Closed"] as const;

type EditIssueModalProps = {
  incident: Incident;
  onSave: (updated: Incident) => void;
  onCancel: () => void;
};

export function EditIssueModal({ incident, onSave, onCancel }: EditIssueModalProps) {
  const [priority, setPriority] = useState<IssuePriority>(() =>
    normalizePriority(incident.issue_priority),
  );
  const [status, setStatus] = useState(
    () => normalizeStatus(incident.status),
  );
  const options = useMemo(
    () => disciplineSelectOptions(incident.discipline),
    [incident.discipline],
  );
  const [discipline, setDiscipline] = useState(() =>
    initialDiscipline(incident.discipline),
  );
  const [title, setTitle] = useState(() => incident.vlm_summary ?? "");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    const trimmedTitle = title.trim();
    if (!trimmedTitle) {
      setError("Title cannot be empty");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      const updated = await updateIncident(incident.incident_id, {
        issue_priority: priority,
        status,
        discipline,
        vlm_summary: trimmedTitle,
      });
      console.log("Incident updated:", updated);
      onSave({ ...updated, vlm_summary: trimmedTitle });
    } catch (err) {
      console.error("Failed to update incident:", err);
      setError(err instanceof Error ? err.message : "Update failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onCancel} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-black shadow-2xl w-full max-w-md p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-xl font-black mb-6">Edit Issue</h2>

          <label className="block mb-4">
            <span className="text-sm font-bold text-gray-700">Title</span>
            <input
              type="text"
              value={title}
              onChange={(e) => setTitle(e.target.value)}
              placeholder="Incident title"
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            />
          </label>

          <label className="block mb-4">
            <span className="text-sm font-bold text-gray-700">Priority</span>
            <select
              value={priority}
              onChange={(e) =>
                setPriority(e.target.value as IssuePriority)
              }
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </label>

          <label className="block mb-4">
            <span className="text-sm font-bold text-gray-700">Status</span>
            <select
              value={status}
              onChange={(e) => setStatus(e.target.value)}
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>{opt}</option>
              ))}
            </select>
          </label>

          <label className="block mb-6">
            <span className="text-sm font-bold text-gray-700">
              Discipline (redirect)
            </span>
            <select
              value={discipline}
              onChange={(e) => setDiscipline(e.target.value)}
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              {options.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>

          {error && (
            <p className="text-red-600 text-sm font-semibold mb-4">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={saving}
              className="px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleSave}
              disabled={saving}
              className="px-5 py-2 rounded-lg border-2 border-black bg-black text-white font-bold text-sm hover:bg-gray-800 disabled:opacity-50"
            >
              {saving ? "Saving…" : "Save"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}

function normalizePriority(p: string | number | null | undefined): IssuePriority {
  if (p == null) return "LOW";
  const raw = String(p).trim();
  const upper = raw.toUpperCase();
  if ((PRIORITY_OPTIONS as readonly string[]).includes(upper)) {
    return upper as IssuePriority;
  }
  const s = raw.toLowerCase();
  if (/\b(critical)\b/.test(s) || s === "emergency" || /\b(severe)\b/.test(s)) {
    return "CRITICAL";
  }
  if (/\b(high)\b/.test(s) || /\b(urgent)\b/.test(s) || s === "1" || p === 1) {
    return "HIGH";
  }
  if (/\b(medium)\b/.test(s)) return "MEDIUM";
  if (/\b(low)\b/.test(s) || s === "standard" || s === "0" || p === 0) {
    return "LOW";
  }
  return "LOW";
}

function normalizeStatus(s: string | null | undefined): string {
  if (!s) return "New";
  const match = STATUS_OPTIONS.find(
    (opt) => opt.toLowerCase() === s.trim().toLowerCase(),
  );
  return match ?? "New";
}

function disciplineSelectOptions(current: string | null | undefined): string[] {
  const list = [...MAINTENANCE_DISCIPLINES];
  const d = current?.trim();
  if (
    d &&
    !list.some((opt) => opt.toLowerCase() === d.toLowerCase())
  ) {
    return [d, ...list];
  }
  return list;
}

function initialDiscipline(current: string | null | undefined): string {
  const d = current?.trim();
  if (!d) return MAINTENANCE_DISCIPLINES[0];
  const match = MAINTENANCE_DISCIPLINES.find(
    (opt) => opt.toLowerCase() === d.toLowerCase(),
  );
  return match ?? d;
}
