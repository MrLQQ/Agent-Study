"""常量定义"""
from enum import Enum


class Role(str, Enum):
    """消息角色"""
    SYSTEM = "system"
    USER = "user"
    ASSISTANT = "assistant"
    TOOL = "tool"


class StreamEventType(str, Enum):
    """SSE流式事件类型"""
    TEXT_DELTA = "text_delta"       # 文本增量
    TEXT_DONE = "text_done"         # 文本完成
    ERROR = "error"                 # 错误事件


class ResponseStatus(str, Enum):
    """响应状态"""
    SUCCESS = "success"
    ERROR = "error"