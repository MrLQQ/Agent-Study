"""通用校验工具"""

import re
from app.core.exceptions import ValidationException


def validate_model_name(model: str) -> None:
    """校验模型名称格式"""
    if not model or not model.strip():
        raise ValidationException("模型名称不能为空")
    if not re.match(r"^[a-zA-Z0-9_\-\.]+$", model):
        raise ValidationException(f"模型名称格式无效: {model}")


def validate_template_ref(template_ref: str) -> tuple[str, str]:
    """校验并解析模板引用格式 'v1:chat_default' → (version, name)"""
    if ":" not in template_ref:
        raise ValidationException(
            f"模板引用格式错误: '{template_ref}'，应为 '版本:名称'，如 'v1:chat_default'"
        )
    parts = template_ref.split(":", 1)
    version, name = parts[0].strip(), parts[1].strip()
    if not version or not name:
        raise ValidationException(
            f"模板引用格式错误: '{template_ref}'，版本和名称不能为空"
        )
    return version, name