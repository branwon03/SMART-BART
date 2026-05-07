"use client";

import { useState } from "react";
import type { Incident } from "../types/api";
import { displayCompactIncidentId } from "../lib/formatIncidentId";

type BulkDeleteModalProps = {
  incidents: Incident[];
  onConfirm: () => Promise<{
    deletedIds: string[];
    failures: { id: string; message: string }[];
  }>;
  onCancel: () => void;
  onAllSucceeded: () => void;
};

const PREVIEW_MAX = 5;

export function BulkDeleteModal({
  incidents,
  onConfirm,
  onCancel,
  onAllSucceeded,
}: BulkDeleteModalProps) {
  const [deleting, setDeleting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const count = incidents.length;

  async function handleConfirm() {
    setDeleting(true);
    setError(null);
    let unmounting = false;
    try {
      const { failures } = await onConfirm();
      if (failures.length === 0) {
        unmounting = true;
        onAllSucceeded();
        return;
      }
      setError(
        failures.length === count
          ? "Could not delete any incidents. Check network or try again."
          : `${failures.length} of ${count} could not be deleted.`,
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "Delete failed");
    } finally {
      if (!unmounting) setDeleting(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onCancel} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-red-600 shadow-2xl w-full max-w-md p-6 max-h-[90vh] overflow-y-auto"
          onClick={(e) => e.stopPropagation()}
        >
          <h2 className="text-xl font-black text-red-600 mb-4">Delete Selected Issues</h2>

          <p className="text-sm text-gray-700 mb-2">
            Permanently delete {count} selected issue{count === 1 ? "" : "s"}? This cannot be
            undone. Associated photo reports are removed as well.
          </p>

          <ul className="bg-gray-100 rounded-lg border border-gray-300 px-4 py-3 mb-4 text-sm space-y-2 max-h-48 overflow-y-auto">
            {incidents.slice(0, PREVIEW_MAX).map((inc) => (
              <li
                key={inc.incident_id}
                className="border-b border-gray-200 last:border-0 pb-2 last:pb-0"
              >
                <div className="font-bold text-gray-800">
                  {inc.vlm_summary ?? "Untitled issue"}
                </div>
                <div className="font-mono text-xs text-gray-500">
                  {displayCompactIncidentId(inc.incident_id)}
                </div>
              </li>
            ))}
            {count > PREVIEW_MAX && (
              <li className="text-xs text-gray-500 italic">…and {count - PREVIEW_MAX} more</li>
            )}
          </ul>

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
              onClick={handleConfirm}
              disabled={deleting}
              className="px-5 py-2 rounded-lg border-2 border-red-700 bg-red-600 text-white font-bold text-sm hover:bg-red-700 disabled:opacity-50"
            >
              {deleting ? "Deleting..." : `Delete ${count}`}
            </button>
          </div>
        </div>
      </div>
    </>
  );
}
