"""适配器注册表 —— 工厂模式，根据 model 字段动态路由到对应适配器"""

import logging
from typing import Dict, List, TYPE_CHECKING

from app.core.exceptions import ModelNotFoundException
from app.adapters.protocol import BaseAdapterProtocol

if TYPE_CHECKING:
    from app.core.config import ModelConfig

logger = logging.getLogger(__name__)


class AdapterRegistry:
    """适配器注册表

    工作流程：
    1. 启动时注册所有 model → adapter 映射
    2. 运行时通过 resolve(model) 获取对应适配器
    """

    def __init__(self) -> None:
        self._adapters: Dict[str, BaseAdapterProtocol] = {}
        self._model_to_provider: Dict[str, str] = {}

    def register(
        self,
        model_name: str,
        provider_type: str,
        adapter: BaseAdapterProtocol,
    ) -> None:
        """注册模型与适配器的映射"""
        self._adapters[model_name] = adapter
        self._model_to_provider[model_name] = provider_type
        logger.info(
            "注册适配器: model=%s, provider=%s",
            model_name,
            provider_type,
        )

    def resolve(self, model: str) -> BaseAdapterProtocol:
        """根据模型名称获取适配器实例"""
        if model not in self._adapters:
            raise ModelNotFoundException(model)
        return self._adapters[model]

    def get_provider_type(self, model: str) -> str:
        """获取模型的供应商类型"""
        if model not in self._model_to_provider:
            raise ModelNotFoundException(model)
        return self._model_to_provider[model]

    def list_models(self) -> List[str]:
        """列出所有已注册的模型"""
        return list(self._adapters.keys())


# 全局单例
registry = AdapterRegistry()