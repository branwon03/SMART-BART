import type { Incident, PhotoReport } from "../types/api";
import { API_BASE_URL } from "../lib/config";
import { displayCompactIncidentId } from "../lib/formatIncidentId";
import { formatElapsedSince } from "../lib/formatElapsedSince";

type IncidentDetailPanelProps = {
  incident: Incident;
  evidence: PhotoReport[];
  now: Date;
  incidentIdExpanded: boolean;
  onToggleIncidentIdExpanded: () => void;
  onClose: () => void;
};

export function IncidentDetailPanel({
  incident,
  evidence,
  now,
  incidentIdExpanded,
  onToggleIncidentIdExpanded,
  onClose,
}: IncidentDetailPanelProps) {
  return (
    <>
      <div className="fixed inset-0 bg-black/20 z-20" onClick={onClose} />

      <aside className="fixed top-0 right-0 w-[450px] bg-white border-l-4 border-black h-screen p-6 shadow-2xl z-30 overflow-y-auto font-sans text-sm">
        <div className="border-b-2 border-gray-300 pb-4 mb-4 relative pr-36">
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
              className={`inline-block max-w-full font-mono text-xs rounded-md border-2 border-black/15 bg-amber-50 px-2 py-0.5 text-slate-900 shadow-sm transition-colors hover:bg-amber-100 hover:border-black/30 cursor-pointer outline-none focus-visible:ring-2 focus-visible:ring-black focus-visible:ring-offset-2 ${
                incidentIdExpanded ? "break-all" : ""
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
              className={
                incident.issue_priority === 1 ? "text-black-500" : "text-yellow-600 font-bold"
              }
            >
              {incident.issue_priority === 1 ? "TODO" : "Standard"}
            </span>

            <span className="font-bold text-gray-700">Status:</span>
            <span className="text-700">{incident.status}</span>

            <span className="font-bold text-gray-700">Location:</span>
            <span>{incident.location_id}</span>

            <span className="font-bold text-gray-700">Age:</span>
            <span>{formatElapsedSince(incident.created_at, now)}</span>
          </div>

          <div className="absolute top-10 right-0 flex flex-col gap-2 w-32">
            <button
              type="button"
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Begin
            </button>
            <button
              type="button"
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Edit Issue
            </button>
            <button
              type="button"
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Redirect
            </button>
            <button
              type="button"
              className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100"
            >
              Merge/Split
            </button>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="font-bold text-lg mb-2">Description:</h3>
          <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 h-48 overflow-y-auto text-[11px] leading-relaxed space-y-4">
            {evidence.map((ev, idx) => (
              <div key={ev.evidence_id} className="border-b border-gray-200 pb-3 last:border-0">
                <div className="flex justify-between font-bold text-gray-500 mb-1">
                  <span>Report summary {idx + 1}:</span>
                  <span>TODO:timestamp</span>
                </div>
                <p className="text-gray-800">
                  - &quot;{ev.user_context || "Rider report logged via web-app."}&quot;
                </p>
              </div>
            ))}
            {evidence.length === 0 && (
              <p className="text-gray-400 italic text-center py-4">No historical reports found.</p>
            )}
          </div>
        </div>

        <div className="flex flex-col items-center">
          <div className="relative w-full aspect-square bg-gray-200 mb-8 border-2 border-gray-300 overflow-hidden rounded-none">
            {evidence.length > 0 && evidence[0].image_url ? (
              <img
                src={`${API_BASE_URL}${evidence[0].image_url}`}
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
              className="absolute left-2 top-1/2 -translate-y-1/2 text-2xl font-bold bg-white/50 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white transition-colors"
            >
              ←
            </button>
            <button
              type="button"
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
    </>
  );
}
