"""延迟统计对象"""

from pydantic import BaseModel, Field


class LatencyInfo(BaseModel):
    """延迟信息"""
    ttft_ms: float = Field(default=0.0, description="首字延迟（Time To First Token），毫秒")
    total_ms: float = Field(default=0.0, description="端到端总延迟，毫秒")