"""提示词模板服务接口"""

from abc import ABC, abstractmethod
from typing import Dict, List


class PromptService(ABC):
    """提示词模板服务抽象接口"""

    @abstractmethod
    def render(self, template_ref: str, variables: Dict[str, str]) -> str:
        """渲染模板"""
        ...

    @abstractmethod
    def list_templates(self) -> List[str]:
        """列出所有可用模板"""
        ...