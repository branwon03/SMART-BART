import { useEffect, useState } from "react";
import type { DisciplineStat } from "./IncidentsTable";

type DisciplineSummaryProps = {
  activeTab: string;
};

export function DisciplineSummary({ activeTab }: DisciplineSummaryProps) {
  const [stats, setStats] = useState<DisciplineStat[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    fetch("/api/dashboard/discipline-stats")
      .then((res) => res.json())
      .then((data) => {
        setStats(data);
        setLoading(false);
      })
      .catch((err) => console.error("Stats fetch error:", err));
  }, []);

  if (loading || !activeTab) return null;

  const currentStat = stats.find(
    (s) => s.discipline?.toUpperCase() === activeTab.toUpperCase()
  );

  if (!currentStat) return null;

  const start = currentStat.first_report ? new Date(currentStat.first_report).toLocaleDateString() : "N/A";
  const end = currentStat.last_report ? new Date(currentStat.last_report).toLocaleDateString() : "N/A";

  return (
    <div className="flex gap-4 text-[10px] font-bold text-slate-400 uppercase tracking-widest">
      <span>Start: {start}</span>
      <span>End: {end}</span>
    </div>
  );
}