"""对话服务接口"""

from abc import ABC, abstractmethod
from collections.abc import AsyncGenerator

from app.schemas.request.chat import ChatRequest
from app.schemas.response.chat import ChatResponse
from app.schemas.response.stream import StreamChunk


class ChatService(ABC):
    """对话服务抽象接口"""

    @abstractmethod
    async def chat(self, request: ChatRequest) -> ChatResponse:
        """非流式对话"""
        ...

    @abstractmethod
    async def chat_stream(
        self, request: ChatRequest
    ) -> AsyncGenerator[StreamChunk, None]:
        """流式对话"""
        ...