import type { Incident } from "../types/api";
import { formatElapsedSince } from "../lib/formatElapsedSince";
import { isHighPriority } from "../lib/priorityUi";

type IncidentsTableProps = {
  activeTab: string;
  filteredData: Incident[];
  selectedIncidentId: string | null;
  now: Date;
  onSelectIncident: (incident: Incident) => void;
};

export function IncidentsTable({
  activeTab,
  filteredData,
  selectedIncidentId,
  now,
  onSelectIncident,
}: IncidentsTableProps) {
  return (
    <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
      <div className="p-4 bg-white border-b border-slate-100 flex items-center justify-between">
        <button
          type="button"
          className="bg-blue-500 text-white px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:bg-blue-600 transition-colors"
        >
          Actions <span>▼</span>
        </button>
        <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
          {filteredData.length} Total Records
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead className="bg-slate-50 text-[10px] uppercase tracking-widest text-slate-400 font-black border-b border-slate-100">
            <tr>
              <th className="p-5 w-12">
                <input type="checkbox" className="w-4 h-4 rounded border-slate-300" />
              </th>
              <th className="p-5">Issue Title</th>
              <th className="p-5">Incident ID</th>
              <th className="p-5">Priority</th>
              <th className="p-5">Location</th>
              <th className="p-5 text-right font-bold text-blue-600 uppercase">Time Elapsed</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-50">
            {filteredData.length === 0 ? (
              <tr>
                <td colSpan={6} className="p-20 text-center text-slate-400 italic">
                  No reports currently active for {activeTab}.
                </td>
              </tr>
            ) : (
              filteredData.map((item) => (
                <tr
                  key={item.incident_id}
                  onClick={() => onSelectIncident(item)}
                  className={`cursor-pointer transition-all group ${
                    selectedIncidentId === item.incident_id
                      ? "bg-blue-50"
                      : "hover:bg-slate-50"
                  }`}
                >
                  <td className="p-5">
                    <input
                      type="checkbox"
                      className="w-4 h-4 rounded border-slate-300 text-blue-600"
                    />
                  </td>
                  <td className="p-5 font-bold text-slate-700">{item.vlm_summary}</td>
                  <td className="p-5 font-mono text-xs text-slate-400">
                    #{item.incident_id.slice(0, 8)}
                  </td>
                  <td className="p-5">
                    <div
                      className={`h-1.5 w-10 rounded-full ${
                        isHighPriority(item.issue_priority)
                          ? "bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)]"
                          : "bg-yellow-400"
                      }`}
                    />
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
    </div>
  );
}
