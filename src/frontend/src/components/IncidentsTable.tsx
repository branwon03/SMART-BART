import { useCallback, useEffect, useRef, useState } from "react";
import type { Incident } from "../types/api";
import { formatElapsedSince } from "../lib/formatElapsedSince";
import { isHighPriority } from "../lib/priorityUi";
import { BulkDeleteModal } from "./BulkDeleteModal";

type IncidentsTableProps = {
  activeTab: string;
  filteredData: Incident[];
  selectedIncidentId: string | null;
  now: Date;
  onSelectIncident: (incident: Incident) => void;
  onBulkDelete: (
    incidentIds: string[],
  ) => Promise<{
    deletedIds: string[];
    failures: { id: string; message: string }[];
  }>;
};

export function IncidentsTable({
  activeTab,
  filteredData,
  selectedIncidentId,
  now,
  onSelectIncident,
  onBulkDelete,
}: IncidentsTableProps) {
  const [bulkSelectedIds, setBulkSelectedIds] = useState<Set<string>>(() => new Set());
  const [actionsMenuOpen, setActionsMenuOpen] = useState(false);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);
  const headerCheckboxRef = useRef<HTMLInputElement>(null);
  const actionsWrapRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const valid = new Set(filteredData.map((i) => i.incident_id));
    setBulkSelectedIds((prev) => {
      const next = new Set<string>();
      for (const id of prev) {
        if (valid.has(id)) next.add(id);
      }
      return next.size === prev.size && [...prev].every((id) => valid.has(id)) ? prev : next;
    });
  }, [filteredData]);

  const allBulkSelected =
    filteredData.length > 0 &&
    filteredData.every((item) => bulkSelectedIds.has(item.incident_id));

  const someBulkSelected =
    bulkSelectedIds.size > 0 && !allBulkSelected;

  useEffect(() => {
    const el = headerCheckboxRef.current;
    if (el) el.indeterminate = someBulkSelected;
  }, [someBulkSelected]);

  const toggleSelectAll = useCallback(() => {
    setBulkSelectedIds((prev) => {
      if (filteredData.length === 0) return new Set();
      const allIds = new Set(filteredData.map((i) => i.incident_id));
      const fullySelected =
        prev.size === allIds.size && [...allIds].every((id) => prev.has(id));
      return fullySelected ? new Set() : allIds;
    });
  }, [filteredData]);

  const toggleRowBulk = useCallback((incidentId: string) => {
    setBulkSelectedIds((prev) => {
      const next = new Set(prev);
      if (next.has(incidentId)) next.delete(incidentId);
      else next.add(incidentId);
      return next;
    });
  }, []);

  useEffect(() => {
    if (!actionsMenuOpen) return;
    const onPointerDown = (e: PointerEvent) => {
      const el = actionsWrapRef.current;
      if (el && !el.contains(e.target as Node)) setActionsMenuOpen(false);
    };
    document.addEventListener("pointerdown", onPointerDown);
    return () => document.removeEventListener("pointerdown", onPointerDown);
  }, [actionsMenuOpen]);

  const selectedIncidentsForBulk = filteredData.filter((i) =>
    bulkSelectedIds.has(i.incident_id),
  );

  const closeBulkDeleteModal = useCallback(() => setBulkDeleteOpen(false), []);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-4 bg-white border-b border-slate-100 flex items-center justify-between">
        <div ref={actionsWrapRef} className="relative">
          <button
            type="button"
            aria-expanded={actionsMenuOpen}
            aria-haspopup="menu"
            onClick={() => setActionsMenuOpen((o) => !o)}
            className="bg-blue-500 text-white px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:bg-blue-600 transition-colors"
          >
            Actions <span aria-hidden>▼</span>
          </button>
          {actionsMenuOpen && (
            <div
              role="menu"
              className="absolute left-0 top-full mt-1 min-w-[12rem] rounded-lg border border-slate-200 bg-white py-1 shadow-lg z-20"
            >
              <button
                type="button"
                role="menuitem"
                disabled={bulkSelectedIds.size === 0}
                onClick={() => {
                  if (bulkSelectedIds.size === 0) return;
                  setActionsMenuOpen(false);
                  setBulkDeleteOpen(true);
                }}
                className="w-full px-4 py-2 text-left text-xs font-semibold text-red-600 hover:bg-red-50 disabled:cursor-not-allowed disabled:text-slate-400 disabled:hover:bg-transparent"
              >
                Delete selected{bulkSelectedIds.size > 0 ? ` (${bulkSelectedIds.size})` : ""}
              </button>
            </div>
          )}
        </div>
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          {filteredData.length} Total Records
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-widest text-slate-400 font-black border-b border-slate-100">
            <tr>
              <th className="p-5 w-12">
                <input
                  ref={headerCheckboxRef}
                  type="checkbox"
                  checked={allBulkSelected}
                  onChange={toggleSelectAll}
                  onClick={(e) => e.stopPropagation()}
                  className="w-4 h-4 rounded border-slate-300"
                />
              </th>
              <th className="p-5">Issue Title</th>
              <th className="p-5">Incident ID</th>
              <th className="p-5">Priority</th>
              <th className="p-5">Status</th>
              <th className="p-5">Location</th>
              <th className="p-5 text-right font-bold text-blue-600 uppercase">Time Elapsed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={7} className="p-20 text-center text-slate-400 italic">
                  No reports currently active for {activeTab}.
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr
                  key={item.incident_id}
                  onClick={(e) => {
                    if ((e.target as HTMLElement).closest("input, button, a, label")) return;
                    onSelectIncident(item);
                  }}
                  className={`cursor-pointer transition-all group ${selectedIncidentId === item.incident_id
                      ? "bg-blue-50"
                      : "hover:bg-slate-50"
                    }`}
                >
                  <td className="p-5">
                    <input
                      type="checkbox"
                      checked={bulkSelectedIds.has(item.incident_id)}
                      onChange={() => toggleRowBulk(item.incident_id)}
                      onClick={(e) => e.stopPropagation()}
                      className="w-4 h-4 rounded border-slate-300 text-blue-600"
                    />
                  </td>
                  <td className="p-5 font-bold text-slate-700">{item.vlm_summary}</td>
                  <td className="p-5 font-mono text-xs text-slate-400">
                    #{item.incident_id.slice(0, 8)}
                  </td>
                  <td className="p-5">
                    <div
                      className={`h-1.5 w-10 rounded-full ${isHighPriority(item.issue_priority)
                          ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)]"
                          : "bg-yellow-400"
                        }`}
                    />
                  </td>
                  <td className="p-5 text-xs font-semibold text-slate-600">
                    {item.status ?? "—"}
                  </td>
                  <td className="p-5 text-xs font-semibold text-slate-600 uppercase tracking-tighter">
                    {item.location_id}
                  </td>
                  <td className="p-5 text-right font-mono text-xs font-bold text-slate-500">
                    {formatElapsedSince(item.created_at, now)}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {bulkDeleteOpen && selectedIncidentsForBulk.length > 0 && (
        <BulkDeleteModal
          incidents={selectedIncidentsForBulk}
          onCancel={closeBulkDeleteModal}
          onAllSucceeded={() => {
            closeBulkDeleteModal();
          }}
          onConfirm={async () => {
            const ids = selectedIncidentsForBulk.map((i) => i.incident_id);
            return onBulkDelete(ids);
          }}
        />
      )}
    </div>
  );
}
