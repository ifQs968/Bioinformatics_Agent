"""
LangGraph State 定义 — Agent 执行过程中的共享状态。
"""
from typing import Annotated, Any, TypedDict
from langgraph.graph.message import add_messages


class SubTask(TypedDict):
    """Planner 拆解出的单个子任务"""
    id: str                # 任务编号
    type: str              # "search" / "parse" / "compare" / "report"
    description: str       # 任务描述
    depends_on: list[str]  # 依赖的前置任务 ID
    status: str            # "pending" / "running" / "done" / "failed"


class ResearchState(TypedDict):
    """研究 Agent 的全局状态"""
    # 用户输入
    query: str                          # 用户原始研究意图
    max_papers: int                     # 最大检索文献数

    # Planner 输出
    sub_tasks: list[SubTask]            # 拆解后的任务 DAG
    plan_summary: str                   # 规划摘要（给用户看的）

    # 检索结果
    search_results: list[dict[str, Any]]  # PubMed 检索返回的文献列表
    selected_papers: list[dict[str, Any]] # 筛选后的文献

    # 解析结果
    parsed_papers: dict[str, dict[str, Any]]  # {pubmed_id: {parse_result, structured_data}}
    pdf_available: dict[str, str]             # {pubmed_id: pdf_path or ""}

    # 对比分析
    comparison_report: str              # 对比报告 Markdown

    # 最终输出
    final_report: str                   # 最终 Markdown 报告

    # 执行日志（白盒可视化）
    execution_log: Annotated[list[str], add_messages]  # 逐步追加日志

    # 错误信息
    errors: list[str]
    current_step: str                   # 当前执行步骤描述
