"use client";

import { useMemo, useState } from "react";
import type { Incident } from "../types/api";
import { MAINTENANCE_DISCIPLINES } from "../lib/disciplines";
import { updateIncident } from "../lib/incidents";

type RedirectIssueModalProps = {
  incident: Incident;
  onSave: (updated: Incident) => void;
  onCancel: () => void;
};

export function RedirectIssueModal({ incident, onSave, onCancel }: RedirectIssueModalProps) {
  const options = useMemo(
    () => disciplineSelectOptions(incident.discipline),
    [incident.discipline],
  );
  const [discipline, setDiscipline] = useState(() =>
    initialDiscipline(incident.discipline),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function handleSave() {
    setSaving(true);
    setError(null);
    try {
      const updated = await updateIncident(incident.incident_id, {
        discipline,
      });
      onSave(updated);
    } catch (err) {
      console.error("Failed to redirect incident:", err);
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
          <h2 className="text-xl font-black mb-6">Redirect Issue</h2>

          <label className="block mb-6">
            <span className="text-sm font-bold text-gray-700">Discipline</span>
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
