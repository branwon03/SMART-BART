import { useCallback, useEffect, useMemo, useState } from "react";
import type { Incident, PhotoReport } from "../types/api";
import { getIncidents, getPhotoReports } from "../lib/incidents";

export const MAINTENANCE_DISCIPLINES = [
  "FARE COLLECTION",
  "BUILDINGS",
  "COMMS",
  "ELEVATOR AND ESCALATOR",
  "GROUNDS",
  "MECHANICAL",
  "SYSTEM SERVICE",
  "ELECTRICAL",
] as const;

const INCIDENTS_POLL_MS = 10_000;
const CLOCK_TICK_MS = 60_000;

export function useMaintenanceDashboard() {
  const [data, setData] = useState<Incident[]>([]);
  const [activeTab, setActiveTab] = useState("ELECTRICAL");
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<PhotoReport[]>([]);
  const [now, setNow] = useState(() => new Date());
  const [incidentIdExpanded, setIncidentIdExpanded] = useState(false);


  const fetchData = useCallback(async () => {
    try {
      const json = await getIncidents();
      setData(json);

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
    const clockInterval = setInterval(() => setNow(new Date()), CLOCK_TICK_MS);
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
  }, []);

  const updateSelectedIncident = useCallback((updated: Incident) => {
    setData((prev) =>
      prev.map((inc) => (inc.incident_id === updated.incident_id ? updated : inc)),
    );
    setSelectedIncident((prev) =>
      prev && prev.incident_id === updated.incident_id ? updated : prev,
    );
  }, []);

  const removeIncident = useCallback((incidentId: string) => {
    setData((prev) => prev.filter((inc) => inc.incident_id !== incidentId));
    setSelectedIncident((prev) =>
      prev && prev.incident_id === incidentId ? null : prev,
    );
    setEvidence([]);
    setIncidentIdExpanded(false);
  }, []);

  const notifyIncidentSplitForParent = useCallback(
    (parentIncidentId: string) => {
      void fetchData();
      void fetchEvidence(parentIncidentId);
    },
    [fetchData, fetchEvidence],
  );

  return {
    disciplines: MAINTENANCE_DISCIPLINES,
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
    notifyIncidentSplitForParent,
  };
}
