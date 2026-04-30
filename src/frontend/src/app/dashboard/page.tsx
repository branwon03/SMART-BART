"use client";

import { DisciplineSidebar } from "../../components/DisciplineSidebar";
import { IncidentDetailPanel } from "../../components/IncidentDetailPanel";
import { IncidentsTable } from "../../components/IncidentsTable";
import { useMaintenanceDashboard } from "../../hooks/useMaintenanceDashboard";

export default function MaintenanceDashboard() {
  const {
    disciplines,
    activeTab,
    filteredData,
    selectedIncident,
    setSelectedIncident,
    evidence,
    now,
    incidentIdExpanded,
    setIncidentIdExpanded,
    selectDiscipline,
    updateSelectedIncident,
    removeIncident,
  } = useMaintenanceDashboard();

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans text-sm overflow-x-hidden">
      <DisciplineSidebar
        disciplines={disciplines}
        activeTab={activeTab}
        onSelectDiscipline={selectDiscipline}
      />

      <div className="flex-1 ml-64 relative">
        <main className="p-10">
          <header className="mb-10 flex justify-between items-end">
            <div>
              <h1 className="text-3xl font-black text-slate-800 tracking-tight leading-none">
                Maintenance Dashboard
              </h1>
              <p className="text-slate-400 font-medium uppercase text-[10px] tracking-widest mt-3">
                Viewing Discipline: <span className="text-blue-500">{activeTab}</span>
              </p>
            </div>
            <div className="text-right">
              <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">
                Server Time
              </div>
              <div className="font-mono font-bold text-slate-600">
                {now.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
              </div>
            </div>
          </header>

          <IncidentsTable
            activeTab={activeTab}
            filteredData={filteredData}
            selectedIncidentId={selectedIncident?.incident_id ?? null}
            now={now}
            onSelectIncident={setSelectedIncident}
          />
        </main>

        {selectedIncident && (
          <IncidentDetailPanel
            incident={selectedIncident}
            evidence={evidence}
            now={now}
            incidentIdExpanded={incidentIdExpanded}
            onToggleIncidentIdExpanded={() => setIncidentIdExpanded((e) => !e)}
            onClose={() => {
              setIncidentIdExpanded(false);
              setSelectedIncident(null);
            }}
            onIncidentUpdated={updateSelectedIncident}
            onIncidentDeleted={removeIncident}
          />
        )}
      </div>
    </div>
  );
}
