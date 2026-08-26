"""全局异常处理中间件 —— 捕获所有异常并返回统一错误响应"""

import logging
import traceback

from fastapi import Request
from fastapi.responses import JSONResponse

from app.core.errors import (
    ErrorCode,
    ERROR_CODE_TO_HTTP_STATUS,
    ERROR_CODE_MESSAGES,
)
from app.core.exceptions import GatewayException
from app.schemas.response.error import ErrorDetail

logger = logging.getLogger(__name__)


async def error_handler_middleware(request: Request, call_next):
    """全局异常处理中间件

    捕获链路:
    1. GatewayException → 提取 error_code，返回对应 HTTP 状态码
    2. 其他异常 → 统一返回 500 INTERNAL_ERROR
    """
    try:
        return await call_next(request)
    except GatewayException as e:
        status_code = ERROR_CODE_TO_HTTP_STATUS.get(e.error_code, 500)
        error_detail = ErrorDetail(
            code=e.error_code.value,
            message=e.message,
            request_id=getattr(request.state, "request_id", None),
        )
        logger.warning(
            "业务异常: code=%d, message=%s",
            e.error_code.value,
            e.message,
        )
        return JSONResponse(
            status_code=status_code,
            content=error_detail.model_dump(),
        )
    except Exception as e:
        logger.error(
            "未捕获异常: %s\n%s",
            str(e),
            traceback.format_exc(),
        )
        error_detail = ErrorDetail(
            code=ErrorCode.INTERNAL_ERROR.value,
            message=ERROR_CODE_MESSAGES[ErrorCode.INTERNAL_ERROR],
            request_id=getattr(request.state, "request_id", None),
        )
        return JSONResponse(
            status_code=500,
            content=error_detail.model_dump(),
        )