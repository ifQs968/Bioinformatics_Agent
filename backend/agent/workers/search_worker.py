"""
Search Worker — 调用 PubMed 检索文献，并由 LLM 筛选排序。
"""
from backend.tools.pubmed_search import pubmed
from backend.tools.llm_client import llm
from backend.agent.state import ResearchState


QUERY_BUILD_PROMPT = """你是一个 PubMed 检索专家。请将以下生物医学研究任务转换为 PubMed 检索式。

任务描述：
{description}

用户原始研究意图：
{query}

请返回一个 JSON：
{{
  "pubmed_query": "正式的 PubMed 检索式（英文关键词 + PubMed 语法）",
  "keywords": "提取的核心关键词（逗号分隔）"
}}

规则：
1. 检索式必须使用英文，只包含 PubMed 支持的语法：MeSH 词、布尔运算符 (AND/OR/NOT)、字段限定符 ([Title/Abstract], [MeSH Terms], [All Fields])
2. 不要包含中文或自然语言描述
3. 优先使用 MeSH 词和精准的字段限定
4. 例子：输入 "CRISPR癌症治疗" → 输出 "CRISPR-Cas9[MeSH Terms] AND neoplasms[MeSH Terms] AND therapy[Title/Abstract]"
"""

SEARCH_FILTER_PROMPT = """你是一个生物医学文献筛选专家。根据用户的研究意图，从检索结果中筛选最相关的文献。

用户意图：{query}

检索结果：
{results_text}

请选出最相关的 {max_papers} 篇文献，按相关性从高到低排序。返回 JSON：
{{
  "selected_ids": ["pubmed_id_1", "pubmed_id_2", ...],
  "reason": "简短的筛选理由"
}}

筛选标准：
1. 优先选择与研究意图直接相关的文献
2. 优先选择近3年发表的文献
3. 优先选择有摘要的文献
4. 避免选择明显不相关的文献
"""


def search_papers(state: ResearchState, task: dict) -> ResearchState:
    """执行检索任务"""
    description = task.get("description", state["query"])
    user_query = state.get("query", "")
    max_results = state.get("max_papers", 10) * 3  # 多检索一些

    state["execution_log"].append(f"[Search Worker] 开始检索: {description}")
    state["current_step"] = f"构建 PubMed 查询式..."

    # ── Step 0: LLM 翻译中文描述 → PubMed 检索式 ──
    try:
        query_result = llm.chat_json(
            user_prompt=QUERY_BUILD_PROMPT.format(
                description=description,
                query=user_query,
            ),
            system_prompt="请以 JSON 格式返回 PubMed 检索式。",
            temperature=0.1,
        )
        pubmed_query = query_result.get("pubmed_query", "")
        keywords = query_result.get("keywords", "")
    except Exception as e:
        # Fallback: 用用户原始查询（去除中文）
        pubmed_query = _fallback_query(user_query, description)
        keywords = pubmed_query
        state["execution_log"].append(f"[Search Worker] LLM 查询构建失败，使用 fallback: {pubmed_query}")

    if not pubmed_query or pubmed_query.strip() == "":
        pubmed_query = _fallback_query(user_query, description)

    state["execution_log"].append(f"[Search Worker] PubMed 检索式: {pubmed_query}")
    state["current_step"] = f"检索中: {pubmed_query[:60]}..."

    # ── Step 1: PubMed 检索 ──
    try:
        articles = pubmed.search(pubmed_query, max_results=max_results)
    except Exception as e:
        state["errors"].append(f"PubMed 检索失败: {e}")
        state["execution_log"].append(f"[Search Worker] 检索失败: {e}")
        state["search_results"] = []
        return state

    state["search_results"] = articles
    state["execution_log"].append(f"[Search Worker] 检索到 {len(articles)} 篇文献")

    if not articles:
        # 尝试用更宽泛的关键词重试
        fallback = _build_fallback_query(keywords, user_query)
        if fallback and fallback != pubmed_query:
            state["execution_log"].append(f"[Search Worker] 第一次无结果，用宽泛查询重试: {fallback}")
            try:
                articles = pubmed.search(fallback, max_results=max_results)
                state["search_results"] = articles
                state["execution_log"].append(f"[Search Worker] 重试检索到 {len(articles)} 篇文献")
            except Exception as e:
                state["errors"].append(f"PubMed 重试也失败: {e}")

    if not articles:
        state["execution_log"].append("[Search Worker] 无检索结果，跳过后续步骤")
        state["selected_papers"] = []
        return state

    # ── Step 2: LLM 筛选排序 ──
    results_text = "\n\n".join(
        f"[{a['pubmed_id']}] {a['title']}\n{a['abstract'][:300]}..."
        for a in articles
    )

    try:
        filter_result = llm.chat_json(
            user_prompt=SEARCH_FILTER_PROMPT.format(
                query=user_query,
                results_text=results_text,
                max_papers=state.get("max_papers", 5),
            ),
            system_prompt="请以 JSON 格式返回筛选结果。",
            temperature=0.1,
        )
    except Exception as e:
        state["errors"].append(f"LLM 筛选失败: {e}")
        max_n = state.get("max_papers", 5)
        state["selected_papers"] = articles[:max_n]
        state["execution_log"].append(f"[Search Worker] LLM 筛选失败，降级取前 {max_n} 篇")
        return state

    selected_ids = filter_result.get("selected_ids", [])
    article_map = {a["pubmed_id"]: a for a in articles}

    selected = []
    for pid in selected_ids:
        if pid in article_map:
            selected.append(article_map[pid])

    state["selected_papers"] = selected
    state["execution_log"].append(
        f"[Search Worker] 筛选完成: {len(selected)} 篇相关文献\n"
        + "\n".join(f"  - [{p.get('pubmed_id', '?')}] {p.get('title', '')[:80]}" for p in selected)
    )
    return state


def _fallback_query(user_query: str, description: str) -> str:
    """当 LLM 不可用时，从用户输入中提取英文关键词作为查询"""
    import re
    # 提取英文单词和数字
    combined = f"{user_query} {description}"
    # 提取英文词组（连续的字母数字组合）
    english_terms = re.findall(r'[A-Za-z0-9\-+]+', combined)
    # 过滤掉太短的词
    meaningful = [t for t in english_terms if len(t) > 2]
    if meaningful:
        return " AND ".join(meaningful[:5])
    # 最后的 fallback
    return user_query.strip().replace(" ", " AND ")


def _build_fallback_query(keywords: str, user_query: str) -> str:
    """构建宽泛查询用于重试"""
    import re
    if keywords:
        terms = [t.strip() for t in keywords.split(",") if t.strip() and len(t.strip()) > 2]
        if terms:
            return " OR ".join(terms[:4])
    # 提取英文关键词
    english = re.findall(r'[A-Za-z0-9\-+]{3,}', user_query)
    if english:
        return " OR ".join(english[:4])
    return ""
