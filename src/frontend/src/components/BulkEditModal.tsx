"use client";

import { useState } from "react";
import type { Incident } from "../types/api";
import { updateIncident } from "../lib/incidents";
import { displayCompactIncidentId } from "../lib/formatIncidentId";
import { MAINTENANCE_DISCIPLINES } from "../lib/disciplines";

const PRIORITY_OPTIONS = ["LOW", "MEDIUM", "HIGH", "CRITICAL"] as const;
type BulkPriority = (typeof PRIORITY_OPTIONS)[number];
const STATUS_OPTIONS = ["New", "In Progress", "Closed"] as const;

type BulkEditModalProps = {
  incidents: Incident[];
  onApplied: (updated: Incident[]) => void;
  onClose: () => void;
};

export function BulkEditModal({ incidents, onApplied, onClose }: BulkEditModalProps) {
  const [priorityChange, setPriorityChange] = useState<BulkPriority | "">("");
  const [statusChange, setStatusChange] = useState<(typeof STATUS_OPTIONS)[number] | "">("");
  const [disciplineChange, setDisciplineChange] = useState<string>("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultNote, setResultNote] = useState<string | null>(null);

  async function handleApply() {
    const body: { issue_priority?: string; status?: string; discipline?: string } = {};
    if (priorityChange) body.issue_priority = priorityChange;
    if (statusChange) body.status = statusChange;
    if (disciplineChange) body.discipline = disciplineChange;
    if (Object.keys(body).length === 0) {
      setError("Pick at least priority, status, or discipline to change.");
      return;
    }

    setBusy(true);
    setError(null);
    setResultNote(null);
    try {
      const results = await Promise.allSettled(
        incidents.map((inc) => updateIncident(inc.incident_id, body)),
      );
      const updated: Incident[] = [];
      const failedIds: string[] = [];
      results.forEach((r, i) => {
        if (r.status === "fulfilled") {
          updated.push({ ...incidents[i], ...r.value });
        } else {
          failedIds.push(displayCompactIncidentId(incidents[i].incident_id));
        }
      });

      if (updated.length > 0) {
        onApplied(updated);
      }

      if (failedIds.length === 0) {
        setResultNote(`Updated ${updated.length} incident${updated.length === 1 ? "" : "s"}.`);
      } else {
        setError(`Updated ${updated.length}; failed ${failedIds.length}: ${failedIds.join(", ")}`);
        if (updated.length > 0) {
          setResultNote("Partial success — fix failures and retry if needed.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk update failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-black shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-xl font-black mb-2">Bulk edit incidents</h2>
          <p className="text-sm text-gray-600 mb-4">
            Applying changes to <strong>{incidents.length}</strong> selected incident
            {incidents.length === 1 ? "" : "s"} for this discipline tab.
          </p>

          <div className="rounded-lg border border-gray-200 bg-gray-50 max-h-40 overflow-y-auto mb-4 text-sm divide-y divide-gray-200">
            {incidents.map((inc) => (
              <div key={inc.incident_id} className="px-3 py-2">
                <div className="font-semibold text-gray-900 truncate">
                  {inc.vlm_summary?.trim() || "(Untitled)"}
                </div>
                <div className="font-mono text-xs text-gray-500">
                  {displayCompactIncidentId(inc.incident_id)}
                </div>
              </div>
            ))}
          </div>

          <label className="block mb-3">
            <span className="text-sm font-bold text-gray-700">New priority</span>
            <select
              value={priorityChange}
              onChange={(e) =>
                setPriorityChange(e.target.value === "" ? "" : (e.target.value as BulkPriority))
              }
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              <option value="">— No change —</option>
              {PRIORITY_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>

          <label className="block mb-3">
            <span className="text-sm font-bold text-gray-700">New status</span>
            <select
              value={statusChange}
              onChange={(e) =>
                setStatusChange(
                  e.target.value === "" ? "" : (e.target.value as (typeof STATUS_OPTIONS)[number]),
                )
              }
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              <option value="">— No change —</option>
              {STATUS_OPTIONS.map((opt) => (
                <option key={opt} value={opt}>
                  {opt}
                </option>
              ))}
            </select>
          </label>

          <label className="block mb-4">
            <span className="text-sm font-bold text-gray-700">New discipline</span>
            <select
              value={disciplineChange}
              onChange={(e) => setDisciplineChange(e.target.value)}
              className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
            >
              <option value="">— No change —</option>
              {MAINTENANCE_DISCIPLINES.map((d) => (
                <option key={d} value={d}>
                  {d}
                </option>
              ))}
            </select>
          </label>

          {error && <p className="text-red-600 text-sm font-semibold mb-2">{error}</p>}
          {resultNote && <p className="text-green-700 text-sm font-semibold mb-2">{resultNote}</p>}

          <div className="flex justify-end gap-3 mt-auto pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
            >
              Close
            </button>
            <button
              type="button"
              onClick={() => void handleApply()}
              disabled={busy}
              className="px-5 py-2 rounded-lg border-2 border-black bg-black text-white font-bold text-sm hover:bg-gray-800 disabled:opacity-50"
            >
              {busy ? "Applying…" : "Apply to selected"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
