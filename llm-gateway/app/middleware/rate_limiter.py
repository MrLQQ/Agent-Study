"""限流中间件 —— 按模型维度 TPM 限流，超限返回 429"""

import logging

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

from app.core.errors import ErrorCode, ERROR_CODE_MESSAGES
from app.core.exceptions import RateLimitedException
from app.infrastructure.rate_limiter.engine import tpm_limiter

logger = logging.getLogger(__name__)


class RateLimiterMiddleware(BaseHTTPMiddleware):
    """限流中间件

    仅在 POST /v1/chat 接口触发限流检查
    根据请求体中的 model 字段和预估 Token 数进行 TPM 限流
    """

    async def dispatch(self, request: Request, call_next):
        # 仅对对话接口做限流
        if request.url.path == "/v1/chat" and request.method == "POST":
            # 尝试读取请求体获取 model
            try:
                body = await request.body()
                import json
                data = json.loads(body)
                model = data.get("model", "")
                # 估算 Token 数（简单按字符数/4 估算，实际应更精确）
                messages = data.get("messages", [])
                estimated_tokens = sum(
                    len(m.get("content", "")) for m in messages
                ) // 4 + 100  # +100 作为系统提示词和参数开销

                if model and not tpm_limiter.acquire(model, max(estimated_tokens, 1)):
                    logger.warning("模型 %s 触发限流，返回 429", model)
                    return JSONResponse(
                        status_code=429,
                        content={
                            "code": ErrorCode.RATE_LIMITED.value,
                            "message": ERROR_CODE_MESSAGES[ErrorCode.RATE_LIMITED],
                            "request_id": getattr(
                                request.state, "request_id", None
                            ),
                        },
                    )
            except (json.JSONDecodeError, KeyError):
                # 请求体解析失败，放行（后续由参数校验处理）
                pass

        return await call_next(request)