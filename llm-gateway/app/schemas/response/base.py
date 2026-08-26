"""统一响应基类"""

from typing import Any, Optional

from pydantic import BaseModel, Field


class BaseResponse(BaseModel):
    """统一API响应格式"""
    code: int = Field(default=0, description="业务状态码，0 表示成功")
    message: str = Field(default="success", description="提示信息")
    data: Any = Field(default=None, description="响应数据体")
    request_id: Optional[str] = Field(default=None, description="请求追踪ID")