import { useState, useRef, useEffect } from "react";
import type { Incident } from "../types/api";
import { formatElapsedSince } from "../lib/formatElapsedSince";
import { formatShortDate } from "../lib/formatDate";
import { DisciplineSummary } from "./DisciplineSummary";

import {
  issuePriorityDotClassFromRaw,
  normalizeIssuePriority,
} from "../lib/priorityUi";

type IncidentsTableProps = {
  activeTab: string;
  filteredData: Incident[];
  selectedIncidentId: string | null;
  now: Date;
  checkedIds: Set<string>;
  onSelectIncident: (incident: Incident) => void;
  onToggleCheckedOne: (incidentId: string) => void;
  onToggleCheckedAllVisible: (visibleIncidentIds: string[]) => void;
  onBulkEditRequest: () => void;
  onBulkDeleteRequest: () => void;
};

export type DisciplineStat = {
  discipline: string;
  first_report: string | null;
  last_report: string | null;
  total_count: number;
};

export function IncidentsTable({
  activeTab,
  filteredData,
  selectedIncidentId,
  now,
  checkedIds,
  onSelectIncident,
  onToggleCheckedOne,
  onToggleCheckedAllVisible,
  onBulkEditRequest,
  onBulkDeleteRequest,
}: IncidentsTableProps) {
  const [actionsOpen, setActionsOpen] = useState(false);
  const dropdownRef = useRef<HTMLDivElement>(null);
  const headerCheckboxRef = useRef<HTMLInputElement>(null);

  const visibleIds = filteredData.map((i) => i.incident_id);
  const checkedVisibleCount =
    visibleIds.length === 0
      ? 0
      : visibleIds.reduce((acc, id) => acc + (checkedIds.has(id) ? 1 : 0), 0);
  const allChecked = visibleIds.length > 0 && checkedVisibleCount === visibleIds.length;
  const someChecked = checkedVisibleCount > 0 && !allChecked;
  const bulkDisabled = checkedIds.size === 0;

  useEffect(() => {
    if (headerCheckboxRef.current) {
      headerCheckboxRef.current.indeterminate = someChecked;
    }
  }, [someChecked]);

  useEffect(() => {
    function handleClickOutside(e: MouseEvent) {
      if (dropdownRef.current && !dropdownRef.current.contains(e.target as Node)) {
        setActionsOpen(false);
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
  }, []);

  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-4 bg-white border-b border-slate-100 flex items-center justify-between">
        <div className="relative" ref={dropdownRef}>
          <button
            type="button"
            onClick={() => setActionsOpen((prev) => !prev)}
            className="bg-blue-500 text-white px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:bg-blue-600 transition-colors"
          >
            Actions{" "}
            <span className={`transition-transform ${actionsOpen ? "rotate-180" : ""}`}>▼</span>
          </button>

          {actionsOpen && (
            <div className="absolute left-0 mt-1 w-44 bg-white border border-slate-200 rounded-lg shadow-lg z-50 overflow-hidden">
              <button
                type="button"
                disabled={bulkDisabled}
                onClick={() => {
                  setActionsOpen(false);
                  onBulkEditRequest();
                }}
                className="w-full text-left px-4 py-2.5 text-xs font-semibold text-slate-700 hover:bg-blue-50 hover:text-blue-600 disabled:opacity-40 disabled:pointer-events-none transition-colors flex items-center gap-2"
              >
                Bulk update
              </button>
              <button
                type="button"
                disabled={bulkDisabled}
                onClick={() => {
                  setActionsOpen(false);
                  onBulkDeleteRequest();
                }}
                className="w-full text-left px-4 py-2.5 text-xs font-semibold text-red-600 hover:bg-red-50 disabled:opacity-40 disabled:pointer-events-none transition-colors flex items-center gap-2"
              >
                Bulk delete
              </button>
            </div>
          )}
        </div>

        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          <DisciplineSummary activeTab={activeTab} />
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
                  className="w-4 h-4 rounded border-slate-300"
                  aria-label={
                    filteredData.length === 0 ? "Select incidents" : "Select all in this discipline"
                  }
                  disabled={filteredData.length === 0}
                  checked={filteredData.length > 0 && allChecked}
                  onChange={() => onToggleCheckedAllVisible(visibleIds)}
                />
              </th>
              <th className="p-5">Issue Title</th>
              <th className="p-5">Incident ID</th>
              <th className="p-5">Priority</th>
              <th className="p-5">Status</th>
              <th className="p-5">Location</th>
              <th className="p-5 text-right font-bold text-blue-600 uppercase">First Reported</th>
              <th className="p-5 text-right font-bold text-blue-600 uppercase">Age</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={8} className="p-20 text-center text-slate-400 italic">
                  No reports currently active for {activeTab}.
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr
                  key={item.incident_id}
                  onClick={() => onSelectIncident(item)}
                  className={`cursor-pointer transition-all group ${selectedIncidentId === item.incident_id
                      ? "bg-blue-50"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <td className="p-5" onClick={(e) => e.stopPropagation()}>
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-slate-300 text-blue-600"
                      aria-label={`Select issue ${item.incident_id.slice(0, 8)}`}
                      checked={checkedIds.has(item.incident_id)}
                      onChange={() => onToggleCheckedOne(item.incident_id)}
                    />
                  </td>
                  <td className="p-5 font-bold text-slate-2000">{item.vlm_summary}</td>
                  <td className="p-5 font-mono text-xs text-slate-400">
                    #{item.incident_id.slice(0, 8)}
                  </td>
                  <td className="p-5">
                    <div
                      className={issuePriorityDotClassFromRaw(item.issue_priority)}
                      title={`Priority: ${normalizeIssuePriority(item.issue_priority)}`}
                    />
                  </td>
                  <td className="p-5 text-xs font-semibold text-slate-600">
                    {item.status ?? "—"}
                  </td>
                  <td className="p-5 text-xs font-semibold text-slate-600 uppercase tracking-tighter">
                    {item.location_id}
                  </td>
                  <td className="p-5 text-right font-mono text-xs font-bold text-slate-500">
                    {formatShortDate(item.created_at)}
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
    </div>
  );
}
