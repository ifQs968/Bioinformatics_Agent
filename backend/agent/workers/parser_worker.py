"""
Parser Worker — 解析文献（全文 PDF 或摘要）并提取结构化数据。
"""
from backend.tools.llm_client import llm
from backend.tools.pdf_parser import pdf_parser, ParseResult
from backend.schemas.literature import LiteratureSchema
from backend.agent.state import ResearchState


PARSE_SYSTEM_PROMPT = """你是一个生物医学文献信息提取专家。请从以下文献内容中提取关键信息。

请提取以下字段并以 JSON 格式返回：
{
  "objective": "研究目标（1-2句话）",
  "method": "使用的实验方法、技术手段",
  "target": "研究的靶点、基因、蛋白质或疾病",
  "biomarker": "涉及的生物标志物（如无可留空）",
  "sample_size": "样本量（如无可留空）",
  "model_system": "模型系统，如细胞系、动物模型等",
  "key_findings": "核心发现（2-3句话）",
  "result_value": "关键数值结果，如p值、效应量等",
  "conclusion": "结论（1-2句话）",
  "figures_summary": "图表内容概述（如无图表可留空）",
  "limitations": "研究局限性（如未提及可留空）"
}

只提取文献中明确提到的内容，不要编造。如果某字段信息不明，填入空字符串。
"""


def parse_papers(state: ResearchState, task: dict) -> ResearchState:
    """解析选中的文献"""
    papers = state.get("selected_papers", [])
    if not papers:
        state["execution_log"].append("[Parser Worker] 没有需要解析的文献")
        return state

    state["current_step"] = f"解析中: 共 {len(papers)} 篇文献..."
    parsed = state.get("parsed_papers", {})

    for i, paper in enumerate(papers):
        pubmed_id = paper.get("pubmed_id", f"unknown_{i}")
        title = paper.get("title", "N/A")

        state["execution_log"].append(
            f"[Parser Worker] ({i+1}/{len(papers)}) 解析: {title[:80]}"
        )
        state["current_step"] = f"解析文献 {i+1}/{len(papers)}: {title[:50]}..."

        # 检查是否有 PDF 全文
        pdf_path = state.get("pdf_available", {}).get(pubmed_id, "")

        content_text = ""
        figures_data = []

        if pdf_path:
            # 有 PDF → 使用 PDF 解析器
            try:
                parse_result: ParseResult = pdf_parser.parse(pdf_path, prefer_mineru=True)
                content_text = parse_result.full_text[:8000]  # 限制长度
                state["execution_log"].append(
                    f"  PDF 已解析: {parse_result.page_count} 页, "
                    f"{len(parse_result.figures)} 张图表"
                )
            except Exception as e:
                state["execution_log"].append(f"  PDF 解析失败，回退到摘要: {e}")

        # 无 PDF 或 PDF 解析失败 → 用摘要
        if not content_text:
            content_text = f"标题: {title}\n摘要: {paper.get('abstract', '无摘要')}"
            state["execution_log"].append(f"  使用摘要进行信息提取")

        # LLM 提取结构化信息
        try:
            extracted = llm.chat_json(
                user_prompt=f"文献内容：\n{content_text[:6000]}",
                system_prompt=PARSE_SYSTEM_PROMPT,
                temperature=0.1,
            )
        except Exception as e:
            state["errors"].append(f"文献 {pubmed_id} 解析失败: {e}")
            extracted = {}

        schema = LiteratureSchema(
            pubmed_id=pubmed_id,
            title=title,
            authors=", ".join(paper.get("authors", [])[:5]),
            year=int(paper.get("publication_date", "0")[:4]) if paper.get("publication_date") else 0,
            journal=paper.get("journal", ""),
            doi=paper.get("doi", ""),
            objective=extracted.get("objective", ""),
            method=extracted.get("method", ""),
            target=extracted.get("target", ""),
            biomarker=extracted.get("biomarker", ""),
            sample_size=extracted.get("sample_size", ""),
            model_system=extracted.get("model_system", ""),
            key_findings=extracted.get("key_findings", ""),
            result_value=extracted.get("result_value", ""),
            conclusion=extracted.get("conclusion", ""),
            figures_summary=extracted.get("figures_summary", ""),
            limitations=extracted.get("limitations", ""),
        )

        parsed[pubmed_id] = {
            "structured": schema.to_dict(),
            "paper_info": paper,
            "figures": figures_data,
        }

    state["parsed_papers"] = parsed
    state["execution_log"].append(
        f"[Parser Worker] 完成。共解析 {len(parsed)} 篇文献"
    )
    return state
