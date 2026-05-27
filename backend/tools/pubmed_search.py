"""
PubMed 文献检索封装 — 使用 pymed 库。
NCBI API Key 可选，不用也能检索（但频率受限制）。
"""
from typing import Any
from pymed import PubMed

from backend.config import config


class PubMedSearch:
    """PubMed 文献检索工具"""

    def __init__(self):
        kwargs: dict[str, str] = {"tool": "BioinformaticsAgent/1.0"}
        if config.PUBMED_EMAIL:
            kwargs["email"] = config.PUBMED_EMAIL
        if config.PUBMED_API_KEY:
            kwargs["api_key"] = config.PUBMED_API_KEY
        self._pubmed = PubMed(**kwargs)

    @staticmethod
    def _format_article(article: Any) -> dict[str, Any]:
        """将 pymed 的 Article 对象转为统一 dict 格式"""
        pubmed_id = (
            article.pubmed_id.split("\n")[0] if article.pubmed_id else "N/A"
        )
        return {
            "pubmed_id": pubmed_id,
            "title": article.title or "N/A",
            "abstract": article.abstract or "",
            "authors": [
                f"{a.get('lastname', '')} {a.get('firstname', '')}"
                for a in (article.authors or [])
                if a.get("lastname")
            ],
            "journal": article.journal or "",
            "doi": article.doi or "",
            "publication_date": str(article.publication_date or ""),
            "url": f"https://pubmed.ncbi.nlm.nih.gov/{pubmed_id}/",
        }

    def search(self, query: str, max_results: int = 10) -> list[dict[str, Any]]:
        """按关键词检索 PubMed 文献。

        Args:
            query: 检索关键词，支持 PubMed 高级语法
                  例如: "CRISPR therapy[Title/Abstract] AND 2024[dp]"
            max_results: 返回结果数上限

        Returns:
            文献信息列表，每条包含 pubmed_id, title, abstract, authors, doi 等
        """
        try:
            results = list(self._pubmed.query(query, max_results=max_results))
            articles = [self._format_article(a) for a in results]
            if not articles:
                # 诊断信息：看看是不是查询格式问题
                print(f"[PubMed] 查询返回 0 条结果。Query: {query[:200]}")
            return articles
        except Exception as e:
            raise RuntimeError(
                f"PubMed 检索失败: {e}\n"
                f"Query was: {query[:200]}"
            ) from e

    def get_detail(self, pubmed_id: str) -> dict[str, Any] | None:
        """根据 PubMed ID 获取单篇文献详情。

        Returns:
            文献信息 dict，未找到返回 None
        """
        try:
            results = self._pubmed.query(pubmed_id, max_results=1)
            article = next(results, None)
            if article is None:
                return None
            return self._format_article(article)
        except Exception as e:
            raise RuntimeError(f"PubMed 查询 {pubmed_id} 失败: {e}") from e


# 全局单例
pubmed = PubMedSearch()
