"""上下文传递对象"""

from typing import Optional

from pydantic import BaseModel, Field


class Context(BaseModel):
    """会话上下文"""
    conversation_id: Optional[str] = Field(default=None, description="会话ID")
    user_id: Optional[str] = Field(default=None, description="用户ID")
    trace_id: Optional[str] = Field(default=None, description="链路追踪ID")