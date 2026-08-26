"""适配器统一协议（抽象基类）

所有模型适配器必须实现此协议，屏蔽不同厂商API的差异：
- OpenAI Responses API：POST /v1/responses，input/instructions 字段
- Anthropic Messages API：POST /v1/messages，messages/system 字段
"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator
from dataclasses import dataclass
from typing import List, Optional

from app.schemas.model.latency import LatencyInfo
from app.schemas.model.message import Message
from app.schemas.model.usage import Usage
from app.schemas.response.stream import StreamChunk


@dataclass
class UnifiedRequest:
    """统一请求结构 —— 适配器将 ChatRequest 转换为此结构"""
    model: str
    messages: List[Message]
    system_prompt: Optional[str]
    stream: bool
    parameters: dict


@dataclass
class UnifiedResponse:
    """统一响应结构 —— 适配器将各厂商响应统一解析为此结构"""
    content: str
    model: str
    usage: Usage
    latency: LatencyInfo


class BaseAdapterProtocol(ABC):
    """适配器抽象协议"""

    @abstractmethod
    async def call(self, request: UnifiedRequest) -> UnifiedResponse:
        """非流式调用 —— 返回完整响应"""
        ...

    @abstractmethod
    async def stream(
        self, request: UnifiedRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式调用 —— 返回 SSE 事件流"""
        ...

    @abstractmethod
    def extract_usage(self, raw_response: dict) -> Usage:
        """从原始响应中提取 Token 用量"""
        ...

    @abstractmethod
    def build_request_payload(self, request: UnifiedRequest) -> dict:
        """将统一请求构建为厂商特定格式的请求体"""
        ...