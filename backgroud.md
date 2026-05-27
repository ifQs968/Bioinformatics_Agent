# 背景

我们现在想做一个agent。呈现的方式是网页端。

学术与科研赋能方向，希望能够针对生物医学领域文献全文阅读成本高、关键信息（如图表数据、实验结论）难定位、跨文献对比效率低等困境开发一个AI Agent，能够根据用户的研究意图主动规划任务路径，并结合调用多个生物医学文献专业工具，最终生成结构清晰、来源可溯、图文对照的文献概括报告。

# 值得参考的类似工具

Consensus (AI Academic Search)

Elicit (The AI Research Assistant)

SciSpace (formerly Typeset.io)

# 开源Agent框架与论文参考

LangGraph/AutoGen/CrewAI：目前实现“主动规划任务路径”最常用的多Agent异步协作框架。

Bio-Agents / MedAgents (学术论文)：近年来顶级 AI 会议上关于生物医学 Agent 的研究。它们的核心思路是“让不同的 Agent 扮演不同的专家”（例如：一个扮演生物信息学专家，一个扮演临床医学专家，一个扮演审稿人），通过多轮辩论（Debate）或协作来得出更准确的结论。

# Agent架构建议

[ 用户前端 (Web UI) ] 交互层：输入意图，展示动态规划路径、图文报告
        │
[ 规划与路由层 (Planner/Router Agent) ] 核心大脑：拆解任务，生成 DAG 图
        │
[ 执行层 (Specialized Workers) ] 专家 Agent 团队 (文献解析、工具调用、对比分析)
        │
[ 工具与数据层 (Tools & APIs) ] 外部基础设施 (PubMed API, OCR, PDF Parser, 向量库)

第一层：规划与路由层 (Planner Agent)
功能：不要让用户一上来就直接得到结果，因为生物医学任务太复杂。用户输入意图后（例如：“对比近三年针对某靶点的 RNA 疗法临床二期数据”），Planner 负责将这个大任务拆解为 DAG（有向无环图） 任务流。

建议：在网页端动态可视化这个规划路径（类似 Langflow 或 AutoGen Studio 的节点执行过程）。让科研人员看到 Agent 正在“搜索 PubMed -> 提取 PDF 图表 -> 调用结构预测 -> 比对数据”，这种“确定感”和“白盒化”能极大增加科研人员对 AI 的信任度。

🧪 第二层：执行层 (专职专家子 Agent)
不要用一个大模型做所有事，建议解耦为以下几个特化 Agent：

PDF/图表解析 Agent (Parser Agent)：专门负责处理复杂的多栏生物医学 PDF，识别其中的 Table、Image 及其 Caption。

工具调用 Agent (Tool Agent)：专门负责把自然语言转化为结构化的 API 请求（如将“查找这个蛋白质序列”转化为 BLAST 或 UniProt API 的参数）。

批判与比对 Agent (Critic Agent)：负责交叉比对不同文献的实验条件（如细胞系、小鼠周龄、给药剂量），找出矛盾点或共性。

🧰 第三层：工具与数据层 (Tools)
这是你们区别于通用文献 Agent 的核心护城河。你们需要集成的工具应包括：

标准文献检索：PubMed API, Europe PMC API。

高级 PDF 解析：Marker 或 MinerU（开源的高清 PDF 转 Markdown 工具，对公式和图表提取极好），以及 Nougat（Meta 出的专门针对学术论文的 Transformer 了解析工具）。

专业生物医药工具：RDKit（如果是小分子）、Biopython（序列处理）、甚至接入一些结构预测的中间结果看板。

# 可能的硬骨头

1. 图文对照与“来源可溯”（Provenance）
痛点：大模型生成的报告经常幻觉，或者用户不知道某句话对应 PDF 的哪一页、哪张图。

建议：

在解析 PDF 时，必须保留每个段落、图表的 Bounding Box（坐标位置）和页码。

在前端呈现报告时，采用双栏/悬浮窗设计。点击报告中的某个结论或图表引用标签（如 [Figure 1, Ref 2]），右侧页面自动滚动到原文献 PDF 的对应高亮区域。

基于 Markdown 语法扩展，将图表以 ![fig_1](oss_path) 的形式在报告中就地渲染，实现真正的图文并茂。

2. 跨文献对比的“长文本与结构化”矛盾
痛点：多篇文献动辄十几万字，直接塞给大模型（如 Claude 3.5 或 GPT-4o）虽然装得下，但很容易漏掉细节（Needle in a Haystack 效应），且对比流于表面。

建议：采用“先结构化，后对比”的策略。

Step 1：让 Agent 对每篇选定的文献执行一个固定的“Schema 提取任务”（如提取：Method, Biomarker, Target, Result Value）。

Step 2：将提取出的结构化 JSON/表格存入临时数据库。

Step 3：让对比 Agent 基于这个结构化的表格去撰写对比报告，而不是直接去读几十篇原始 PDF。

3. 用户意图的“主动引导”
痛点：很多时候研究生或科研人员自己的 Prompt 也很模糊（例如：“帮我看看关于这个靶点的最新进展”）。

建议：前端加入交互式澄清（Human-in-the-loop）。当 Planner Agent 拆解任务后，如果在某个分支发现文献量过大或方向不明确，可以弹出微型表单：“为你找到了 50 篇相关文献，请问你更倾向于：A. 临床试验数据 B. 分子机制机理 C. 药物合成工艺？”，用户点选后再继续执行，避免 Agent 跑偏浪费 Token。

这是一个紧密结合了前沿 AI 技术（Agentic Workflow）与垂直领域（Bio-Med）的极佳课题。如果你们准备开始动手，第一步可以先用 LangGraph 搭建一个能稳定调用 PubMed 检索并用 MinerU 解析单篇 PDF 图表的原型（MVP），验证这条通路后，再往多文献对比和主动规划去扩展。


