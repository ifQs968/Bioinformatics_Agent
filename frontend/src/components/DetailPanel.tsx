import { X, ExternalLink, BookOpen, Users, Calendar } from "lucide-react";

interface PaperDetail {
  pubmed_id: string;
  title: string;
  abstract: string;
  authors: string[];
  journal: string;
  publication_date: string;
  doi: string;
  url: string;
  objective?: string;
  method?: string;
  target?: string;
  key_findings?: string;
  conclusion?: string;
}

interface Props {
  paper: PaperDetail | null;
  onClose: () => void;
}

export default function DetailPanel({ paper, onClose }: Props) {
  if (!paper) return null;

  return (
    <div className="border-l border-slate-200 bg-white w-96 shrink-0 overflow-y-auto animate-in slide-in-from-right duration-300">
      {/* Header */}
      <div className="sticky top-0 bg-white border-b border-slate-100 px-4 py-3 flex items-center justify-between z-10">
        <div className="flex items-center gap-2">
          <BookOpen className="w-4 h-4 text-blue-500" />
          <span className="text-sm font-semibold text-slate-700">文献详情</span>
        </div>
        <button
          onClick={onClose}
          className="p-1 hover:bg-slate-100 rounded-lg transition-colors"
        >
          <X className="w-4 h-4 text-slate-400" />
        </button>
      </div>

      <div className="p-4 space-y-4">
        {/* 标题 */}
        <h2 className="text-base font-semibold text-slate-900 leading-snug">
          {paper.title}
        </h2>

        {/* 元信息 */}
        <div className="space-y-2 text-xs text-slate-500">
          <div className="flex items-center gap-2">
            <Users className="w-3.5 h-3.5" />
            <span>{paper.authors?.slice(0, 3).join(", ") || "N/A"}
              {(paper.authors?.length || 0) > 3 ? " et al." : ""}</span>
          </div>
          <div className="flex items-center gap-2">
            <Calendar className="w-3.5 h-3.5" />
            <span>{paper.journal || "N/A"} · {paper.publication_date || "N/A"}</span>
          </div>
          {paper.doi && (
            <div className="text-[11px] text-slate-400">
              DOI: {paper.doi}
            </div>
          )}
        </div>

        {/* PubMed 链接 */}
        <a
          href={paper.url}
          target="_blank"
          rel="noopener noreferrer"
          className="inline-flex items-center gap-1.5 text-xs text-blue-600 hover:text-blue-700
                     bg-blue-50 hover:bg-blue-100 px-3 py-1.5 rounded-lg transition-colors"
        >
          <ExternalLink className="w-3 h-3" />
          在 PubMed 中查看
        </a>

        {/* 结构化信息 */}
        {paper.objective && (
          <InfoBlock label="研究目标" content={paper.objective} />
        )}
        {paper.method && (
          <InfoBlock label="方法" content={paper.method} />
        )}
        {paper.target && (
          <InfoBlock label="靶点 / 对象" content={paper.target} />
        )}
        {paper.key_findings && (
          <InfoBlock label="关键发现" content={paper.key_findings} />
        )}
        {paper.conclusion && (
          <InfoBlock label="结论" content={paper.conclusion} />
        )}

        {/* 摘要 */}
        {paper.abstract && (
          <div>
            <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-2">
              摘要
            </h4>
            <p className="text-sm text-slate-600 leading-relaxed">
              {paper.abstract.slice(0, 500)}
              {paper.abstract.length > 500 ? "..." : ""}
            </p>
          </div>
        )}
      </div>
    </div>
  );
}

function InfoBlock({ label, content }: { label: string; content: string }) {
  return (
    <div>
      <h4 className="text-xs font-semibold text-slate-400 uppercase tracking-wider mb-1.5">
        {label}
      </h4>
      <p className="text-sm text-slate-700 leading-relaxed">{content}</p>
    </div>
  );
}
