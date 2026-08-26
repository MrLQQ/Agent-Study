"""适配器基类 —— 提供重试、超时等公共能力"""

import asyncio
import logging
from collections.abc import AsyncGenerator
from abc import abstractmethod
from typing import Any, Optional

import httpx

from app.adapters.protocol import (
    BaseAdapterProtocol,
    UnifiedRequest,
    UnifiedResponse,
)
from app.core.config import settings, get_api_key, ModelConfig
from app.core.exceptions import (
    ProviderException,
    ModelTimeoutException,
    RetryExhaustedException,
)
from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage
from app.schemas.response.stream import StreamChunk, StreamEventType
from app.utils.clock import Clock

logger = logging.getLogger(__name__)


class BaseAdapter(BaseAdapterProtocol):
    """适配器基类

    封装了：
    - 指数退避重试（最多 N 次）
    - 超时控制
    - HTTP 客户端管理
    """

    def __init__(self, model_config: ModelConfig) -> None:
        self.model_config = model_config
        self.api_key = get_api_key(model_config.api_key_env)
        self._client: Optional[httpx.AsyncClient] = None

    @property
    def client(self) -> httpx.AsyncClient:
        """懒加载 HTTP 客户端"""
        if self._client is None:
            self._client = httpx.AsyncClient(
                base_url=self.model_config.api_base,
                timeout=httpx.Timeout(
                    settings.timeout.request_seconds,
                    connect=settings.timeout.connect_seconds,
                ),
                headers={
                    "Authorization": f"Bearer {self.api_key}",
                    "Content-Type": "application/json",
                },
            )
        return self._client

    async def close(self) -> None:
        """关闭 HTTP 客户端"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    # ── 重试逻辑 ──

    async def _retry_call(
        self, request: UnifiedRequest, clock: Clock
    ) -> UnifiedResponse:
        """带指数退避重试的非流式调用"""
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.retry.max_attempts + 1):
            try:
                return await self._do_call(request, clock)
            except (ProviderException, ModelTimeoutException) as e:
                last_error = e
                if attempt < settings.retry.max_attempts:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        "模型 %s 调用失败(第%d次)，%s后重试: %s",
                        request.model, attempt, f"{delay:.1f}s", e,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "模型 %s 重试耗尽(%d次): %s",
                        request.model, attempt, e,
                    )
        raise RetryExhaustedException(request.model) from last_error

    async def _retry_stream(
        self, request: UnifiedRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """带指数退避重试的流式调用"""
        last_error: Optional[Exception] = None
        for attempt in range(1, settings.retry.max_attempts + 1):
            try:
                async for chunk in self._do_stream(request):
                    yield chunk
                return  # 流式成功完成
            except (ProviderException, ModelTimeoutException) as e:
                last_error = e
                if attempt < settings.retry.max_attempts:
                    delay = self._backoff_delay(attempt)
                    logger.warning(
                        "模型 %s 流式调用失败(第%d次)，%s后重试: %s",
                        request.model, attempt, f"{delay:.1f}s", e,
                    )
                    await asyncio.sleep(delay)
                else:
                    logger.error(
                        "模型 %s 流式重试耗尽(%d次): %s",
                        request.model, attempt, e,
                    )
        # 重试耗尽，发送错误事件
        yield StreamChunk(
            type=StreamEventType.ERROR,
            error=str(RetryExhaustedException(request.model)),
        )

    def _backoff_delay(self, attempt: int) -> float:
        """计算指数退避延迟: base * multiplier^(attempt-1)，不超过最大值"""
        delay = settings.retry.backoff_base_seconds * (
            settings.retry.backoff_multiplier ** (attempt - 1)
        )
        return min(delay, settings.retry.max_backoff_seconds)

    # ── 子类需要实现的方法 ──

    @abstractmethod
    async def _do_call(
        self, request: UnifiedRequest, clock: Clock
    ) -> UnifiedResponse:
        """实际执行非流式调用（子类实现）"""
        ...

    @abstractmethod
    async def _do_stream(
        self, request: UnifiedRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """实际执行流式调用（子类实现）"""
        ...

    # ── 公共接口 ──

    async def call(self, request: UnifiedRequest) -> UnifiedResponse:
        """非流式调用入口（含重试）"""
        clock = Clock()
        return await self._retry_call(request, clock)

    async def stream(
        self, request: UnifiedRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用入口（含重试）"""
        async for chunk in self._retry_stream(request):
            yield chunk