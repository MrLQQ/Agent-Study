"""Jinja2模板加载器 —— 支持版本化模板存储与变量替换

通俗理解：
- 就像邮件模板，占位符 {{name}} 在发送时被替换为实际姓名
- 模板按版本目录组织（v1/v2），支持A/B切换
- 通过 template_ref（如 "v1:chat_default"）引用特定版本的模板
"""

import logging
from pathlib import Path
from typing import Dict, List

from jinja2 import Environment, FileSystemLoader, TemplateNotFound

from app.core.config import settings, PROJECT_ROOT
from app.core.exceptions import TemplateNotFoundException

logger = logging.getLogger(__name__)


class TemplateLoader:
    """Jinja2模板加载器

    模板目录结构:
        prompts/
        ├── v1/
        │   ├── chat_default.j2
        │   └── code_review.j2
        └── v2/
            └── chat_default.j2

    引用方式:
        "v1:chat_default"  → prompts/v1/chat_default.j2
        "v2:code_review"   → prompts/v2/code_review.j2
    """

    def __init__(self) -> None:
        self._templates_dir = PROJECT_ROOT / settings.templates.base_dir
        if not self._templates_dir.exists():
            raise FileNotFoundError(
                f"模板目录不存在: {self._templates_dir}"
            )
        self._env = Environment(
            loader=FileSystemLoader(str(self._templates_dir)),
            autoescape=False,  # 模板内容不需要HTML转义
            trim_blocks=True,
            lstrip_blocks=True,
        )

    def render(self, template_ref: str, variables: Dict[str, str]) -> str:
        """加载并渲染模板

        Args:
            template_ref: 模板引用，格式 "版本:名称"，如 "v1:chat_default"
            variables: 模板变量键值对

        Returns:
            渲染后的字符串

        Raises:
            TemplateNotFoundException: 模板不存在
        """
        # 解析引用 → "v1/chat_default.j2"
        template_path = template_ref.replace(":", "/") + ".j2"
        try:
            template = self._env.get_template(template_path)
        except TemplateNotFound:
            raise TemplateNotFoundException(template_ref)

        result = template.render(**variables)
        logger.info(
            "模板渲染成功: ref=%s, vars=%s",
            template_ref,
            list(variables.keys()),
        )
        return result.strip()

    def list_templates(self) -> List[str]:
        """列出所有可用模板引用"""
        templates = []
        for version_dir in self._templates_dir.iterdir():
            if not version_dir.is_dir():
                continue
            for template_file in version_dir.glob("*.j2"):
                ref = f"{version_dir.name}:{template_file.stem}"
                templates.append(ref)
        return sorted(templates)


# 全局单例
template_loader = TemplateLoader()