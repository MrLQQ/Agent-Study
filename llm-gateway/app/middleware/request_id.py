"""请求ID注入中间件 —— 为每个请求注入 X-Request-ID"""

import uuid

from fastapi import Request
from starlette.middleware.base import BaseHTTPMiddleware


class RequestIDMiddleware(BaseHTTPMiddleware):
    """请求ID中间件

    1. 从请求头 X-Request-ID 提取，不存在则生成
    2. 注入到 request.state.request_id
    3. 注入到响应头 X-Request-ID
    """

    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID") or uuid.uuid4().hex[:16]
        request.state.request_id = request_id

        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response