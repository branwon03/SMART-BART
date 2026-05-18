type DisciplineSidebarProps = {
  disciplines: readonly string[];
  activeTab: string;
  onSelectDiscipline: (discipline: string) => void;
};

export function DisciplineSidebar({
  disciplines,
  activeTab,
  onSelectDiscipline,
}: DisciplineSidebarProps) {
  return (
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
            type="button"
            onClick={() => onSelectDiscipline(item)}
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
    </aside>
  );
}
