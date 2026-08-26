"""错误响应体"""

from typing import Optional

from pydantic import BaseModel, Field


class ErrorDetail(BaseModel):
    """错误详情"""
    code: int = Field(..., description="错误码")
    message: str = Field(..., description="错误描述")
    request_id: Optional[str] = Field(default=None, description="请求追踪ID")