"use client";

import { useCallback, useMemo, useState } from "react";
import { DisciplineSidebar } from "../../components/DisciplineSidebar";
import { IncidentDetailPanel } from "../../components/IncidentDetailPanel";
import { IncidentsTable } from "../../components/IncidentsTable";
import { BulkEditModal } from "../../components/BulkEditModal";
import { BulkDeleteModal } from "../../components/BulkDeleteModal";
import { useMaintenanceDashboard } from "../../hooks/useMaintenanceDashboard";

export default function MaintenanceDashboard() {
  const {
    disciplines,
    activeTab,
    filteredData,
    allIncidents,
    selectedIncident,
    setSelectedIncident,
    checkedIds,
    toggleCheckedOne,
    toggleCheckedAllVisible,
    clearCheckedIds,
    evidence,
    now,
    incidentIdExpanded,
    setIncidentIdExpanded,
    selectDiscipline,
    closeIncidentPanel,
    updateSelectedIncident,
    removeIncident,
    refreshAfterMerge,
    notifyIncidentSplitForParent,
  } = useMaintenanceDashboard();

  const [bulkEditOpen, setBulkEditOpen] = useState(false);
  const [bulkDeleteOpen, setBulkDeleteOpen] = useState(false);

  const selectedForBulk = useMemo(
    () => filteredData.filter((i) => checkedIds.has(i.incident_id)),
    [filteredData, checkedIds],
  );

  const handleSelectDiscipline = useCallback(
    (d: string) => {
      setBulkEditOpen(false);
      setBulkDeleteOpen(false);
      selectDiscipline(d);
    },
    [selectDiscipline],
  );

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans text-sm overflow-x-hidden">
      <DisciplineSidebar
        disciplines={disciplines}
        activeTab={activeTab}
        onSelectDiscipline={handleSelectDiscipline}
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
            checkedIds={checkedIds}
            onSelectIncident={setSelectedIncident}
            onToggleCheckedOne={toggleCheckedOne}
            onToggleCheckedAllVisible={toggleCheckedAllVisible}
            onBulkEditRequest={() => setBulkEditOpen(true)}
            onBulkDeleteRequest={() => setBulkDeleteOpen(true)}
          />
        </main>

        {selectedIncident && (
          <IncidentDetailPanel
            key={selectedIncident.incident_id}
            incident={selectedIncident}
            evidence={evidence}
            allIncidents={allIncidents}
            incidentIdExpanded={incidentIdExpanded}
            onToggleIncidentIdExpanded={() => setIncidentIdExpanded((e) => !e)}
            onClose={closeIncidentPanel}
            onIncidentUpdated={updateSelectedIncident}
            onIncidentDeleted={removeIncident}
            onRefreshAfterMerge={refreshAfterMerge}
            onIncidentSplit={notifyIncidentSplitForParent}
          />
        )}

        {bulkEditOpen && selectedForBulk.length > 0 && (
          <BulkEditModal
            incidents={selectedForBulk}
            onApplied={(updates) => {
              for (const u of updates) {
                updateSelectedIncident(u);
              }
              clearCheckedIds();
            }}
            onClose={() => setBulkEditOpen(false)}
          />
        )}

        {bulkDeleteOpen && selectedForBulk.length > 0 && (
          <BulkDeleteModal
            incidents={selectedForBulk}
            onApplied={(deletedIds) => {
              for (const id of deletedIds) {
                removeIncident(id);
              }
              clearCheckedIds();
            }}
            onClose={() => setBulkDeleteOpen(false)}
          />
        )}
      </div>
    </div>
  );
}
