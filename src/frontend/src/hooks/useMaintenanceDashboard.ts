import { useCallback, useEffect, useMemo, useState } from "react";
import type { Incident, PhotoReport } from "../types/api";
import { MAINTENANCE_DISCIPLINES } from "../lib/disciplines";
import { getIncidents, getPhotoReports } from "../lib/incidents";

const INCIDENTS_POLL_MS = 10_000;
/** Server time display + incidents age column reference (same tick). */
const DASHBOARD_CLOCK_MS = 60_000;

export function useMaintenanceDashboard() {
  const [data, setData] = useState<Incident[]>([]);
  const [activeTab, setActiveTab] = useState("FARE COLLECTION");
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<PhotoReport[]>([]);
  const [now, setNow] = useState(() => new Date());
  const [incidentIdExpanded, setIncidentIdExpanded] = useState(false);
  const [checkedIds, setCheckedIds] = useState<Set<string>>(new Set());

  const fetchData = useCallback(async () => {
    try {
      const json = await getIncidents();
      setData(json);

      const validIds = new Set(json.map((i) => i.incident_id));
      setCheckedIds((prev) => {
        const next = new Set<string>();
        for (const id of prev) {
          if (validIds.has(id)) next.add(id);
        }
        return next;
      });

      setSelectedIncident((prevSelectedIncident) => {
        if (!prevSelectedIncident) {
          return prevSelectedIncident;
        }
        const updated = json.find((i) => i.incident_id === prevSelectedIncident.incident_id);
        return updated ?? prevSelectedIncident;
      });

    } catch (err) {
      console.error("Fetch incidents failed:", err);
    }
  }, []);

  const fetchEvidence = useCallback(async (incidentId: string) => {
    try {
      const json = await getPhotoReports(incidentId);
      setEvidence(json);
    } catch (err) {
      console.error("Fetch evidence failed:", err);
    }
  }, []);

  useEffect(() => {
    const tick = () => {
      void fetchData();
    };
    const initialTimeout = setTimeout(tick, 0);
    const dataInterval = setInterval(tick, INCIDENTS_POLL_MS);
    const clockInterval = setInterval(() => setNow(new Date()), DASHBOARD_CLOCK_MS);
    return () => {
      clearTimeout(initialTimeout);
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, [fetchData]);

  useEffect(() => {
    if (!selectedIncident?.incident_id) return;
    const incidentId = selectedIncident.incident_id;
    const timeoutId = setTimeout(() => {
      void fetchEvidence(incidentId);
    }, 0);
    return () => clearTimeout(timeoutId);
  }, [fetchEvidence, selectedIncident?.incident_id]);

  const filteredData = useMemo(
    () => data.filter((item) => item.discipline === activeTab),
    [data, activeTab],
  );

  const selectDiscipline = useCallback((discipline: string) => {
    setActiveTab(discipline);
    setSelectedIncident(null);
    setEvidence([]);
    setIncidentIdExpanded(false);
    setCheckedIds(new Set());
  }, []);

  const closeIncidentPanel = useCallback(() => {
    setSelectedIncident(null);
    setEvidence([]);
    setIncidentIdExpanded(false);
  }, []);

  const toggleCheckedOne = useCallback((id: string) => {
    setCheckedIds((prev) => {
      const next = new Set(prev);
      if (next.has(id)) next.delete(id);
      else next.add(id);
      return next;
    });
  }, []);

  const toggleCheckedAllVisible = useCallback((visibleIds: string[]) => {
    if (visibleIds.length === 0) return;
    setCheckedIds((prev) => {
      const allIncluded = visibleIds.every((id) => prev.has(id));
      const next = new Set(prev);
      if (allIncluded) {
        for (const id of visibleIds) next.delete(id);
      } else {
        for (const id of visibleIds) next.add(id);
      }
      return next;
    });
  }, []);

  const clearCheckedIds = useCallback(() => setCheckedIds(new Set()), []);

  const updateSelectedIncident = useCallback((updated: Incident) => {
    setData((prev) =>
      prev.map((inc) =>
        inc.incident_id === updated.incident_id ? { ...inc, ...updated } : inc,
      ),
    );
    setSelectedIncident((prev) =>
      prev && prev.incident_id === updated.incident_id
        ? { ...prev, ...updated }
        : prev,
    );
  }, []);

  const removeIncident = useCallback((incidentId: string) => {
    setData((prev) => prev.filter((inc) => inc.incident_id !== incidentId));
    setCheckedIds((prev) => {
      const next = new Set(prev);
      next.delete(incidentId);
      return next;
    });
    setSelectedIncident((prev) => {
      if (prev && prev.incident_id === incidentId) {
        setEvidence([]);
        setIncidentIdExpanded(false);
        return null;
      }
      return prev;
    });
  }, []);

  const refreshAfterMerge = useCallback(
    async (openIncidentId: string) => {
      await fetchData();
      await fetchEvidence(openIncidentId);
    },
    [fetchData, fetchEvidence],
  );

  const notifyIncidentSplitForParent = useCallback(
    (parentIncidentId: string) => {
      void fetchData();
      void fetchEvidence(parentIncidentId);
    },
    [fetchData, fetchEvidence],
  );

  return {
    allIncidents: data,
    disciplines: MAINTENANCE_DISCIPLINES,
    activeTab,
    filteredData,
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
  };
}
