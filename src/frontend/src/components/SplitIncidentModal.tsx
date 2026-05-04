"use client";

import { useMemo, useState } from "react";
import type { Incident, PhotoReport } from "../types/api";
import { MAINTENANCE_DISCIPLINES } from "../hooks/useMaintenanceDashboard";
import { API_BASE_URL } from "../lib/config";
import { splitIncident } from "../lib/incidents";

function disciplineDefaultFromIncident(incident: Incident): string {
  const raw = incident.discipline?.trim();
  if (!raw) return MAINTENANCE_DISCIPLINES[0];
  const found = MAINTENANCE_DISCIPLINES.find(
    (d) => d === raw || d.toLowerCase() === raw.toLowerCase(),
  );
  return found ?? MAINTENANCE_DISCIPLINES[0];
}

type Step = 1 | 2;

type SplitIncidentModalProps = {
  incident: Incident;
  evidence: PhotoReport[];
  onSplit: (parentIncidentId: string) => void;
  onCancel: () => void;
};

export function SplitIncidentModal({
  incident,
  evidence,
  onSplit,
  onCancel,
}: SplitIncidentModalProps) {
  const [step, setStep] = useState<Step>(1);
  const [selected, setSelected] = useState<Set<string>>(() => new Set());
  const [title, setTitle] = useState("");
  const [description, setDescription] = useState("");
  const [childDiscipline, setChildDiscipline] = useState(() =>
    disciplineDefaultFromIncident(incident),
  );
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const toggle = (id: string) => {
    setSelected((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  };

  const selectedCount = selected.size;
  const total = evidence.length;
  const leavesParentWithPhoto = total - selectedCount >= 1;

  const canAdvanceToDetails = selectedCount > 0 && leavesParentWithPhoto;

  const canSubmit = useMemo(() => {
    if (!childDiscipline.trim()) return false;
    if (!title.trim()) return false;
    if (selectedCount === 0) return false;
    if (!leavesParentWithPhoto) return false;
    return true;
  }, [title, selectedCount, leavesParentWithPhoto, childDiscipline]);

  async function handleSave() {
    if (!canSubmit) return;
    setSaving(true);
    setError(null);
    try {
      await splitIncident(incident.incident_id, {
        evidence_ids: [...selected],
        title: title.trim(),
        description: description.trim() === "" ? undefined : description.trim(),
        discipline: childDiscipline,
      });
      onSplit(incident.incident_id);
    } catch (err) {
      console.error("Split failed:", err);
      setError(err instanceof Error ? err.message : "Split failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div className="fixed inset-0 bg-black/40 z-40" onClick={onCancel} />

      <div className="fixed inset-0 z-50 flex items-center justify-center p-4">
        <div
          className="bg-white rounded-xl border-2 border-black shadow-2xl w-full max-w-lg max-h-[90vh] overflow-hidden flex flex-col p-6"
          onClick={(e) => e.stopPropagation()}
        >
          <div className="flex items-baseline justify-between gap-4 mb-1">
            <h2 className="text-xl font-black">Split incident</h2>
            <span className="text-xs font-bold tabular-nums text-gray-500 shrink-0">
              {step} / 2
            </span>
          </div>

          {step === 1 && (
            <>
              <p className="text-sm text-gray-600 mb-4">
                Scroll sideways, tap photos for the child incident. Parent keeps at least one.
              </p>

              <div className="border-2 border-gray-200 rounded-lg p-3 mb-2 shrink-0">
                <div className="overflow-x-auto pb-2 -mx-0.5 px-0.5 [scrollbar-width:thin]">
                  <div className="flex gap-3 w-max min-h-[10rem]">
                    {evidence.map((ev) => {
                      const checked = selected.has(ev.evidence_id);
                      return (
                        <label
                          key={ev.evidence_id}
                          className={`relative cursor-pointer shrink-0 w-[9.5rem] rounded-lg border-2 overflow-hidden ${
                            checked ? "border-black ring-2 ring-black/30" : "border-gray-200"
                          }`}
                        >
                          <input
                            type="checkbox"
                            className="absolute left-2 top-2 size-4 z-10"
                            checked={checked}
                            onChange={() => toggle(ev.evidence_id)}
                          />
                          {ev.image_url ? (
                            <img
                              src={`${API_BASE_URL}${ev.image_url}`}
                              alt=""
                              className="aspect-square h-36 w-full object-cover bg-gray-100"
                            />
                          ) : (
                            <div className="flex h-36 w-full items-center justify-center bg-gray-100 text-gray-400 text-xs">
                              No image
                            </div>
                          )}
                        </label>
                      );
                    })}
                  </div>
                </div>
              </div>

              <p className="text-xs text-gray-600 mb-2">
                Selected {selectedCount} of {total}
              </p>

              {selectedCount > 0 && !leavesParentWithPhoto && (
                <p className="text-amber-700 text-sm font-semibold mb-2">
                  Leave at least one photo on this incident.
                </p>
              )}
            </>
          )}

          {step === 2 && (
            <>
              <p className="text-sm text-gray-600 mb-4">
                {selectedCount} photo{selectedCount === 1 ? "" : "s"} will move. Set title for new incident.
              </p>

              <label className="block mb-3">
                <span className="text-sm font-bold text-gray-700">Discipline</span>
                <select
                  value={childDiscipline}
                  onChange={(e) => setChildDiscipline(e.target.value)}
                  className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
                >
                  {MAINTENANCE_DISCIPLINES.map((d) => (
                    <option key={d} value={d}>
                      {d}
                    </option>
                  ))}
                </select>
              </label>

              <label className="block mb-3">
                <span className="text-sm font-bold text-gray-700">New incident title</span>
                <input
                  type="text"
                  value={title}
                  onChange={(e) => setTitle(e.target.value)}
                  placeholder="Title for the split incident"
                  className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm font-semibold focus:border-black focus:outline-none"
                />
              </label>

              <label className="block mb-4">
                <span className="text-sm font-bold text-gray-700">Description (optional)</span>
                <textarea
                  value={description}
                  onChange={(e) => setDescription(e.target.value)}
                  placeholder="Applied to split photos…"
                  rows={3}
                  className="mt-1 block w-full rounded-lg border-2 border-gray-300 bg-white px-3 py-2 text-sm focus:border-black focus:outline-none resize-y min-h-[4.5rem]"
                />
              </label>
            </>
          )}

          {error && (
            <p className="text-red-600 text-sm font-semibold mb-4">{error}</p>
          )}

          <div className="flex flex-wrap justify-end gap-3 mt-auto pt-2 border-t border-gray-100">
            {step === 1 && (
              <>
                <button
                  type="button"
                  onClick={onCancel}
                  disabled={saving}
                  className="mr-auto px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
                >
                  Cancel
                </button>
                <button
                  type="button"
                  onClick={() => setStep(2)}
                  disabled={saving || !canAdvanceToDetails}
                  className="px-5 py-2 rounded-lg border-2 border-black bg-black text-white font-bold text-sm hover:bg-gray-800 disabled:opacity-50"
                >
                  Next
                </button>
              </>
            )}
            {step === 2 && (
              <>
                <button
                  type="button"
                  onClick={() => {
                    setError(null);
                    setStep(1);
                  }}
                  disabled={saving}
                  className="mr-auto px-5 py-2 rounded-lg border-2 border-black font-bold text-sm hover:bg-gray-100 disabled:opacity-50"
                >
                  Back
                </button>
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
                  disabled={saving || !canSubmit}
                  className="px-5 py-2 rounded-lg border-2 border-black bg-black text-white font-bold text-sm hover:bg-gray-800 disabled:opacity-50"
                >
                  {saving ? "Saving…" : "Split"}
                </button>
              </>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
