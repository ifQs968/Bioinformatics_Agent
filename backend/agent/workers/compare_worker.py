"""
Compare Worker — 跨文献对比分析，发现共性、矛盾点和研究空白。
"""
from backend.tools.llm_client import llm
from backend.agent.state import ResearchState


COMPARE_SYSTEM_PROMPT = """你是一个生物医学文献对比分析专家。你的任务是对比多篇文献，找出其中的共性、差异和研究空白。

请基于每篇文献的提取信息，生成对比分析报告。返回 JSON：
{
  "common_points": ["共性发现1", "共性发现2", ...],
  "contradictions": ["矛盾点1", "矛盾点2", ...],
  "research_gaps": ["研究空白1", "研究空白2", ...],
  "summary": "总体对比总结（2-3段）"
}

分析要点：
1. 共性：多篇文献都一致支持的结论、共同使用的方法
2. 矛盾：不同文献之间结果或结论不一致的地方
3. 空白：目前文献中尚未涉及或证据不足的方向
"""


def compare_papers(state: ResearchState, task: dict) -> ResearchState:
    """对比分析多篇文献的结构化数据"""
    parsed = state.get("parsed_papers", {})
    if len(parsed) < 2:
        state["execution_log"].append(
            "[Compare Worker] 文献数量不足2篇，跳过对比分析"
        )
        state["comparison_report"] = (
            "文献数量不足（少于2篇），无法进行有意义的跨文献对比分析。\n\n"
            "建议扩大检索范围或调整关键词。"
        )
        return state

    state["current_step"] = f"对比分析中: {len(parsed)} 篇文献..."
    state["execution_log"].append(
        f"[Compare Worker] 开始对比 {len(parsed)} 篇文献"
    )

    # 构建结构化数据摘要
    structured_summaries = []
    for pubmed_id, data in parsed.items():
        s = data.get("structured", {})
        summary_text = (
            f"文献 [{pubmed_id}]: {s.get('title', 'N/A')}\n"
            f"  目标: {s.get('objective', 'N/A')}\n"
            f"  方法: {s.get('method', 'N/A')}\n"
            f"  靶点: {s.get('target', 'N/A')}\n"
            f"  标志物: {s.get('biomarker', 'N/A')}\n"
            f"  样本量: {s.get('sample_size', 'N/A')}\n"
            f"  模型系统: {s.get('model_system', 'N/A')}\n"
            f"  关键发现: {s.get('key_findings', 'N/A')}\n"
            f"  数值结果: {s.get('result_value', 'N/A')}\n"
            f"  结论: {s.get('conclusion', 'N/A')}\n"
            f"  限制: {s.get('limitations', 'N/A')}"
        )
        structured_summaries.append(summary_text)

    prompt = (
        f"用户研究意图: {state['query']}\n\n"
        f"需要对比的 {len(parsed)} 篇文献：\n\n"
        + "\n\n---\n\n".join(structured_summaries)
    )

    try:
        result = llm.chat_json(
            user_prompt=prompt,
            system_prompt=COMPARE_SYSTEM_PROMPT,
            temperature=0.2,
        )
    except Exception as e:
        state["errors"].append(f"对比分析失败: {e}")
        state["comparison_report"] = f"对比分析过程出现错误: {e}"
        return state

    # 生成 Markdown 报告
    lines = ["# 跨文献对比分析\n"]

    common = result.get("common_points", [])
    if common:
        lines.append("## 共同发现\n")
        for pt in common:
            lines.append(f"- {pt}")
        lines.append("")

    contradictions = result.get("contradictions", [])
    if contradictions:
        lines.append("## 矛盾与差异\n")
        for pt in contradictions:
            lines.append(f"- {pt}")
        lines.append("")

    gaps = result.get("research_gaps", [])
    if gaps:
        lines.append("## 研究空白\n")
        for pt in gaps:
            lines.append(f"- {pt}")
        lines.append("")

    summary = result.get("summary", "")
    if summary:
        lines.append(f"## 总体评估\n\n{summary}\n")

    state["comparison_report"] = "\n".join(lines)
    state["execution_log"].append(
        f"[Compare Worker] 对比完成: "
        f"{len(common)} 条共性, {len(contradictions)} 条矛盾, {len(gaps)} 个空白"
    )
    return state
