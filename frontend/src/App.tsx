import { useState, useCallback } from "react";
import Header from "./components/Header";
import Sidebar from "./components/Sidebar";
import DAGFlow from "./components/DAGFlow";
import ReportView from "./components/ReportView";
import CompareTable from "./components/CompareTable";
import DetailPanel from "./components/DetailPanel";
import { useResearch } from "./hooks/useResearch";

type Tab = "report" | "compare" | "dag";

export default function App() {
  const [query, setQuery] = useState("");
  const [maxPapers, setMaxPapers] = useState(5);
  const [activeTab, setActiveTab] = useState<Tab>("report");
  const [selectedPmid, setSelectedPmid] = useState<string | null>(null);

  const {
    loading,
    currentStep,
    subTasks,
    comparisonReport,
    finalReport,
    errors,
    stats,
    start,
    getPaperByPmid,
  } = useResearch();

  const handleSubmit = useCallback(() => {
    if (!query.trim() || loading) return;
    setSelectedPmid(null);
    start(query, maxPapers);
  }, [query, maxPapers, loading, start]);

  const handlePmidClick = useCallback((pmid: string) => {
    setSelectedPmid((prev) => (prev === pmid ? null : pmid));
  }, []);

  const tabs: { id: Tab; label: string }[] = [
    { id: "report", label: "最终报告" },
    { id: "compare", label: "对比分析" },
    { id: "dag", label: "任务流程" },
  ];

  return (
    <div className="h-screen flex flex-col bg-slate-50">
      <Header />

      <div className="flex flex-1 overflow-hidden">
        <Sidebar
          query={query}
          onQueryChange={setQuery}
          maxPapers={maxPapers}
          onMaxPapersChange={setMaxPapers}
          onSubmit={handleSubmit}
          loading={loading}
          stats={stats}
        />

        <main className="flex-1 flex flex-col min-w-0">
          {/* Tab 栏 */}
          <div className="flex items-center gap-0 px-6 pt-4 pb-0 border-b border-slate-100 bg-white">
            {tabs.map((tab) => (
              <button
                key={tab.id}
                onClick={() => setActiveTab(tab.id)}
                className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-[1px] transition-colors ${
                  activeTab === tab.id
                    ? "border-blue-600 text-blue-600"
                    : "border-transparent text-slate-400 hover:text-slate-600"
                }`}
              >
                {tab.label}
              </button>
            ))}

            {loading && (
              <div className="ml-auto flex items-center gap-2 pr-4">
                <span className="w-2 h-2 bg-blue-500 rounded-full animate-pulse" />
                <span className="text-xs text-slate-500">{currentStep}</span>
              </div>
            )}
            {errors.length > 0 && !loading && (
              <div className="ml-auto flex items-center gap-2 pr-4">
                <span className="w-2 h-2 bg-red-500 rounded-full" />
                <span className="text-xs text-red-500">{errors[0]}</span>
              </div>
            )}
          </div>

          {/* Tab 内容 */}
          <div className="flex-1 overflow-y-auto px-8 py-6">
            {activeTab === "report" && (
              <ReportView
                report={finalReport}
                loading={loading}
                onPmidClick={handlePmidClick}
              />
            )}
            {activeTab === "compare" && (
              <CompareTable report={comparisonReport} />
            )}
            {activeTab === "dag" && (
              <div className="max-w-2xl mx-auto">
                <h2 className="text-lg font-semibold text-slate-800 mb-4">
                  任务执行流程
                </h2>
                <DAGFlow subTasks={subTasks} />
              </div>
            )}
          </div>
        </main>

        {selectedPmid && (
          <DetailPanel
            paper={getPaperByPmid(selectedPmid)}
            onClose={() => setSelectedPmid(null)}
          />
        )}
      </div>
    </div>
  );
}
