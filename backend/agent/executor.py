"""
Executor — 按 Planner 输出的任务 DAG 调度各 Worker 执行。
异步生成器版本，适配 FastAPI SSE 流式输出。
"""
import asyncio
from typing import Any, AsyncGenerator

from backend.tools.llm_client import llm
from backend.agent.state import ResearchState, SubTask
from backend.agent.planner import plan_tasks
from backend.agent.workers.search_worker import search_papers
from backend.agent.workers.parser_worker import parse_papers
from backend.agent.workers.compare_worker import compare_papers

WORKER_MAP = {
    "search": search_papers,
    "parse": parse_papers,
    "compare": compare_papers,
}

REPORT_SYSTEM_PROMPT = """你是一个生物医学文献综述撰写专家。请基于前面的分析结果，生成一份结构清晰的文献概览报告。

报告应包含以下部分（使用 Markdown 格式）：
1. **研究问题概述**：简述用户意图和检索范围
2. **文献概览**：逐篇介绍筛选出的文献（标题、作者、核心发现）
3. **对比分析**：引用 Compare Worker 的对比结果
4. **结论与建议**：总结当前研究现状，给出后续研究建议

要求：
- 每篇文献引用请标注 PubMed ID，格式: [PMID:xxxxx]
- 如果有图表提取结果，使用 ![](path) 格式嵌入
- 报告末尾标注生成时间和数据来源
"""


async def execute_research(
    query: str,
    max_papers: int = 5,
) -> AsyncGenerator[dict[str, Any], None]:
    """执行完整的研究流程，逐步 yield 状态更新（供 FastAPI SSE 流式展示）。"""
    state: ResearchState = {
        "query": query,
        "max_papers": max_papers,
        "sub_tasks": [],
        "plan_summary": "",
        "search_results": [],
        "selected_papers": [],
        "parsed_papers": {},
        "pdf_available": {},
        "comparison_report": "",
        "final_report": "",
        "execution_log": [],
        "errors": [],
        "current_step": "初始化...",
    }

    yield _snapshot(state)
    await asyncio.sleep(0)

    # ── Step 1: Planner ──
    state = await asyncio.to_thread(plan_tasks, state)
    yield _snapshot(state)
    await asyncio.sleep(0)

    if state["errors"]:
        state["final_report"] = _error_report(state)
        yield _snapshot(state)
        return

    # ── Step 2-4: 按 DAG 顺序执行子任务 ──
    tasks = state["sub_tasks"]
    completed: set[str] = set()

    while len(completed) < len(tasks):
        made_progress = False
        for task in tasks:
            tid = task["id"]
            if tid in completed:
                continue
            if not set(task.get("depends_on", []) or []).issubset(completed):
                continue

            task["status"] = "running"
            state["current_step"] = f"执行中: {task['description'][:60]}..."
            yield _snapshot(state)
            await asyncio.sleep(0)

            task_type = task["type"]
            if task_type == "report":
                task["status"] = "done"
                completed.add(tid)
                continue

            worker_func = WORKER_MAP.get(task_type)
            if worker_func:
                state = await asyncio.to_thread(worker_func, state, task)
            else:
                state["execution_log"].append(f"[Executor] 未知任务类型: {task_type}")

            task["status"] = "done"
            completed.add(tid)
            made_progress = True

        if not made_progress:
            state["errors"].append("任务执行陷入死锁或存在无法满足的依赖")
            break

        yield _snapshot(state)
        await asyncio.sleep(0)

    # ── Step 5: 生成最终报告 ──
    state["current_step"] = "生成最终报告..."
    state["execution_log"].append("[Reporter] 正在汇总所有信息，生成最终报告...")
    yield _snapshot(state)
    await asyncio.sleep(0)

    try:
        state["final_report"] = await asyncio.to_thread(_generate_final_report, state)
        state["execution_log"].append("[Reporter] 最终报告生成完毕")
    except Exception as e:
        state["errors"].append(f"报告生成失败: {e}")
        state["final_report"] = _error_report(state)

    state["current_step"] = "完成"
    yield _snapshot(state)


