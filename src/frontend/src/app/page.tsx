"use client"
import { useCallback, useEffect, useState } from 'react';
import type { Incident, PhotoReport } from "../types/api";
import { getIncidents, getPhotoReports } from "../lib/incidents";
import { API_BASE_URL } from "../lib/config";


export default function MaintenanceDashboard() {
  const [data, setData] = useState<Incident[]>([]);
  const [activeTab, setActiveTab] = useState("ELECTRICAL");
  const [selectedIncident, setSelectedIncident] = useState<Incident | null>(null);
  const [evidence, setEvidence] = useState<PhotoReport[]>([]);
  const [now, setNow] = useState(new Date());

  const disciplines = [
    "FARE COLLECTION", "BUILDINGS", "COMMS",
    "ELEVATOR AND ESCALATOR", "GROUNDS", "MECHANICAL",
    "SYSTEM SERVICE", "STRUCTURES", "TRACK",
    "ELECTRICAL", "RSS",
  ];


  const filteredData = data.filter((item) => item.discipline === activeTab);


  const formatElapsed = (isoString: string | null | undefined) => {
    if (!isoString) return "0m";
    const start = new Date(isoString);
    const diffInMs = now.getTime() - start.getTime();
    const totalMinutes = Math.floor(diffInMs / (1000 * 60));
    const hours = Math.floor(totalMinutes / 60);
    const mins = totalMinutes % 60;
    return hours > 0 ? `${hours}h ${mins}m` : `${mins}m`;
  };


  const fetchData = useCallback(async () => {
    try {
      const json = await getIncidents();
      setData(json);
     
    
      setSelectedIncident((prevSelectedIncident) => {
        if (!prevSelectedIncident) return prevSelectedIncident;
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
    const initialFetchTimeout = setTimeout(() => {
      void fetchData();
    }, 0);
    const dataInterval = setInterval(() => {
      void fetchData();
    }, 10000);
    const clockInterval = setInterval(() => setNow(new Date()), 60000);
    return () => {
      clearTimeout(initialFetchTimeout);
      clearInterval(dataInterval);
      clearInterval(clockInterval);
    };
  }, [fetchData]);

  return (
    <div className="flex min-h-screen bg-slate-50 text-slate-900 font-sans text-sm overflow-x-hidden">
     
      {/* LEFT SIDEBAR */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col p-6 fixed h-full shadow-sm z-10">
        <div className="flex flex-col items-center justify-center mb-4">
          <img
            src="/logo.png"
            alt="BART Logo"
            className="w-32 h-auto object-contain"
          />
          <div className="font-black text-[10px] tracking-[0.2em] text-slate-400 uppercase mt-3">
            Maintenance System
          </div>
        </div>


        <nav className="flex-1 space-y-1 overflow-y-auto mt-8">
          {disciplines.map((item) => (
            <button
              key={item}
              onClick={() => {
                setActiveTab(item);
                setSelectedIncident(null);
                setEvidence([]);
              }}
              className={`w-full text-left px-4 py-2.5 rounded-lg font-bold transition-all ${
                activeTab === item
                ? "bg-blue-50 text-blue-700 border-r-4 border-blue-600 shadow-sm"
                : "text-slate-500 hover:bg-slate-50 hover:text-slate-800"
              }`}
            >
              {item}
            </button>
          ))}
        </nav>


        <div className="pt-6 border-t border-slate-100 flex items-center gap-3">
          <div className="w-8 h-8 rounded-full bg-slate-200 flex items-center justify-center text-[10px] font-bold text-slate-500">AS</div>
          <div className="text-[10px] font-bold text-slate-400 uppercase tracking-tight">Akash Sant</div>
        </div>
      </aside>


      {/* MAIN CONTENT AREA */}
      <div className="flex-1 ml-64 relative">
        <main className="p-10">
          <header className="mb-10 flex justify-between items-end">
            <div>
              <h1 className="text-3xl font-black text-slate-800 tracking-tight leading-none">Maintenance Dashboard</h1>
              <p className="text-slate-400 font-medium uppercase text-[10px] tracking-widest mt-3">
                Viewing Discipline: <span className="text-blue-500">{activeTab}</span>
              </p>
            </div>
            <div className="text-right">
               <div className="text-[10px] font-bold text-slate-400 uppercase tracking-widest">Server Time</div>
               <div className="font-mono font-bold text-slate-600">{now.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}</div>
            </div>
          </header>


          {/* TABLE SECTION */}
          <div className="bg-white rounded-2xl shadow-sm border border-slate-200 overflow-hidden">
            <div className="p-4 bg-white border-b border-slate-100 flex items-center justify-between">
               <button className="bg-blue-500 text-white px-5 py-2 rounded-lg font-bold text-xs flex items-center gap-2 hover:bg-blue-600 transition-colors">
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
                    <th className="p-5 w-12"><input type="checkbox" className="w-4 h-4 rounded border-slate-300" /></th>
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
                    filteredData.map((item: Incident) => (
                      <tr
                        key={item.incident_id}
                        onClick={() => setSelectedIncident(item)}
                        className={`cursor-pointer transition-all group ${
                          selectedIncident?.incident_id === item.incident_id ? 'bg-blue-50' : 'hover:bg-slate-50'
                        }`}
                      >
                        <td className="p-5"><input type="checkbox" className="w-4 h-4 rounded border-slate-300 text-blue-600" /></td>
                        <td className="p-5 font-bold text-slate-700">{item.vlm_summary}</td>
                        <td className="p-5 font-mono text-xs text-slate-400">#{item.incident_id.slice(0,8)}</td>
                        <td className="p-5">
                          <div className={`h-1.5 w-10 rounded-full ${['HIGH', 'CRITICAL', '1'].includes(item.issue_priority) ? 'bg-red-500 shadow-[0_0_8px_rgba(239,68,68,0.3)]' : 'bg-yellow-400'}`} />
                        </td>
                        <td className="p-5 text-xs font-semibold text-slate-600 uppercase tracking-tighter">{item.location_id}</td>
                        <td className="p-5 text-right font-mono text-xs font-bold text-slate-500">
                          {formatElapsed(item.created_at)}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </main>


        {/* OVERLAY SIDEBAR */}
        {selectedIncident && (
          <>
            <div
              className="fixed inset-0 bg-black/20 z-20"
              onClick={() => {
                setSelectedIncident(null)
                setEvidence([]);
              }}
            />
           
            <aside className="fixed top-0 right-0 w-[450px] bg-white border-l-4 border-black h-screen p-6 shadow-2xl z-30 overflow-y-auto font-sans text-sm">
             
              <div className="border-b-2 border-gray-300 pb-4 mb-4 relative">
                <h2 className="text-xl font-bold mb-4 pr-32 leading-tight">{selectedIncident.vlm_summary}</h2>
               
                <div className="grid grid-cols-[100px_1fr] gap-y-2 text-sm">
                  <span className="font-bold text-gray-700">Incident ID:</span>
                  <span>{selectedIncident.incident_id}</span>
                 
                  <span className="font-bold text-gray-700">Priority:</span>
                  <span className={selectedIncident.issue_priority === 1 ? "text-black-500" : "text-yellow-600 font-bold"}>
                    {selectedIncident.issue_priority === 1 ? "TODO" : "Standard"}
                  </span>
                 
                  <span className="font-bold text-gray-700">Status:</span>
                  <span className="text-700">
                    {selectedIncident.status}
                  </span>
                 
                  <span className="font-bold text-gray-700">Location:</span>
                  <span>{selectedIncident.location_id}</span>
                 
                  <span className="font-bold text-gray-700">Age:</span>
                  <span>{formatElapsed(selectedIncident.created_at)}</span>
                </div>


                <div className="absolute top-10 right-0 flex flex-col gap-2 w-32">
                  <button className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100">
                    Begin
                  </button>
                  <button className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100">
                    Edit Issue
                  </button>
                  <button className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100">
                    Redirect
                  </button>
                  <button className="bg-white text-black font-bold py-1 rounded-lg border-2 border-black hover:bg-gray-100">
                    Merge/Split
                  </button>
                </div>
              </div>


              <div className="mb-6">
                <h3 className="font-bold text-lg mb-2">Description:</h3>
                <div className="bg-gray-100 border border-gray-300 rounded-lg p-4 h-48 overflow-y-auto text-[11px] leading-relaxed space-y-4">
                  {evidence.map((ev: PhotoReport, idx: number) => (
                    <div key={ev.evidence_id} className="border-b border-gray-200 pb-3 last:border-0">
                      <div className="flex justify-between font-bold text-gray-500 mb-1">
                        <span>Report summary {idx + 1}:</span>
                        <span>{new Date(ev.submitted_at).toLocaleTimeString()}</span>
                      </div>
                      <p className="text-gray-800">- &quot;{ev.user_context || "Rider report logged via web-app."}&quot;</p>
                     
                     
                    </div>
                  ))}
                  {evidence.length === 0 && <p className="text-gray-400 italic text-center py-4">No historical reports found.</p>}
                </div>
              </div>


              <div className="flex flex-col items-center">
                <div className="relative w-full aspect-square bg-gray-200 mb-8 border-2 border-gray-300 overflow-hidden rounded-none">
                  {evidence.length > 0 && evidence[0].image_url ? (
                    <img
                      src={evidence[0].image_url.startsWith('http') ? evidence[0].image_url : `${API_BASE_URL.replace(/\/api$/, '')}${evidence[0].image_url}`}
                      className="w-full h-full object-cover"
                      alt="Main evidence"
                    />
                  ) : (
                    <div className="flex items-center justify-center h-full text-gray-400">No Image Available</div>
                  )}
                  <button className="absolute left-2 top-1/2 -translate-y-1/2 text-2xl font-bold bg-white/50 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white transition-colors">←</button>
                  <button className="absolute right-2 top-1/2 -translate-y-1/2 text-2xl font-bold bg-white/50 w-8 h-8 rounded-full flex items-center justify-center hover:bg-white transition-colors">→</button>
                </div>


                <button
                  onClick={() => {
                    setSelectedIncident(null);
                    setEvidence([]);
                  }}
                  className="w-32 py-2 border-[3px] border-black rounded-lg font-black text-lg uppercase tracking-tighter hover:bg-gray-100 active:scale-95 transition-all">
                    Close
                  </button>
              </div>
            </aside>
          </>
        )}
      </div>
    </div>
  );
}

