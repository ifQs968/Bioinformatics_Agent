"""
DeepSeek API 统一调用封装 — 兼容 OpenAI SDK 格式。
"""
import json
from typing import Any, Iterator
from openai import OpenAI

from backend.config import config
from dotenv import load_dotenv
load_dotenv()  # 自动读取 .env 文件中的密钥

class LLMClient:
    """LLM 调用客户端，封装 DeepSeek Chat API"""

    def __init__(self):
        self._client = OpenAI(
            api_key=config.DEEPSEEK_API_KEY,
            base_url=config.DEEPSEEK_BASE_URL,
        )
        self._model = config.DEEPSEEK_MODEL

    def chat(
        self,
        user_prompt: str,
        system_prompt: str = "你是一个专业的生物医学研究助手。",
        temperature: float = 0.3,
        response_format: str | None = None,
    ) -> str:
        """发送同步对话请求，返回完整回复文本。

        Args:
            user_prompt: 用户消息
            system_prompt: 系统提示词
            temperature: 控制随机性 (0-2)，生物医学任务建议偏低
            response_format: 设为 "json_object" 可让模型返回 JSON

        Returns:
            模型回复的完整文本
        """
        kwargs: dict[str, Any] = {
            "model": self._model,
            "temperature": temperature,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
        }
        if response_format == "json_object":
            kwargs["response_format"] = {"type": "json_object"}

        response = self._client.chat.completions.create(**kwargs)
        return response.choices[0].message.content or ""

    def chat_json(
        self,
        user_prompt: str,
        system_prompt: str = "你是一个专业的生物医学研究助手。请始终以 JSON 格式返回。",
        temperature: float = 0.1,
    ) -> dict[str, Any]:
        """发送请求并解析 JSON 返回。

        Returns:
            解析后的 dict，解析失败返回 {"raw": raw_text}
        """
        raw = self.chat(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            response_format="json_object",
        )
        try:
            return json.loads(raw)
        except json.JSONDecodeError:
            return {"raw": raw}

    def stream_chat(
        self,
        user_prompt: str,
        system_prompt: str = "你是一个专业的生物医学研究助手。",
        temperature: float = 0.3,
    ) -> Iterator[str]:
        """流式对话，逐步 yield 文本块。"""
        response = self._client.chat.completions.create(
            model=self._model,
            temperature=temperature,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            stream=True,
        )
        for chunk in response:
            delta = chunk.choices[0].delta
            if delta.content:
                yield delta.content


# 全局单例
llm = LLMClient()
