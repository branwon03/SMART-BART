"use client";

import { useMemo, useState } from "react";
import type { Incident, PhotoReport } from "../types/api";
import { API_BASE_URL } from "../lib/config";
import { displayCompactIncidentId } from "../lib/formatIncidentId";
import { formatDateTime, formatShortDate } from "../lib/formatDate";
import { formatElapsedSince } from "../lib/formatElapsedSince";
import { getPriorityStyles } from "../lib/priorityUi";
import { EditIssueModal } from "./EditIssueModal";
import { DeleteIssueModal } from "./DeleteIssueModal";
import { MergeIncidentModal } from "./MergeIncidentModal";
import { SplitIncidentModal } from "./SplitIncidentModal";

type IncidentDetailPanelProps = {
  incident: Incident;
  evidence: PhotoReport[];
  allIncidents: Incident[];
  now: Date;
  incidentIdExpanded: boolean;
  onToggleIncidentIdExpanded: () => void;
  onClose: () => void;
  onIncidentUpdated: (updated: Incident) => void;
  onIncidentDeleted: (incidentId: string) => void;
  onRefreshAfterMerge: (incidentId: string) => Promise<void>;
  onIncidentSplit: (parentIncidentId: string) => void;
};

export function IncidentDetailPanel({
  incident,
  evidence,
  allIncidents,
  now,
  incidentIdExpanded,
  onToggleIncidentIdExpanded,
  onClose,
  onIncidentUpdated,
  onIncidentDeleted,
  onRefreshAfterMerge,
  onIncidentSplit,
}: IncidentDetailPanelProps) {
  const [currentIndex, setCurrentIndex] = useState(0);

  const [editModalOpen, setEditModalOpen] = useState(false);
  const [deleteModalOpen, setDeleteModalOpen] = useState(false);
  const [splitModalOpen, setSplitModalOpen] = useState(false);
  const [mergeModalOpen, setMergeModalOpen] = useState(false);

  const descriptionBlocks = useMemo(() => {
    if (evidence.length === 0) {
      return { kind: "empty" as const };
    }
    const trimmed = evidence.map((e) => (e.user_context ?? "").trim());
    const unique = new Set(trimmed);
    if (unique.size <= 1) {
      const text = trimmed[0]
        ? trimmed[0]
        : "Rider report logged via web-app.";
      return {
        kind: "single" as const,
        text,
        submittedAt: evidence[0].submitted_at,
        photoCount: evidence.length,
      };
    }
    return { kind: "multiple" as const, items: evidence };
  }, [evidence]);

  const displayIndex =
    evidence.length === 0
      ? 0
      : Math.min(Math.max(currentIndex, 0), evidence.length - 1);

  const handlePrev = () => {
    setCurrentIndex((prev) => {
      const n = evidence.length;
      if (n === 0) return 0;
      const i = Math.min(Math.max(prev, 0), n - 1);
      return i === 0 ? n - 1 : i - 1;
    });
  };

  const handleNext = () => {
    setCurrentIndex((prev) => {
      const n = evidence.length;
      if (n === 0) return 0;
      const i = Math.min(Math.max(prev, 0), n - 1);
      return i === n - 1 ? 0 : i + 1;
    });
  };

  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-20" onClick={onClose} />

      <aside className="fixed top-0 right-0 w-[450px] bg-white border-l-4 border-black h-screen p-6 shadow-2xl z-30 overflow-y-auto font-sans text-sm">
        <div className="flex items-start gap-4 mb-8">
          <div className="flex-1 min-w-0 border-b-2 border-slate-300 pb-4">
            <h2 className="text-xl font-bold mb-4 leading-tight">{incident.vlm_summary}</h2>

            <div className="grid grid-cols-[100px_1fr] gap-y-2 text-sm">
              <span className="font-bold text-gray-700">Incident ID:</span>
              <span
                role="button"
                tabIndex={0}
                aria-expanded={incidentIdExpanded}
                aria-label={
                  incidentIdExpanded
                    ? "Full incident ID. Click to collapse."
                    : "Incident ID. Click to expand."
                }
                onClick={onToggleIncidentIdExpanded}
                onKeyDown={(e) => {
                  if (e.key === "Enter" || e.key === " ") {
                    e.preventDefault();
                    onToggleIncidentIdExpanded();
                  }
                }}
                className={`inline-block max-w-full font-mono text-xs rounded-md border-2 border-black/15 bg-amber-50 px-2 py-0.5 text-slate-900 shadow-sm transition-colors hover:bg-amber-100 hover:border-black/30 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 ${incidentIdExpanded ? "break-all" : ""
                  }`}
                title={
                  incidentIdExpanded
                    ? "Click to show short ID"
                    : `${incident.incident_id} — click to expand`
                }
              >
                {incidentIdExpanded
                  ? incident.incident_id
                  : displayCompactIncidentId(incident.incident_id)}
              </span>

              <span className="font-bold text-gray-700">Priority:</span>
              <span
                className={getPriorityStyles(
                  // CHANGED: Use a fallback to ensure we only pass string | null
                  incident.issue_priority ? String(incident.issue_priority) : null // [cite: 651, 656]
                )}
              >
                {incident.issue_priority != null && incident.issue_priority !== ""
                  ? String(incident.issue_priority)
                  : "—"}
              </span>

              <span className="font-bold text-gray-700">Status:</span>
              <span className="text-700">{incident.status}</span>

              <span className="font-bold text-gray-700">Location:</span>
              <span>{incident.location_id}</span>

              <span className="font-bold text-gray-700">First reported:</span>
              <span>{formatShortDate(incident.created_at)}</span>

              <span className="font-bold text-gray-700">Age:</span>
              <span>{formatElapsedSince(incident.created_at, now)}</span>
            </div>
          </div>

          <div className="w-[7.5rem] shrink-0 flex flex-col gap-2 pl-4 pt-10">
            <button
              type="button"
              onClick={() => setEditModalOpen(true)}
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Edit Issue
            </button>
            <button
              type="button"
              onClick={() => setMergeModalOpen(true)}
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Merge
            </button>
            <button
              type="button"
              disabled={evidence.length < 2}
              title={evidence.length < 2 ? "Need at least two photos to split" : undefined}
              onClick={() => setSplitModalOpen(true)}
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100 disabled:opacity-50 disabled:hover:bg-white disabled:cursor-not-allowed"
            >
              Split
            </button>
            <button
              type="button"
              onClick={() => setDeleteModalOpen(true)}
              className="bg-red-600 text-white font-bold py-1 rounded-lg border-2 border-red-700 hover:bg-red-700"
            >
              Delete
            </button>
          </div>
        </div>

        <div className="mt-4 mb-6">
          <h3 className="font-bold text-lg mb-2">Description:</h3>
          <div className="bg-gray-100 border border-gray-300 rounded-lg p-5 h-48 overflow-y-auto text-[15px] leading-relaxed space-y-8">
            {/* Case 1: Single Report or consolidated view */}
            {descriptionBlocks.kind === "single" && (
              <div className="border-b border-gray-200 pb-3 last:border-0">
                <div className="flex justify-between font-bold text-gray-500 mb-1">
                  <span>
                    Rider report
                    {descriptionBlocks.photoCount > 1 ? (
                      <span className="font-normal text-gray-400">
                        {" "} ({descriptionBlocks.photoCount} photos)
                      </span>
                    ) : null}
                  </span>
                  <span className="font-mono text-[10px] font-normal text-slate-500">
                    {formatDateTime(descriptionBlocks.submittedAt)}
                  </span>
                </div>
                <div className="text-gray-800">
                  <div>&quot;{descriptionBlocks.text}&quot;</div>
                  {incident.issue_priority && (
                    <div className="text-gray-600 mt-1">
                      Priority: {String(incident.issue_priority)}
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Case 2: Multiple individual reports merged together */}
            {descriptionBlocks.kind === "multiple" &&
              descriptionBlocks.items.map((ev, idx) => (
                <div key={ev.evidence_id} className="border-b border-gray-200 pb-3 last:border-0">
                  <div className="flex justify-between font-bold text-gray-500 mb-1">
                    <span>Report summary {idx + 1}:</span>
                    <span className="font-mono text-[10px] font-normal text-slate-500">
                      {formatDateTime(ev.submitted_at)}
                    </span>
                  </div>
                  {/* Use <div> here too */}
                  <div className="text-gray-800">
                    <div>- &quot;{ev.user_context || "Rider report logged via web-app."}&quot;</div>
                    {ev.found_priority && (
                      <div className="text-gray-600 mt-1">
                        Priority: {ev.found_priority}
                      </div>
                    )}
                  </div>
                </div>
              ))}

            {/* Reporter info block */}
            {descriptionBlocks.kind === "empty" && (
              <p className="text-gray-400 italic text-center py-4">No historical reports found.</p>
            )}
            {(() => {
              const reporter = evidence.find(
                (e) => e.reporter_name || e.reporter_contact,
              );
              if (!reporter) return null;
              return (
                /* Removed 'border-t' and 'pt-3' to eliminate the double line */
                <div className="mt-3">
                  <span className="font-bold text-gray-500 text-xs tracking-wide">
                    Last Reporter
                  </span>
                  <p className="text-gray-800 mt-1">
                    {reporter.reporter_name ? (
                      <span>{reporter.reporter_name}</span>
                    ) : null}
                    {reporter.reporter_name && reporter.reporter_contact ? (
                      <span> — </span>
                    ) : null}
                    {reporter.reporter_contact ? (
                      <span className="text-blue-600">{reporter.reporter_contact}</span>
                    ) : null}
                  </p>
                </div>
              );
            })()}
          </div>
        </div>

        <div className="flex flex-col items-center">
          <div className="relative w-full aspect-square bg-gray-200 mb-8 border-2 border-gray-300 overflow-hidden rounded-none">
            {evidence.length > 0 && evidence[displayIndex]?.image_url ? (
              <img
                src={`${API_BASE_URL}${evidence[displayIndex].image_url}`}
                className="w-full h-full object-cover"
                alt="Main evidence"
              />
            ) : (
              <div className="flex items-center justify-center h-full text-gray-400">
                No Image Available
              </div>
            )}
            <button
              type="button"
              onClick={handlePrev}
              className="absolute left-2 top-1/2 -translate-y-1/2 text-2xl font-bold bg-white/50 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white transition-colors"
            >
              ←
            </button>
            <button
              type="button"
              onClick={handleNext}
              className="absolute right-2 top-1/2 -translate-y-1/2 text-2xl font-bold bg-white/50 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white transition-colors"
            >
              →
            </button>
          </div>

          <button
            type="button"
            onClick={onClose}
            className="w-32 py-2 border-[3px] border-black rounded-lg font-black text-lg uppercase tracking-tighter hover:bg-gray-100 active:scale-95 transition-all"
          >
            Close
          </button>
        </div>
      </aside>

      {editModalOpen && (
        <EditIssueModal
          incident={incident}
          onSave={(updated) => {
            setEditModalOpen(false);
            onIncidentUpdated(updated);
            onClose();
          }}
          onCancel={() => setEditModalOpen(false)}
        />
      )}

      {deleteModalOpen && (
        <DeleteIssueModal
          incident={incident}
          onConfirm={() => {
            setDeleteModalOpen(false);
            onIncidentDeleted(incident.incident_id);
          }}
          onCancel={() => setDeleteModalOpen(false)}
        />
      )}

      {mergeModalOpen && (
        <MergeIncidentModal
          targetIncident={incident}
          allIncidents={allIncidents}
          onCancel={() => setMergeModalOpen(false)}
          onMerged={() => {
            void (async () => {
              await onRefreshAfterMerge(incident.incident_id);
              setMergeModalOpen(false);
            })();
          }}
        />
      )}
      {splitModalOpen && (
        <SplitIncidentModal
          incident={incident}
          evidence={evidence}
          onSplit={(parentId) => {
            setSplitModalOpen(false);
            onIncidentSplit(parentId);
          }}
          onCancel={() => setSplitModalOpen(false)}
        />
      )}
    </>
  );
}
