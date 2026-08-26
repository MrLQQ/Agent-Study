"""SSE流式响应块格式定义"""

from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import StreamEventType
from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage


class StreamChunk(BaseModel):
    """SSE流式响应块"""
    type: StreamEventType = Field(..., description="事件类型")
    content: str = Field(default="", description="文本内容（text_delta类型时使用）")
    usage: Optional[Usage] = Field(default=None, description="Token用量（text_done类型时使用）")
    latency: Optional[LatencyInfo] = Field(default=None, description="延迟信息（text_done类型时使用）")
    error: Optional[str] = Field(default=None, description="错误信息（error类型时使用）")