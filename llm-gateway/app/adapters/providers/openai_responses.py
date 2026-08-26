"""OpenAI Responses API 适配器

适用模型: deepseek-v4-pro
协议端点: POST /v1/responses

请求体差异（与 Anthropic 对比）：
- 用户输入: "input" 字段（字符串或数组），而非 "messages"
- 系统提示词: "instructions" 字段，而非顶层 "system" 字段
- 流式事件: response.output_text.delta
"""

import json
import logging
from collections.abc import AsyncGenerator

from app.adapters.base import BaseAdapter
from app.adapters.protocol import UnifiedRequest, UnifiedResponse
from app.core.constants import StreamEventType
from app.core.exceptions import ProviderException, ModelTimeoutException
from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage
from app.schemas.response.stream import StreamChunk
from app.utils.clock import Clock

logger = logging.getLogger(__name__)


class OpenAIResponsesAdapter(BaseAdapter):
    """OpenAI Responses API 适配器"""

    # ── 请求构建 ──

    def build_request_payload(self, request: UnifiedRequest) -> dict:
        """构建 OpenAI Responses API 请求体

        格式转换:
        UnifiedRequest → OpenAI Responses API 格式
        """
        # 提取用户消息（最后一条 user 消息作为 input）
        user_messages = [
            m.content
            for m in request.messages
            if m.role == "user"
        ]
        # 历史消息（不含最后一条 user 消息）
        previous_messages = [
            {"role": m.role.value, "content": m.content}
            for m in request.messages
            if m.role != "user"
            or m.content != (user_messages[-1] if user_messages else "")
        ]

        payload: dict = {
            "model": request.model,
            "input": user_messages[-1] if user_messages else "",
            "stream": request.stream,
        }

        # 系统提示词 → instructions
        if request.system_prompt:
            payload["instructions"] = request.system_prompt

        # 历史消息通过 previous_response_id 或直接拼接
        if previous_messages:
            # 将历史消息拼接到 input 中以保持上下文
            history_text = "\n".join(
                f"{m['role']}: {m['content']}" for m in previous_messages
            )
            if history_text:
                payload["input"] = (
                    f"[历史对话]\n{history_text}\n\n[当前问题]\n"
                    f"{payload['input']}"
                )

        # 模型参数
        if request.parameters:
            for key in ("temperature", "top_p", "max_output_tokens"):
                if key in request.parameters:
                    payload[key] = request.parameters[key]

        return payload

    # ── 用量提取 ──

    def extract_usage(self, raw_response: dict) -> Usage:
        """从 OpenAI Responses API 响应中提取 Token 用量

        OpenAI Responses API 用量字段:
        - usage.input_tokens
        - usage.output_tokens
        - usage.total_tokens
        """
        usage_data = raw_response.get("usage", {})
        return Usage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

    # ── 非流式调用 ──

    async def _do_call(
        self, request: UnifiedRequest, clock: Clock
    ) -> UnifiedResponse:
        """执行非流式 Responses API 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = False

        logger.info(
            "OpenAI Responses API 调用: model=%s, stream=False",
            request.model,
        )

        clock.start()
        try:
            response = await self.client.post("/v1/responses", json=payload)
        except Exception as e:
            raise ProviderException(f"请求失败: {e}") from e

        if response.status_code != 200:
            raise ProviderException(
                f"OpenAI Responses API 返回错误: status={response.status_code}, "
                f"body={response.text[:500]}"
            )

        data = response.json()
        clock.stop()

        # 提取输出文本
        output_text = ""
        for item in data.get("output", []):
            if item.get("type") == "message":
                for content_item in item.get("content", []):
                    if content_item.get("type") == "output_text":
                        output_text += content_item.get("text", "")

        usage = self.extract_usage(data)

        return UnifiedResponse(
            content=output_text,
            model=data.get("model", request.model),
            usage=usage,
            latency=LatencyInfo(ttft_ms=0.0, total_ms=clock.total_ms),
        )

    # ── 流式调用 ──

    async def _do_stream(
        self, request: UnifiedRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """执行流式 Responses API 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = True

        logger.info(
            "OpenAI Responses API 流式调用: model=%s",
            request.model,
        )

        clock = Clock()
        clock.start()

        try:
            async with self.client.stream(
                "POST", "/v1/responses", json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise ProviderException(
                        f"流式请求失败: status={response.status_code}, "
                        f"body={body[:500]}"
                    )

                buffer = ""
                async for line in response.aiter_lines():
                    if not line or not line.startswith("data: "):
                        continue
                    data_str = line[6:]  # 去掉 "data: " 前缀
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    event_type = event.get("type", "")

                    # 处理文本增量事件
                    if event_type == "response.output_text.delta":
                        text = event.get("delta", "")
                        if text:
                            clock.mark_first_token()
                            yield StreamChunk(
                                type=StreamEventType.TEXT_DELTA,
                                content=text,
                            )

                    # 处理响应完成事件
                    elif event_type in (
                        "response.completed",
                        "response.output_text.done",
                    ):
                        clock.stop()
                        usage = self.extract_usage(
                            event.get("response", {})
                        )
                        yield StreamChunk(
                            type=StreamEventType.TEXT_DONE,
                            usage=usage,
                            latency=LatencyInfo(
                                ttft_ms=clock.ttft_ms,
                                total_ms=clock.total_ms,
                            ),
                        )
                        return

        except Exception as e:
            raise ProviderException(f"流式请求异常: {e}") from e