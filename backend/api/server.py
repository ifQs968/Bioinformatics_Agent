"""
FastAPI 服务 — Bioinformatics Agent REST API + SSE 流式端点。
"""
import json
import asyncio
from typing import AsyncGenerator

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, JSONResponse
from pydantic import BaseModel, Field

from backend.config import config
from backend.agent.executor import execute_research


app = FastAPI(
    title="Bioinformatics Agent API",
    description="AI 驱动的生物医学文献智能分析系统",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


class ResearchRequest(BaseModel):
    query: str = Field(..., description="研究问题", min_length=5)
    max_papers: int = Field(default=5, ge=2, le=20, description="最大文献数")


@app.get("/api/health")
async def health():
    return {"status": "ok", "service": "Bioinformatics Agent"}


@app.post("/api/research")
async def research(request: ResearchRequest):
    """SSE 流式端点：接收研究问题，逐步返回执行状态"""

    async def event_stream() -> AsyncGenerator[str, None]:
        try:
            async for snapshot in execute_research(
                query=request.query,
                max_papers=request.max_papers,
            ):
                data = json.dumps(snapshot, ensure_ascii=False)
                yield f"data: {data}\n\n"
                await asyncio.sleep(0)  # 让出控制权

            # 发送结束信号
            yield "data: [DONE]\n\n"

        except Exception as e:
            import traceback
            error_snapshot = {
                "current_step": "执行出错",
                "plan_summary": "",
                "sub_tasks": [],
                "execution_log": [f"系统错误: {str(e)}"],
                "search_results_count": 0,
                "selected_papers_count": 0,
                "parsed_papers_count": 0,
                "comparison_report": "",
                "final_report": "",
                "errors": [f"{type(e).__name__}: {str(e)}"],
                "papers": [],
            }
            error_data = json.dumps(error_snapshot, ensure_ascii=False)
            yield f"data: {error_data}\n\n"
            yield "data: [DONE]\n\n"

    return StreamingResponse(
        event_stream(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",
        },
    )


@app.post("/api/research/simple")
async def research_simple(request: ResearchRequest):
    """非流式端点：返回完整结果（用于测试 / 无需流式的场景）"""
    final_snapshot = None
    async for snapshot in execute_research(
        query=request.query,
        max_papers=request.max_papers,
    ):
        final_snapshot = snapshot

    if final_snapshot is None:
        return JSONResponse({"error": "执行失败"}, status_code=500)

    return JSONResponse(final_snapshot)
