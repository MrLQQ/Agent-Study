"""提示词模板管理API"""

import logging
from typing import Dict

from fastapi import APIRouter, Depends

from app.api.deps import get_prompt_service
from app.schemas.response.base import BaseResponse
from app.services.interfaces.prompt import PromptService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["模板"])


@router.get("/templates")
async def list_templates(
    prompt_service: PromptService = Depends(get_prompt_service),
):
    """列出所有可用模板"""
    templates = prompt_service.list_templates()
    return BaseResponse(
        code=0,
        message="success",
        data={"templates": templates},
    )


@router.post("/templates/render")
async def render_template(
    template_ref: str,
    variables: Dict[str, str],
    prompt_service: PromptService = Depends(get_prompt_service),
):
    """渲染模板"""
    result = prompt_service.render(template_ref, variables)
    return BaseResponse(
        code=0,
        message="success",
        data={"rendered": result},
    )