def _generate_final_report(state: ResearchState) -> str:
    """调用 LLM 生成最终报告"""
    paper_summaries = []
    for pubmed_id, data in state.get("parsed_papers", {}).items():
        s = data.get("structured", {})
        paper_summaries.append(
            f"### [{pubmed_id}] {s.get('title', 'N/A')}\n"
            f"- 作者: {s.get('authors', 'N/A')}\n"
            f"- 期刊: {s.get('journal', 'N/A')} ({s.get('year', 'N/A')})\n"
            f"- DOI: {s.get('doi', 'N/A')}\n"
            f"- 靶点: {s.get('target', 'N/A')}\n"
            f"- 方法: {s.get('method', 'N/A')}\n"
            f"- 关键发现: {s.get('key_findings', 'N/A')}\n"
            f"- 结论: {s.get('conclusion', 'N/A')}\n"
        )

    prompt = (
        f"## 用户研究意图\n{state['query']}\n\n"
        f"## 检索到 {len(paper_summaries)} 篇文献的结构化信息\n\n"
        + "\n".join(paper_summaries)
        + f"\n\n## 对比分析结果\n{state.get('comparison_report', '无')}"
        + f"\n\n请生成最终文献概览报告。"
    )

    report = llm.chat(
        user_prompt=prompt,
        system_prompt=REPORT_SYSTEM_PROMPT,
        temperature=0.3,
    )

    report += (
        f"\n\n---\n"
        f"*报告由 Bioinformatics Agent 自动生成 | "
        f"检索文献数: {len(state.get('search_results', []))} | "
        f"筛选文献数: {len(paper_summaries)}*\n"
    )
    return report


def _error_report(state: ResearchState) -> str:
    return (
        f"# 报告生成失败\n\n"
        f"执行过程中遇到以下错误：\n\n"
        + "\n".join(f"- {e}" for e in state["errors"])
        + f"\n\n## 已完成步骤\n\n"
        + "\n".join(f"- {log}" for log in state["execution_log"])
    )


def _snapshot(state: ResearchState) -> dict[str, Any]:
    """返回状态的快照 dict，包含前端所需的所有字段"""

    # 序列化 sub_tasks（确保 TypedDict → plain dict）
    safe_tasks = []
    for t in state.get("sub_tasks", []):
        safe_tasks.append({
            "id": t.get("id", ""),
            "type": t.get("type", "search"),
            "description": t.get("description", ""),
            "depends_on": list(t.get("depends_on", [])),
            "status": t.get("status", "pending"),
        })

    # 构建论文详情列表（供前端 DetailPanel 使用）
    papers = _build_papers_list(state)

    return {
        "current_step": state.get("current_step", ""),
        "plan_summary": state.get("plan_summary", ""),
        "sub_tasks": safe_tasks,
        "execution_log": list(state.get("execution_log", [])),
        "search_results_count": len(state.get("search_results", [])),
        "selected_papers_count": len(state.get("selected_papers", [])),
        "parsed_papers_count": len(state.get("parsed_papers", {})),
        "comparison_report": state.get("comparison_report", ""),
        "final_report": state.get("final_report", ""),
        "errors": state.get("errors", []),
        "papers": papers,
    }


def _build_papers_list(state: ResearchState) -> list[dict[str, Any]]:
    """从解析结果中提取论文详情列表"""
    papers: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    # 已解析的论文（含结构化数据）
    for pubmed_id, data in state.get("parsed_papers", {}).items():
        paper_info = data.get("paper_info", {})
        structured = data.get("structured", {})
        papers.append({
            "pubmed_id": pubmed_id,
            "title": structured.get("title", paper_info.get("title", "")),
            "abstract": paper_info.get("abstract", ""),
            "authors": _as_list(structured.get("authors", "").split(", ")) or _as_list(paper_info.get("authors", [])),
            "journal": structured.get("journal", paper_info.get("journal", "")),
            "publication_date": str(structured.get("year", paper_info.get("publication_date", ""))),
            "doi": structured.get("doi", paper_info.get("doi", "")),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
            "objective": structured.get("objective", ""),
            "method": structured.get("method", ""),
            "target": structured.get("target", ""),
            "key_findings": structured.get("key_findings", ""),
            "conclusion": structured.get("conclusion", ""),
        })
        seen_ids.add(pubmed_id)

    # 未解析的论文（只有标题摘要）
    for paper in state.get("selected_papers", []):
        pid = paper.get("pubmed_id", "")
        if pid and pid not in seen_ids:
            papers.append({
                "pubmed_id": pid,
                "title": paper.get("title", ""),
                "abstract": paper.get("abstract", ""),
                "authors": _as_list(paper.get("authors", [])),
                "journal": paper.get("journal", ""),
                "publication_date": paper.get("publication_date", ""),
                "doi": paper.get("doi", ""),
                "url": paper.get("url", f"https://pubmed.ncbi.nlm.nih.gov/{pid}/"),
                "objective": "",
                "method": "",
                "target": "",
                "key_findings": "",
                "conclusion": "",
            })
            seen_ids.add(pid)

    return papers


def _as_list(val: Any) -> list[str]:
    """将值安全转为字符串列表"""
    if isinstance(val, list):
        return [str(v) for v in val if v]
    if isinstance(val, str) and val.strip():
        return [val.strip()]
    return []
