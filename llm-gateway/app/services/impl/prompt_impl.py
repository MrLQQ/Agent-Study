"""提示词模板服务实现"""

from typing import Dict, List

from app.infrastructure.template_loader import template_loader
from app.services.interfaces.prompt import PromptService


class PromptServiceImpl(PromptService):
    """提示词模板服务实现"""

    def render(self, template_ref: str, variables: Dict[str, str]) -> str:
        return template_loader.render(template_ref, variables)

    def list_templates(self) -> List[str]:
        return template_loader.list_templates()