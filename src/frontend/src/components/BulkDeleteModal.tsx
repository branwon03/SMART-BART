"use client";

import { useState } from "react";
import type { Incident } from "../types/api";
import { deleteIncident } from "../lib/incidents";
import { displayCompactIncidentId } from "../lib/formatIncidentId";

type BulkDeleteModalProps = {
  incidents: Incident[];
  onApplied: (deletedIds: string[]) => void;
  onClose: () => void;
};

export function BulkDeleteModal({ incidents, onApplied, onClose }: BulkDeleteModalProps) {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [resultNote, setResultNote] = useState<string | null>(null);

  async function handleConfirm() {
    setBusy(true);
    setError(null);
    setResultNote(null);
    try {
      const results = await Promise.allSettled(
        incidents.map((inc) => deleteIncident(inc.incident_id)),
      );
      const deletedIds: string[] = [];
      const failedIds: string[] = [];
      results.forEach((r, i) => {
        if (r.status === "fulfilled") {
          deletedIds.push(incidents[i].incident_id);
        } else {
          failedIds.push(displayCompactIncidentId(incidents[i].incident_id));
        }
      });

      if (deletedIds.length > 0) {
        onApplied(deletedIds);
      }

      if (failedIds.length === 0) {
        setResultNote(`Deleted ${deletedIds.length} incident${deletedIds.length === 1 ? "" : "s"}.`);
      } else {
        setError(`Deleted ${deletedIds.length}; failed ${failedIds.length}: ${failedIds.join(", ")}`);
        if (deletedIds.length > 0) {
          setResultNote("Partial success — you can retry failed rows.");
        }
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Bulk delete failed");
    } finally {
      setBusy(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onClose} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-red-600 shadow-2xl w-full max-w-lg max-h-[85vh] flex flex-col p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-xl font-black text-red-600 mb-2">Bulk delete incidents</h2>

          <p className="text-sm text-gray-700 mb-2">
            Permanently delete <strong>{incidents.length}</strong> incident
            {incidents.length === 1 ? "" : "s"} below? Associated photo reports are removed too. Cannot
            undo.
          </p>

          <div className="rounded-lg border border-gray-300 bg-gray-50 max-h-48 overflow-y-auto mb-4 text-sm divide-y divide-gray-200">
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

          {error && <p className="text-red-600 text-sm font-semibold mb-2">{error}</p>}
          {resultNote && <p className="text-green-700 text-sm font-semibold mb-2">{resultNote}</p>}

          <div className="flex justify-end gap-3 mt-auto pt-4">
            <button
              type="button"
              onClick={onClose}
              disabled={busy}
              className="px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
            >
              Cancel
            </button>
            <button
              type="button"
              onClick={() => void handleConfirm()}
              disabled={busy}
              className="px-5 py-2 rounded-lg border-2 border-red-700 bg-red-600 text-white font-bold text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {busy ? "Deleting…" : "Delete selected"}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
