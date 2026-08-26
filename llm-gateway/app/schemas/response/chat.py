"""对话响应体"""

from pydantic import BaseModel, Field

from app.schemas.model.latency import LatencyInfo
from app.schemas.model.usage import Usage


class ChatResponse(BaseModel):
    """非流式对话响应"""
    content: str = Field(default="", description="模型回复内容")
    model: str = Field(default="", description="实际使用的模型名称")
    usage: Usage = Field(default_factory=Usage, description="Token用量")
    latency: LatencyInfo = Field(default_factory=LatencyInfo, description="延迟信息")