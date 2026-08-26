"""消息对象定义"""

from typing import Optional

from pydantic import BaseModel, Field

from app.core.constants import Role


class Message(BaseModel):
    """对话消息"""
    role: Role = Field(..., description="消息角色：system/user/assistant/tool")
    content: str = Field(..., description="消息内容")
    name: Optional[str] = Field(default=None, description="发送者名称（可选）")


class SystemMessage(BaseModel):
    """系统提示词（独立定义，便于适配器转换）"""
    content: str = Field(..., description="系统提示词内容")