"use client";

import { useState } from "react";
import type { Incident } from "../types/api";
import { deleteIncident } from "../lib/incidents";
import { displayCompactIncidentId } from "../lib/formatIncidentId";

type DeleteIssueModalProps = {
  incident: Incident;
  onConfirm: () => void;
  onCancel: () => void;
};

export function DeleteIssueModal({ incident, onConfirm, onCancel }: DeleteIssueModalProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleDelete() {
    setDeleting(true);
    setError(null);
    try {
      await deleteIncident(incident.incident_id);
      onConfirm();
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      setDeleting(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onCancel} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-red-600 shadow-2xl w-full max-w-md p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-xl font-black text-red-600 mb-4">Delete Issue</h2>

          <p className="text-sm text-gray-700 mb-2">
            Are you sure you want to permanently delete this issue?
          </p>

          <div className="bg-gray-100 rounded-lg border border-gray-300 px-4 py-3 mb-4 text-sm">
            <div className="font-bold text-gray-800 mb-1">
              {incident.vlm_summary ?? "Untitled issue"}
            </div>
            <div className="font-mono text-xs text-gray-500">
              {displayCompactIncidentId(incident.incident_id)}
            </div>
          </div>

          <p className="text-xs text-gray-500 mb-6">
            This action cannot be undone. All associated photo reports will also be removed.
          </p>

          {error && (
            <p className="text-red-600 text-sm font-semibold mb-4">{error}</p>
          )}

          <div className="flex justify-end gap-3">
            <button
              type="button"
              onClick={onCancel}
              disabled={deleting}
              className="px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={handleDelete}
              disabled={deleting}
              className="px-5 py-2 rounded-lg border-2 border-red-700 bg-red-600 text-white font-bold text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "Deleting..." : "Delete"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
