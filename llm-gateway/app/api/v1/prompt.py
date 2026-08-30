"""提示词模板管理API"""

import json
import logging
from typing import Dict, Optional

from fastapi import APIRouter, Depends, Query, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service, get_prompt_service
from app.core.constants import Role
from app.schemas.model.message import Message
from app.schemas.request.chat import ChatRequest
from app.schemas.response.base import BaseResponse
from app.services.interfaces.chat import ChatService
from app.services.interfaces.prompt import PromptService
from app.utils.sse import format_sse, format_sse_done

logger = logging.getLogger(__name__)

router = APIRouter(tags=["模板"])


@router.get("/templates")
async def list_templates(
    request: Request,
    prompt_service: PromptService = Depends(get_prompt_service),
):
    """列出所有可用模板"""
    request_id = getattr(request.state, "request_id", None)
    templates = prompt_service.list_templates()
    return BaseResponse(
        code=0,
        message="success",
        data={"templates": templates},
        request_id=request_id,
    )


@router.post("/templates/render")
async def render_template(
    request: Request,
    template_ref: str = Query(..., description="模板引用，如 v1:chat_default"),
    variables: Dict[str, str] = ...,
    model: Optional[str] = Query(default=None, description="指定模型名称则直接调用模型"),
    stream: bool = Query(default=False, description="是否流式返回（仅 model 不为空时生效）"),
    prompt_service: PromptService = Depends(get_prompt_service),
    chat_service: ChatService = Depends(get_chat_service),
):
    """渲染模板并可选调用模型

    - 仅渲染：不传 model 参数，返回渲染后的模板文本
    - 调用模型：传入 model 参数，将渲染结果作为 system_prompt 调用模型，
      variables 中的 user_input 字段作为用户消息
    """
    request_id = getattr(request.state, "request_id", None)

    # 渲染模板
    rendered = prompt_service.render(template_ref, variables)

    if model:
        # ── 调用模型 ──
        user_input = variables.get("user_input", "")
        chat_req = ChatRequest(
            model=model,
            messages=[Message(role=Role.USER, content=user_input)] if user_input else [],
            system_prompt=rendered,
            stream=stream,
            context={"trace_id": request_id or ""},
        )

        if stream:
            # 流式响应
            async def event_generator():
                try:
                    async for chunk in chat_service.chat_stream(chat_req):
                        yield format_sse(chunk)
                    yield format_sse_done()
                except Exception as e:
                    logger.error("流式响应异常: %s", e)
                    error_chunk = json.dumps(
                        {"type": "error", "error": str(e)},
                        ensure_ascii=False,
                    )
                    yield f"data: {error_chunk}\n\n"
                    yield format_sse_done()

            return StreamingResponse(
                event_generator(),
                media_type="text/event-stream",
                headers={
                    "Cache-Control": "no-cache",
                    "Connection": "keep-alive",
                    "X-Request-ID": request_id or "",
                },
            )
        else:
            # 非流式响应
            chat_response = await chat_service.chat(chat_req)
            return BaseResponse(
                code=0,
                message="success",
                data=chat_response.model_dump(),
                request_id=request_id,
            )
    else:
        # ── 仅渲染模板，不调用模型（向后兼容） ──
        return BaseResponse(
            code=0,
            message="success",
            data={"rendered": rendered},
            request_id=request_id,
        )