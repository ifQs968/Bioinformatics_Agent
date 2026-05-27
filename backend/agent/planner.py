"""
Planner Agent — 接收用户意图，拆解为结构化的子任务 DAG。
"""
import json

from backend.tools.llm_client import llm
from backend.agent.state import ResearchState, SubTask


PLANNER_SYSTEM_PROMPT = """你是一个生物医学文献研究规划专家。你的任务是将用户的研究意图拆解为具体的执行步骤。

## 可用的步骤类型 (type)
- "search": 在 PubMed 中检索相关文献
- "parse": 解析检索到文献的全文（或摘要），提取结构化信息
- "compare": 对比多篇文献的方法、结果和结论
- "report": 汇总所有信息，生成最终文献概览报告

## 输出格式
你必须返回一个 JSON，格式如下：
{
  "plan_summary": "用一句话概述你的执行计划",
  "sub_tasks": [
    {
      "id": "task_1",
      "type": "search",
      "description": "在PubMed中检索关于XXX的文献，限定近3年，临床试验",
      "depends_on": [],
      "status": "pending"
    },
    {
      "id": "task_2",
      "type": "parse",
      "description": "解析检索到的文献摘要，提取目标、方法、关键结果",
      "depends_on": ["task_1"],
      "status": "pending"
    },
    ...
  ]
}

## 规则
1. 每个 type 为 "search" 的任务，description 中必须包含具体的关键词和检索策略
2. 依赖关系形成合法的 DAG，不能有循环依赖
3. 通常流程为: search(1-2个) → parse → compare → report
4. 如果用户意图较宽泛，应该拆解为 2 个 search 子任务从不同角度检索
5. 任务总数控制在 4-7 个之间
"""


def plan_tasks(state: ResearchState) -> ResearchState:
    """Planner Agent 主函数：拆解用户意图 → 子任务列表"""
    query = state["query"]
    state["execution_log"].append("[Planner] 正在分析研究意图，拆解任务...")
    state["current_step"] = "Planner 规划中"

    prompt = f"用户研究意图：\n{query}\n\n请拆解为具体的执行子任务。"

    try:
        result = llm.chat_json(
            user_prompt=prompt,
            system_prompt=PLANNER_SYSTEM_PROMPT,
            temperature=0.1,
        )
    except Exception as e:
        state["errors"].append(f"Planner 调用失败: {e}")
        state["sub_tasks"] = _fallback_plan(query)
        state["plan_summary"] = "使用默认规划（LLM 调用失败）"
        state["execution_log"].append(f"[Planner] 失败，使用 fallback 计划: {e}")
        return state

    sub_tasks_raw = result.get("sub_tasks", [])
    plan_summary = result.get("plan_summary", "")

    state["sub_tasks"] = sub_tasks_raw
    state["plan_summary"] = plan_summary
    state["execution_log"].append(
        f"[Planner] 完成。共拆解 {len(sub_tasks_raw)} 个子任务：\n"
        + "\n".join(f"  - {t['id']}: {t['description']}" for t in sub_tasks_raw)
    )
    return state


def _fallback_plan(query: str) -> list[SubTask]:
    """LLM 不可用时的默认规划"""
    return [
        SubTask(id="task_1", type="search", description=f"检索 PubMed: {query}", depends_on=[], status="pending"),
        SubTask(id="task_2", type="parse", description="解析检索结果摘要", depends_on=["task_1"], status="pending"),
        SubTask(id="task_3", type="compare", description="对比分析文献", depends_on=["task_2"], status="pending"),
        SubTask(id="task_4", type="report", description="生成最终报告", depends_on=["task_3"], status="pending"),
    ]
