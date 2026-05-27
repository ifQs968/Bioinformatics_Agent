/** Planner 拆解的单个子任务 */
export interface SubTask {
  id: string;
  type: "search" | "parse" | "compare" | "report";
  description: string;
  depends_on: string[];
  status: "pending" | "running" | "done" | "failed";
}

/** 论文详情（含结构化提取数据） */
export interface PaperDetail {
  pubmed_id: string;
  title: string;
  abstract: string;
  authors: string[];
  journal: string;
  publication_date: string;
  doi: string;
  url: string;
  objective: string;
  method: string;
  target: string;
  key_findings: string;
  conclusion: string;
}

/** SSE 事件推送的研究状态快照 */
export interface ResearchSnapshot {
  current_step: string;
  plan_summary: string;
  sub_tasks: SubTask[];
  execution_log: string[];
  search_results_count: number;
  selected_papers_count: number;
  parsed_papers_count: number;
  comparison_report: string;
  final_report: string;
  errors: string[];
  papers: PaperDetail[];
}
