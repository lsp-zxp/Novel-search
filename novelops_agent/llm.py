from __future__ import annotations

import json
import os
from typing import TypeVar

from dotenv import load_dotenv
from pydantic import BaseModel

load_dotenv()

SchemaT = TypeVar("SchemaT", bound=BaseModel)


class BailianJsonClient:
    """Structured JSON client for Bailian OpenAI-compatible Chat Completions."""

    def __init__(
        self,
        *,
        model: str | None = None,
        api_key: str | None = None,
        base_url: str | None = None,
        timeout_seconds: float | None = None,
    ) -> None:
        from openai import AsyncOpenAI

        key = api_key or os.getenv("LLM_API_KEY") or os.getenv("DASHSCOPE_API_KEY")
        endpoint = base_url or os.getenv("LLM_BASE_URL") or os.getenv("DASHSCOPE_BASE_URL")
        if not key or not endpoint:
            raise RuntimeError("百炼LLM配置不完整。")
        self.model = model or os.getenv("LLM_MODEL", "deepseek-v4-pro")
        self._client = AsyncOpenAI(
            api_key=key,
            base_url=endpoint,
            timeout=timeout_seconds or float(os.getenv("LLM_TIMEOUT_SECONDS", "60")),
            max_retries=1,
        )

    async def parse(
        self,
        schema: type[SchemaT],
        *,
        system: str,
        user: str,
    ) -> SchemaT:
        schema_json = json.dumps(schema.model_json_schema(), ensure_ascii=False)
        completion = await self._client.chat.completions.create(
            model=self.model,
            messages=[
                {
                    "role": "system",
                    "content": (
                        f"{system}\n必须只返回符合以下JSON Schema的JSON对象，不输出Markdown："
                        f"{schema_json}"
                    ),
                },
                {"role": "user", "content": user},
            ],
            response_format={"type": "json_object"},
            extra_body={"enable_thinking": False},
        )
        content = completion.choices[0].message.content or ""
        try:
            return schema.model_validate_json(content)
        except Exception as exc:
            raise RuntimeError(f"{self.model}返回的JSON不符合{schema.__name__}：{exc}") from exc
