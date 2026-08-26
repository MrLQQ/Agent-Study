"""ID生成器"""

import uuid


def generate_request_id() -> str:
    """生成请求追踪ID"""
    return uuid.uuid4().hex[:16]


def generate_conversation_id() -> str:
    """生成会话ID"""
    return f"conv_{uuid.uuid4().hex[:12]}"