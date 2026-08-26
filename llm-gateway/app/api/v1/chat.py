"""对话API路由 —— 统一入口，stream=true 控制流式/非流式"""

import json
import logging

from fastapi import APIRouter, Depends, Request
from fastapi.responses import StreamingResponse

from app.api.deps import get_chat_service
from app.schemas.request.chat import ChatRequest
from app.schemas.response.base import BaseResponse
from app.schemas.response.chat import ChatResponse
from app.utils.sse import format_sse, format_sse_done

logger = logging.getLogger(__name__)

router = APIRouter(tags=["对话"])


@router.post("/chat", response_model=None)
async def chat(
    request: Request,
    req: ChatRequest,
    chat_service=Depends(get_chat_service),
):
    """统一对话接口

    - stream=false: 返回标准 JSON 响应（含 content、usage、latency）
    - stream=true:  返回 SSE 流式响应（text_delta → text_done → [DONE]）
    """
    request_id = getattr(request.state, "request_id", None)

    if req.stream:
        # ── 流式响应 ──
        async def event_generator():
            try:
                async for chunk in chat_service.chat_stream(req):
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
        # ── 非流式响应 ──
        chat_response = await chat_service.chat(req)
        return BaseResponse(
            code=0,
            message="success",
            data=chat_response.model_dump(),
            request_id=request_id,
        )