"""FastAPI 依赖注入 —— 提供各类服务实例"""

from typing import Optional

from app.services.impl.chat_impl import ChatServiceImpl
from app.services.impl.observability_impl import ObservabilityServiceImpl
from app.services.impl.prompt_impl import PromptServiceImpl
from app.services.interfaces.chat import ChatService
from app.services.interfaces.observability import ObservabilityService
from app.services.interfaces.prompt import PromptService

# ── 懒加载单例 ──

_observability_svc: Optional[ObservabilityService] = None
_chat_svc: Optional[ChatService] = None
_prompt_svc: Optional[PromptService] = None


def get_observability_service() -> ObservabilityService:
    """获取可观测性服务实例"""
    global _observability_svc
    if _observability_svc is None:
        _observability_svc = ObservabilityServiceImpl()
    return _observability_svc


def get_chat_service() -> ChatService:
    """获取对话服务实例"""
    global _chat_svc
    if _chat_svc is None:
        _chat_svc = ChatServiceImpl(get_observability_service())
    return _chat_svc


def get_prompt_service() -> PromptService:
    """获取模板服务实例"""
    global _prompt_svc
    if _prompt_svc is None:
        _prompt_svc = PromptServiceImpl()
    return _prompt_svc