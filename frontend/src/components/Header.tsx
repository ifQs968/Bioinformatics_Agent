import { Dna, Settings } from "lucide-react";

export default function Header() {
  return (
    <header className="h-14 border-b border-slate-200 bg-white flex items-center justify-between px-6 shrink-0">
      <div className="flex items-center gap-3">
        <div className="w-8 h-8 bg-blue-600 rounded-lg flex items-center justify-center">
          <Dna className="w-5 h-5 text-white" />
        </div>
        <div>
          <h1 className="text-base font-semibold text-slate-900 leading-none">
            Bioinformatics Agent
          </h1>
          <p className="text-xs text-slate-400 leading-none mt-0.5">
            AI 驱动的生物医学文献智能分析
          </p>
        </div>
      </div>

      <div className="flex items-center gap-2">
        <span className="text-xs text-slate-400 bg-slate-100 px-2 py-1 rounded">
          DeepSeek
        </span>
        <button className="p-2 hover:bg-slate-100 rounded-lg transition-colors">
          <Settings className="w-4 h-4 text-slate-400" />
        </button>
      </div>
    </header>
  );
}
