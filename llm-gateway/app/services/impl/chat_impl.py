"""对话服务实现 —— 编排 adapter 调用、模板渲染、可观测记录"""

import logging
from collections.abc import AsyncGenerator
from datetime import datetime, timezone
from typing import Optional

from app.adapters.protocol import UnifiedRequest
from app.adapters.registry import registry
from app.core.exceptions import GatewayException, ModelNotFoundException
from app.infrastructure.template_loader import template_loader
from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage
from app.schemas.request.chat import ChatRequest
from app.schemas.response.chat import ChatResponse
from app.schemas.response.stream import StreamChunk
from app.services.interfaces.chat import ChatService
from app.services.interfaces.observability import ObservabilityService
from app.utils.validators import validate_model_name, validate_template_ref

logger = logging.getLogger(__name__)


class ChatServiceImpl(ChatService):
    """对话服务实现

    核心流程:
    1. 校验请求参数
    2. 加载/渲染提示词模板
    3. 构建统一请求
    4. 路由到对应适配器
    5. 记录可观测数据
    6. 返回统一响应
    """

    def __init__(self, observability: ObservabilityService) -> None:
        self._obs = observability

    # ── 非流式对话 ──

    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        validate_model_name(request.model)
        system_prompt = self._resolve_system_prompt(request)

        unified = UnifiedRequest(
            model=request.model,
            messages=request.messages,
            system_prompt=system_prompt,
            stream=False,
            parameters=request.parameters,
        )

        adapter = registry.resolve(request.model)
        response = await adapter.call(unified)

        # 记录可观测数据
        self._obs.record({
            "request_id": request.context.get("trace_id", ""),
            "model": request.model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": response.usage.prompt_tokens,
            "completion_tokens": response.usage.completion_tokens,
            "total_tokens": response.usage.total_tokens,
            "ttft_ms": response.latency.ttft_ms,
            "total_latency_ms": response.latency.total_ms,
            "success": True,
            "error_code": None,
            "retry_count": 0,
        })

        return ChatResponse(
            content=response.content,
            model=response.model,
            usage=response.usage,
            latency=response.latency,
        )

    # ── 流式对话 ──

    async def chat_stream(
        self, request: ChatRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式对话"""
        validate_model_name(request.model)
        system_prompt = self._resolve_system_prompt(request)

        unified = UnifiedRequest(
            model=request.model,
            messages=request.messages,
            system_prompt=system_prompt,
            stream=True,
            parameters=request.parameters,
        )

        adapter = registry.resolve(request.model)
        usage = Usage()
        latency = LatencyInfo()

        async for chunk in adapter.stream(unified):
            # 收集最终用量和延迟数据
            if chunk.usage:
                usage = chunk.usage
            if chunk.latency:
                latency = chunk.latency
            yield chunk

        # 流式结束后记录可观测数据
        self._obs.record({
            "request_id": request.context.get("trace_id", ""),
            "model": request.model,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "prompt_tokens": usage.prompt_tokens,
            "completion_tokens": usage.completion_tokens,
            "total_tokens": usage.total_tokens,
            "ttft_ms": latency.ttft_ms,
            "total_latency_ms": latency.total_ms,
            "success": True,
            "error_code": None,
            "retry_count": 0,
        })

    # ── 私有方法 ──

    def _resolve_system_prompt(self, request: ChatRequest) -> Optional[str]:
        """解析系统提示词：优先使用模板，其次使用直接传入的 system_prompt"""
        if request.template_ref:
            validate_template_ref(request.template_ref)
            return template_loader.render(
                request.template_ref, request.template_vars
            )
        return request.system_prompt