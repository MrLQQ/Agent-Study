"""SSE格式化工具"""

import json

from app.schemas.response.stream import StreamChunk


def format_sse(chunk: StreamChunk) -> str:
    """将 StreamChunk 格式化为 SSE 事件字符串

    SSE 格式: data: {json}\n\n
    """
    payload = chunk.model_dump(exclude_none=True)
    return f"data: {json.dumps(payload, ensure_ascii=False)}\n\n"


def format_sse_done() -> str:
    """发送 SSE 完成信号"""
    return "data: [DONE]\n\n"