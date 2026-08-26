"""统一对话请求体"""

from typing import Dict, List, Optional, Union

from pydantic import BaseModel, Field

from app.schemas.model.message import Message


class ChatRequest(BaseModel):
    """统一对话请求 —— 适配器层根据此结构转换为各厂商格式"""
    model: str = Field(
        ...,
        description="模型标识，如 deepseek-v4-pro / deepseek-v4-flash",
        examples=["deepseek-v4-pro"],
    )
    messages: List[Message] = Field(
        default_factory=list,
        description="对话消息列表",
    )
    stream: bool = Field(
        default=False,
        description="是否开启流式响应（SSE格式）",
    )
    system_prompt: Optional[str] = Field(
        default=None,
        description="系统提示词（直接传入时使用，与 template_ref 互斥）",
    )
    template_ref: Optional[str] = Field(
        default=None,
        description="引用的提示词模板版本，格式: 'v1:chat_default'",
        examples=["v1:chat_default"],
    )
    template_vars: Dict[str, str] = Field(
        default_factory=dict,
        description="模板变量键值对，用于 Jinja2 渲染",
    )
    parameters: Dict[str, Union[float, int]] = Field(
        default_factory=dict,
        description="模型参数，如 temperature、top_p、max_tokens 等",
    )
    context: Dict[str, str] = Field(
        default_factory=dict,
        description="会话上下文，如 conversation_id, user_id, trace_id",
    )