"""统一错误码枚举 —— 所有业务异常都必须携带 ErrorCode"""

from enum import IntEnum
from typing import Dict


class ErrorCode(IntEnum):
    # ── 成功 ──
    SUCCESS = 0

    # ── 客户端错误（1xxx）──
    VALIDATION_ERROR = 1001          # 请求参数校验失败
    MODEL_NOT_FOUND = 1002           # 请求的模型不存在
    TEMPLATE_NOT_FOUND = 1003        # 提示词模板不存在
    TEMPLATE_RENDER_ERROR = 1004     # 模板渲染失败

    # ── 限流错误（2xxx）──
    RATE_LIMITED = 2001              # 触发TPM限流

    # ── 服务端错误（3xxx）──
    INTERNAL_ERROR = 3001            # 内部未知错误
    PROVIDER_ERROR = 3002            # 模型供应商返回错误
    MODEL_TIMEOUT = 3003             # 模型调用超时
    ADAPTER_ERROR = 3004             # 适配器转换错误

    # ── 重试耗尽（4xxx）──
    RETRY_EXHAUSTED = 4001           # 重试次数耗尽


# 错误码对应的 HTTP 状态码
ERROR_CODE_TO_HTTP_STATUS: Dict[ErrorCode, int] = {
    ErrorCode.SUCCESS: 200,
    ErrorCode.VALIDATION_ERROR: 422,
    ErrorCode.MODEL_NOT_FOUND: 404,
    ErrorCode.TEMPLATE_NOT_FOUND: 404,
    ErrorCode.TEMPLATE_RENDER_ERROR: 400,
    ErrorCode.RATE_LIMITED: 429,
    ErrorCode.INTERNAL_ERROR: 500,
    ErrorCode.PROVIDER_ERROR: 502,
    ErrorCode.MODEL_TIMEOUT: 504,
    ErrorCode.ADAPTER_ERROR: 500,
    ErrorCode.RETRY_EXHAUSTED: 502,
}

# 错误码对应的默认消息
ERROR_CODE_MESSAGES: Dict[ErrorCode, str] = {
    ErrorCode.SUCCESS: "success",
    ErrorCode.VALIDATION_ERROR: "请求参数校验失败",
    ErrorCode.MODEL_NOT_FOUND: "请求的模型不存在",
    ErrorCode.TEMPLATE_NOT_FOUND: "提示词模板不存在",
    ErrorCode.TEMPLATE_RENDER_ERROR: "模板渲染失败",
    ErrorCode.RATE_LIMITED: "请求频率超限，请稍后重试",
    ErrorCode.INTERNAL_ERROR: "服务内部错误",
    ErrorCode.PROVIDER_ERROR: "模型供应商返回错误",
    ErrorCode.MODEL_TIMEOUT: "模型调用超时",
    ErrorCode.ADAPTER_ERROR: "适配器转换错误",
    ErrorCode.RETRY_EXHAUSTED: "重试次数耗尽，模型调用失败",
}