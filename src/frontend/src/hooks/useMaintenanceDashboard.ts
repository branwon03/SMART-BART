import { useCallback, useEffect, useMemo, useRef, useState } from "react";
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

  const selectedIncidentRef = useRef(selectedIncident);
  selectedIncidentRef.current = selectedIncident;

  const fetchData = useCallback(async () => {
    try {
      const json = await getIncidents();
      setData(json);
      const current = selectedIncidentRef.current;
      if (current) {
        const updated = json.find((i) => i.incident_id === current.incident_id);
        if (updated) setSelectedIncident(updated);
      }
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
    void fetchData();
    const dataInterval = setInterval(() => void fetchData(), INCIDENTS_POLL_MS);
    const clockInterval = setInterval(() => setNow(new Date()), CLOCK_TICK_MS);
    return () => {
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, [fetchData]);

  useEffect(() => {
    const id = selectedIncident?.incident_id;
    if (id) {
      void fetchEvidence(id);
    } else {
      setEvidence([]);
    }
  }, [selectedIncident?.incident_id, fetchEvidence]);

  useEffect(() => {
    setIncidentIdExpanded(false);
  }, [selectedIncident?.incident_id]);

  const filteredData = useMemo(
    () => data.filter((item) => item.discipline === activeTab),
    [data, activeTab],
  );

  const selectDiscipline = useCallback((discipline: string) => {
    setActiveTab(discipline);
    setSelectedIncident(null);
  }, []);

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
  };
}
