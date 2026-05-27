"""
文献提取 Schema 定义 — 用于 PDF 解析后的结构化抽取。
"""
from dataclasses import dataclass, field, asdict


@dataclass
class LiteratureSchema:
    """单篇文献的结构化提取模板

    对应 backgroud.md 中的 Schema 提取策略：
    Method / Biomarker / Target / Result Value
    """
    # 基础信息
    pubmed_id: str = ""
    title: str = ""
    authors: str = ""
    year: int = 0
    journal: str = ""
    doi: str = ""

    # 研究信息
    objective: str = ""            # 研究目标
    method: str = ""               # 实验方法/方案
    target: str = ""               # 靶点 / 研究对象
    biomarker: str = ""            # 生物标志物
    sample_size: str = ""          # 样本量
    model_system: str = ""         # 模型系统 (细胞系、动物模型等)

    # 结果
    key_findings: str = ""         # 核心发现
    result_value: str = ""         # 关键数据值 (p-value, effect size 等)
    conclusion: str = ""           # 结论

    # 图表
    figures_summary: str = ""      # 图表摘要

    # 限制
    limitations: str = ""          # 研究局限性

    def to_dict(self) -> dict:
        return asdict(self)

    def to_markdown_row(self) -> str:
        """转为 Markdown 表格的一行"""
        return (
            f"| {self.pubmed_id} | {self.title[:40]}... | {self.target} | "
            f"{self.method[:30]}... | {self.key_findings[:50]}... |"
        )


# 对比报告的表格表头
COMPARISON_TABLE_HEADER = (
    "| PubMed ID | Title | Target | Method | Key Findings |\n"
    "|-----------|-------|--------|--------|-------------|"
)


@dataclass
class ComparisonResult:
    """多文献对比分析结果"""
    papers: list[LiteratureSchema] = field(default_factory=list)
    common_points: list[str] = field(default_factory=list)      # 共同发现
    contradictions: list[str] = field(default_factory=list)     # 矛盾点
    research_gaps: list[str] = field(default_factory=list)      # 研究空白
    summary: str = ""                                           # 总结

    def to_markdown(self) -> str:
        """生成对比报告 Markdown"""
        lines = [
            "# 跨文献对比分析报告\n",
            "## 对比文献列表\n",
            COMPARISON_TABLE_HEADER,
        ]
        for paper in self.papers:
            lines.append(paper.to_markdown_row())
        lines.append("")

        if self.common_points:
            lines.append("## 共同发现\n")
            for pt in self.common_points:
                lines.append(f"- {pt}")
            lines.append("")

        if self.contradictions:
            lines.append("## 矛盾与差异\n")
            for pt in self.contradictions:
                lines.append(f"- {pt}")
            lines.append("")

        if self.research_gaps:
            lines.append("## 研究空白\n")
            for pt in self.research_gaps:
                lines.append(f"- {pt}")
            lines.append("")

        if self.summary:
            lines.append(f"## 总结\n\n{self.summary}\n")

        return "\n".join(lines)
