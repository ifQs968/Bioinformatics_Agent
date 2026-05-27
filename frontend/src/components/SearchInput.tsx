import { Search, Loader2 } from "lucide-react";

interface Props {
  value: string;
  onChange: (v: string) => void;
  maxPapers: number;
  onMaxPapersChange: (v: number) => void;
  onSubmit: () => void;
  loading: boolean;
}

export default function SearchInput({
  value,
  onChange,
  maxPapers,
  onMaxPapersChange,
  onSubmit,
  loading,
}: Props) {
  return (
    <div className="space-y-4">
      {/* 输入框 */}
      <div className="relative">
        <textarea
          value={value}
          onChange={(e) => onChange(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === "Enter" && !e.shiftKey) {
              e.preventDefault();
              onSubmit();
            }
          }}
          placeholder="输入你的生物医学研究问题...
例如：对比近三年针对 EGFR 靶点的 NSCLC 临床研究中
PD-1 抑制剂的疗效与安全性数据"
          rows={5}
          disabled={loading}
          className="w-full px-4 py-3 text-sm text-slate-700 bg-white border border-slate-200
                     rounded-xl resize-none placeholder:text-slate-400
                     focus:outline-none focus:ring-2 focus:ring-blue-500/20 focus:border-blue-400
                     disabled:opacity-50 disabled:cursor-not-allowed
                     transition-all"
        />
      </div>

      {/* 参数滑块 */}
      <div>
        <div className="flex justify-between items-center mb-2">
          <label className="text-xs font-medium text-slate-500">
            最大文献数
          </label>
          <span className="text-xs font-semibold text-blue-600 bg-blue-50 px-2 py-0.5 rounded-full">
            {maxPapers} 篇
          </span>
        </div>
        <input
          type="range"
          min={2}
          max={20}
          value={maxPapers}
          onChange={(e) => onMaxPapersChange(Number(e.target.value))}
          disabled={loading}
          className="w-full h-1.5 bg-slate-200 rounded-full appearance-none cursor-pointer
                     accent-blue-600 disabled:opacity-50"
        />
        <div className="flex justify-between mt-1">
          <span className="text-[10px] text-slate-400">2</span>
          <span className="text-[10px] text-slate-400">20</span>
        </div>
      </div>

      {/* 搜索按钮 */}
      <button
        onClick={onSubmit}
        disabled={loading || !value.trim()}
        className="w-full py-2.5 px-4 bg-blue-600 hover:bg-blue-700 active:bg-blue-800
                   text-white text-sm font-medium rounded-xl
                   disabled:opacity-50 disabled:cursor-not-allowed
                   flex items-center justify-center gap-2
                   transition-all shadow-sm shadow-blue-600/10"
      >
        {loading ? (
          <>
            <Loader2 className="w-4 h-4 animate-spin" />
            分析中...
          </>
        ) : (
          <>
            <Search className="w-4 h-4" />
            开始研究
          </>
        )}
      </button>
    </div>
  );
}
