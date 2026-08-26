"""Anthropic Messages API 适配器

适用模型: deepseek-v4-flash
协议端点: POST /v1/messages

请求体差异（与 OpenAI Responses 对比）：
- 用户输入: "messages" 字段（数组），而非 "input"
- 系统提示词: 顶层 "system" 字段，而非 "instructions"
- 流式事件: content_block_delta
"""

import json
import logging
from collections.abc import AsyncGenerator

from app.adapters.base import BaseAdapter
from app.adapters.protocol import UnifiedRequest, UnifiedResponse
from app.core.constants import StreamEventType
from app.core.exceptions import ProviderException
from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage
from app.schemas.response.stream import StreamChunk
from app.utils.clock import Clock

logger = logging.getLogger(__name__)


class AnthropicMessagesAdapter(BaseAdapter):
    """Anthropic Messages API 适配器"""

    # ── 请求构建 ──

    def build_request_payload(self, request: UnifiedRequest) -> dict:
        """构建 Anthropic Messages API 请求体

        格式转换:
        UnifiedRequest → Anthropic Messages API 格式
        """
        # 构建消息列表（排除 system 角色）
        messages = []
        for m in request.messages:
            if m.role == "system":
                continue  # system 消息单独处理
            messages.append({
                "role": m.role.value,
                "content": m.content,
            })

        payload: dict = {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
            "max_tokens": 4096,  # Anthropic 需要 max_tokens
        }

        # 系统提示词 → 顶层 system 字段
        if request.system_prompt:
            payload["system"] = request.system_prompt

        # 模型参数
        if request.parameters:
            for key in ("temperature", "top_p", "max_tokens"):
                if key in request.parameters:
                    payload[key] = request.parameters[key]

        return payload

    # ── 用量提取 ──

    def extract_usage(self, raw_response: dict) -> Usage:
        """从 Anthropic Messages API 响应中提取 Token 用量

        Anthropic 用量字段:
        - usage.input_tokens
        - usage.output_tokens
        """
        usage_data = raw_response.get("usage", {})
        return Usage(
            prompt_tokens=usage_data.get("input_tokens", 0),
            completion_tokens=usage_data.get("output_tokens", 0),
            total_tokens=(
                usage_data.get("input_tokens", 0)
                + usage_data.get("output_tokens", 0)
            ),
        )

    # ── 非流式调用 ──

    async def _do_call(
        self, request: UnifiedRequest, clock: Clock
    ) -> UnifiedResponse:
        """执行非流式 Messages API 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = False

        logger.info(
            "Anthropic Messages API 调用: model=%s, stream=False",
            request.model,
        )

        clock.start()
        try:
            response = await self.client.post("/v1/messages", json=payload)
        except Exception as e:
            raise ProviderException(f"请求失败: {e}") from e

        if response.status_code != 200:
            raise ProviderException(
                f"Anthropic Messages API 返回错误: status={response.status_code}, "
                f"body={response.text[:500]}"
            )

        data = response.json()
        clock.stop()

        # 提取输出文本
        output_text = ""
        for content_item in data.get("content", []):
            if content_item.get("type") == "text":
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
        """执行流式 Messages API 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = True

        logger.info(
            "Anthropic Messages API 流式调用: model=%s",
            request.model,
        )

        clock = Clock()
        clock.start()

        try:
            async with self.client.stream(
                "POST", "/v1/messages", json=payload
            ) as response:
                if response.status_code != 200:
                    body = await response.aread()
                    raise ProviderException(
                        f"流式请求失败: status={response.status_code}, "
                        f"body={body[:500]}"
                    )

                usage_data: dict = {}
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
                    if event_type == "content_block_delta":
                        delta = event.get("delta", {})
                        text = delta.get("text", "")
                        if text:
                            clock.mark_first_token()
                            yield StreamChunk(
                                type=StreamEventType.TEXT_DELTA,
                                content=text,
                            )

                    # 处理消息开始事件（记录用量）
                    elif event_type == "message_start":
                        msg = event.get("message", {})
                        usage_data = msg.get("usage", {})

                    # 处理消息结束事件
                    elif event_type == "message_delta":
                        delta_usage = event.get("usage", {})
                        if "output_tokens" in delta_usage:
                            usage_data["output_tokens"] = delta_usage[
                                "output_tokens"
                            ]

                    # 处理消息停止事件
                    elif event_type == "message_stop":
                        clock.stop()
                        usage = self.extract_usage({"usage": usage_data})
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