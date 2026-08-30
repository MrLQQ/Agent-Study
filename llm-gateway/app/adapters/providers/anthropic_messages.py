"""Chat Completions API 适配器（Anthropic 风格配置）

适用模型: deepseek-v4-flash
协议端点: POST /v1/chat/completions

DeepSeek 所有模型均支持 Chat Completions API，此适配器与 openai_responses 适配器
保留独立实现以便未来扩展厂商特定差异。
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
    """Chat Completions API 适配器（DeepSeek 兼容）"""

    # ── 请求构建 ──

    def build_request_payload(self, request: UnifiedRequest) -> dict:
        """构建 Chat Completions API 请求体"""
        messages = []

        if request.system_prompt:
            messages.append({"role": "system", "content": request.system_prompt})

        for m in request.messages:
            messages.append({"role": m.role.value, "content": m.content})

        payload: dict = {
            "model": request.model,
            "messages": messages,
            "stream": request.stream,
        }

        if request.parameters:
            for key in ("temperature", "top_p", "max_tokens"):
                if key in request.parameters:
                    payload[key] = request.parameters[key]

        return payload

    # ── 用量提取 ──

    def extract_usage(self, raw_response: dict) -> Usage:
        """从 Chat Completions 响应中提取 Token 用量"""
        usage_data = raw_response.get("usage", {})
        return Usage(
            prompt_tokens=usage_data.get("prompt_tokens", 0),
            completion_tokens=usage_data.get("completion_tokens", 0),
            total_tokens=usage_data.get("total_tokens", 0),
        )

    # ── 非流式调用 ──

    async def _do_call(
        self, request: UnifiedRequest, clock: Clock
    ) -> UnifiedResponse:
        """执行非流式 Chat Completions 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = False

        logger.info(
            "Chat Completions API 调用: model=%s, stream=False",
            request.model,
        )

        clock.start()
        try:
            response = await self.client.post("/v1/chat/completions", json=payload)
        except Exception as e:
            raise ProviderException(f"请求失败: {e}") from e

        if response.status_code != 200:
            raise ProviderException(
                f"Chat API 返回错误: status={response.status_code}, "
                f"body={response.text[:500]}"
            )

        data = response.json()
        clock.stop()

        output_text = ""
        choices = data.get("choices", [])
        if choices:
            message = choices[0].get("message", {})
            output_text = message.get("content", "")

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
        """执行流式 Chat Completions 调用"""
        payload = self.build_request_payload(request)
        payload["stream"] = True

        logger.info(
            "Chat Completions API 流式调用: model=%s",
            request.model,
        )

        clock = Clock()
        clock.start()

        try:
            async with self.client.stream(
                "POST", "/v1/chat/completions", json=payload
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
                    data_str = line[6:]
                    if data_str.strip() == "[DONE]":
                        break

                    try:
                        event = json.loads(data_str)
                    except json.JSONDecodeError:
                        continue

                    choices = event.get("choices", [])
                    if not choices:
                        continue

                    choice = choices[0]
                    delta = choice.get("delta", {})
                    finish_reason = choice.get("finish_reason")

                    text = delta.get("content", "")
                    if text:
                        clock.mark_first_token()
                        yield StreamChunk(
                            type=StreamEventType.TEXT_DELTA,
                            content=text,
                        )

                    if finish_reason:
                        clock.stop()
                        if "usage" in event:
                            usage_data = event["usage"]
                        usage = self.extract_usage(
                            {"usage": usage_data} if usage_data else {}
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