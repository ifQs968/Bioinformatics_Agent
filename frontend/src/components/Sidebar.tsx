import { Activity } from "lucide-react";
import SearchInput from "./SearchInput";

interface Props {
  query: string;
  onQueryChange: (v: string) => void;
  maxPapers: number;
  onMaxPapersChange: (v: number) => void;
  onSubmit: () => void;
  loading: boolean;
  stats: { searchResults: number; selectedPapers: number; parsedPapers: number };
}

export default function Sidebar({
  query,
  onQueryChange,
  maxPapers,
  onMaxPapersChange,
  onSubmit,
  loading,
  stats,
}: Props) {
  return (
    <aside className="w-80 shrink-0 border-r border-slate-200 bg-white flex flex-col">
      <div className="p-4 border-b border-slate-100">
        <SearchInput
          value={query}
          onChange={onQueryChange}
          maxPapers={maxPapers}
          onMaxPapersChange={onMaxPapersChange}
          onSubmit={onSubmit}
          loading={loading}
        />
      </div>

      {stats.searchResults > 0 && (
        <div className="px-4 py-3">
          <div className="flex items-center gap-1 mb-2">
            <Activity className="w-3.5 h-3.5 text-slate-400" />
            <span className="text-xs font-semibold text-slate-400 uppercase tracking-wider">
              检索统计
            </span>
          </div>
          <div className="grid grid-cols-3 gap-2">
            <StatBox label="检索" value={stats.searchResults} />
            <StatBox label="筛选" value={stats.selectedPapers} />
            <StatBox label="解析" value={stats.parsedPapers} />
          </div>
        </div>
      )}

      {/* 底部提示 */}
      <div className="mt-auto p-4 border-t border-slate-100">
        <p className="text-[11px] text-slate-400 leading-relaxed">
          输入具体的研究问题（含靶点、疾病、干预方式），Agent 将自动检索、解析并生成结构化报告。
        </p>
      </div>
    </aside>
  );
}

function StatBox({ label, value }: { label: string; value: number }) {
  return (
    <div className="text-center bg-slate-50 rounded-lg py-2">
      <div className="text-lg font-bold text-blue-600">{value}</div>
      <div className="text-[10px] text-slate-400">{label}</div>
    </div>
  );
}
