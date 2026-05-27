import React from "react";
import { Scale } from "lucide-react";

interface Props {
  report: string;
}

export default function CompareTable({ report }: Props) {
  if (!report) {
    return (
      <div className="flex flex-col items-center justify-center h-full text-slate-400 gap-3">
        <Scale className="w-12 h-12 text-slate-200" />
        <p className="text-sm">对比分析将在文献解析完成后自动生成</p>
      </div>
    );
  }

  return (
    <div className="report-content px-1 h-full overflow-y-auto">
      <MarkdownToHtml content={report} />
    </div>
  );
}

/** 简易的 Markdown → HTML（仅用于对比分析的简单场景） */
function MarkdownToHtml({ content }: { content: string }) {
  // 按段落拆分，简单处理
  const lines = content.split("\n");
  const elements: React.JSX.Element[] = [];

  let i = 0;
  while (i < lines.length) {
    const line = lines[i];

    if (line.startsWith("# ")) {
      elements.push(
        <h1 key={i} className="text-2xl font-bold text-slate-900 mt-6 mb-4">
          {line.slice(2)}
        </h1>,
      );
    } else if (line.startsWith("## ")) {
      elements.push(
        <h2 key={i} className="text-lg font-semibold text-slate-800 mt-5 mb-3">
          {line.slice(3)}
        </h2>,
      );
    } else if (line.startsWith("- ")) {
      elements.push(
        <li key={i} className="text-sm text-slate-600 ml-4 mb-1 list-disc">
          {line.slice(2)}
        </li>,
      );
    } else if (line.trim() === "") {
      elements.push(<div key={i} className="h-2" />);
    } else {
      elements.push(
        <p key={i} className="text-sm text-slate-600 mb-2 leading-relaxed">
          {line}
        </p>,
      );
    }
    i++;
  }

  return <div>{elements}</div>;
}
