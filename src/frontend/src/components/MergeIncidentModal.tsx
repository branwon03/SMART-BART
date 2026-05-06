"use client";

import { useCallback, useEffect, useMemo, useState } from "react";
import type { Incident, PhotoReport } from "../types/api";
import { API_BASE_URL } from "../lib/config";
import { getPhotoReports, mergePhotos } from "../lib/incidents";
import { displayCompactIncidentId } from "../lib/formatIncidentId";

type MergeIncidentModalProps = {
  targetIncident: Incident;
  allIncidents: Incident[];
  onCancel: () => void;
  onMerged: () => void;
};

function evidenceDescription(pr: PhotoReport): string {
  const ctx = (pr.user_context ?? "").trim();
  if (ctx) return ctx;
  const vlm = (pr.vlm_summary ?? "").trim();
  if (vlm) return vlm;
  return "Rider report logged via web-app.";
}

export function MergeIncidentModal({
  targetIncident,
  allIncidents,
  onCancel,
  onMerged,
}: MergeIncidentModalProps) {
  const [step, setStep] = useState<"list" | "pick">("list");
  const [sourceIncident, setSourceIncident] = useState<Incident | null>(null);
  const [sourceReports, setSourceReports] = useState<PhotoReport[]>([]);
  const [loadingReports, setLoadingReports] = useState(false);
  const [selectedIds, setSelectedIds] = useState<Set<string>>(new Set());
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const otherIncidents = useMemo(
    () =>
      allIncidents
        .filter((i) => i.incident_id !== targetIncident.incident_id)
        .sort((a, b) => {
          const ta = a.created_at ? Date.parse(a.created_at) : 0;
          const tb = b.created_at ? Date.parse(b.created_at) : 0;
          return tb - ta;
        }),
    [allIncidents, targetIncident.incident_id],
  );

  const loadReports = useCallback(async (incidentId: string) => {
    setLoadingReports(true);
    setError(null);
    try {
      const rows = await getPhotoReports(incidentId);
      setSourceReports(rows);
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Failed to load images");
      setSourceReports([]);
    } finally {
      setLoadingReports(false);
    }
  }, []);

  useEffect(() => {
    if (step === "pick" && sourceIncident) {
      void loadReports(sourceIncident.incident_id);
    }
  }, [step, sourceIncident, loadReports]);

  function handlePickIncident(inc: Incident) {
    setSourceIncident(inc);
    setSelectedIds(new Set());
    setStep("pick");
  }

  function handleBack() {
    setStep("list");
    setSourceIncident(null);
    setSourceReports([]);
    setSelectedIds(new Set());
    setError(null);
  }

  function toggleEvidence(evidenceId: string) {
    setSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(evidenceId)) next.delete(evidenceId);
      else next.add(evidenceId);
      return next;
    });
  }

  async function handleSave() {
    const ids = [...selectedIds];
    if (ids.length === 0) {
      setError("Select at least one image to merge.");
      return;
    }
    setSaving(true);
    setError(null);
    try {
      await mergePhotos(targetIncident.incident_id, ids);
      onMerged();
    } catch (err) {
      console.error(err);
      setError(err instanceof Error ? err.message : "Merge failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <>
      <div
        className="fixed inset-0 bg-black/40 z-[100]"
        onClick={onCancel}
        aria-hidden
      />
      <div className="fixed inset-0 z-[110] flex items-center justify-center p-4 pointer-events-none">
        <div
          className="bg-white rounded-xl border-2 border-black shadow-2xl w-full max-w-2xl max-h-[90vh] flex flex-col pointer-events-auto"
          onClick={(e) => e.stopPropagation()}
          role="dialog"
          aria-modal
          aria-labelledby="merge-incident-title"
        >
          <div className="p-5 border-b-2 border-gray-200 shrink-0">
            <h2 id="merge-incident-title" className="text-lg font-black">
              {step === "list" ? "Merge from another incident" : "Select images to merge"}
            </h2>
            <p className="text-xs text-slate-500 mt-1 font-medium">
              Target: {targetIncident.vlm_summary ?? "(no title)"} · #
              {displayCompactIncidentId(targetIncident.incident_id)}
            </p>
          </div>

          {step === "list" && (
            <div className="flex-1 min-h-0 overflow-y-auto p-4">
              {otherIncidents.length === 0 ? (
                <p className="text-slate-500 text-center py-8">No other incidents to merge from.</p>
              ) : (
                <ul className="space-y-2">
                  {otherIncidents.map((inc) => (
                    <li key={inc.incident_id}>
                      <button
                        type="button"
                        onClick={() => handlePickIncident(inc)}
                        className="w-full text-left px-4 py-3 rounded-lg border-2 border-slate-200 hover:border-black hover:bg-slate-50 transition-colors"
                      >
                        <div className="font-bold text-slate-800 line-clamp-2">
                          {inc.vlm_summary ?? "—"}
                        </div>
                        <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-[10px] font-bold uppercase tracking-tight text-slate-400">
                          <span>#{displayCompactIncidentId(inc.incident_id)}</span>
                          <span>{inc.discipline ?? "—"}</span>
                          <span>{inc.issue_priority != null ? String(inc.issue_priority) : "—"}</span>
                        </div>
                      </button>
                    </li>
                  ))}
                </ul>
              )}
            </div>
          )}

          {step === "pick" && sourceIncident && (
            <div className="flex-1 min-h-0 flex flex-col">
              <div className="px-4 pt-3 shrink-0">
                <button
                  type="button"
                  onClick={handleBack}
                  className="text-sm font-bold text-blue-600 hover:underline"
                >
                  ← Back to incident list
                </button>
                <p className="text-xs text-slate-500 mt-1 font-mono">
                  Source: #{displayCompactIncidentId(sourceIncident.incident_id)}
                </p>
              </div>
              <div className="flex-1 min-h-0 overflow-y-auto p-4">
                {loadingReports ? (
                  <p className="text-center text-slate-500 py-8">Loading images…</p>
                ) : sourceReports.length === 0 ? (
                  <p className="text-center text-slate-500 py-8">No images on this incident.</p>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-3">
                    {sourceReports.map((pr) => {
                      const checked = selectedIds.has(pr.evidence_id);
                      return (
                        <button
                          key={pr.evidence_id}
                          type="button"
                          onClick={() => toggleEvidence(pr.evidence_id)}
                          className={`text-left rounded-lg border-2 overflow-hidden transition-colors ${
                            checked ? "border-blue-600 ring-2 ring-blue-200" : "border-slate-200 hover:border-black"
                          }`}
                        >
                          <div className="aspect-square bg-slate-100 relative">
                            {pr.image_url ? (
                              <img
                                src={`${API_BASE_URL}${pr.image_url}`}
                                alt=""
                                className="w-full h-full object-cover"
                              />
                            ) : (
                              <div className="w-full h-full flex items-center justify-center text-slate-400 text-xs">
                                No image
                              </div>
                            )}
                            <span
                              className={`absolute top-2 left-2 w-5 h-5 rounded border-2 flex items-center justify-center text-[10px] font-bold ${
                                checked ? "bg-blue-600 border-blue-600 text-white" : "bg-white border-slate-400"
                              }`}
                            >
                              {checked ? "✓" : ""}
                            </span>
                          </div>
                          <p className="p-2 text-[11px] leading-snug text-slate-700 line-clamp-3">
                            {evidenceDescription(pr)}
                          </p>
                        </button>
                      );
                    })}
                  </div>
                )}
              </div>
            </div>
          )}

          {error && (
            <div className="px-4 pb-2 shrink-0">
              <p className="text-sm text-red-600 font-medium">{error}</p>
            </div>
          )}

          <div className="p-4 border-t-2 border-gray-200 flex justify-end gap-3 shrink-0">
            <button
              type="button"
              onClick={onCancel}
              className="px-4 py-2 font-bold border-2 border-slate-300 rounded-lg hover:bg-slate-50"
            >
              Cancel
            </button>
            {step === "pick" && (
              <button
                type="button"
                onClick={() => void handleSave()}
                disabled={saving || selectedIds.size === 0}
                className="px-4 py-2 font-bold bg-blue-600 text-white border-2 border-blue-700 rounded-lg hover:bg-blue-700 disabled:opacity-50"
              >
                {saving ? "Saving…" : `Merge ${selectedIds.size} image(s)`}
              </button>
            )}
          </div>
        </div>
      </div>
    </>
  );
}
