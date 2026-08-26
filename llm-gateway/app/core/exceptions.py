"""自定义异常类 —— 携带 ErrorCode，供中间件统一捕获"""

from typing import Optional

from app.core.errors import ErrorCode, ERROR_CODE_MESSAGES


class GatewayException(Exception):
    """Gateway 基础异常"""

    def __init__(self, error_code: ErrorCode, message: Optional[str] = None):
        self.error_code = error_code
        self.message = message or ERROR_CODE_MESSAGES.get(error_code, "未知错误")
        super().__init__(self.message)


class ValidationException(GatewayException):
    """参数校验异常"""

    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.VALIDATION_ERROR, message)


class ModelNotFoundException(GatewayException):
    """模型不存在异常"""

    def __init__(self, model: Optional[str] = None):
        msg = f"模型 '{model}' 不存在" if model else None
        super().__init__(ErrorCode.MODEL_NOT_FOUND, msg)


class TemplateNotFoundException(GatewayException):
    """模板不存在异常"""

    def __init__(self, template_ref: Optional[str] = None):
        msg = f"模板 '{template_ref}' 不存在" if template_ref else None
        super().__init__(ErrorCode.TEMPLATE_NOT_FOUND, msg)


class RateLimitedException(GatewayException):
    """限流异常"""

    def __init__(self, model: Optional[str] = None):
        msg = f"模型 '{model}' 触发限流" if model else None
        super().__init__(ErrorCode.RATE_LIMITED, msg)


class ProviderException(GatewayException):
    """模型供应商异常"""

    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.PROVIDER_ERROR, message)


class ModelTimeoutException(GatewayException):
    """模型超时异常"""

    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.MODEL_TIMEOUT, message)


class AdapterException(GatewayException):
    """适配器异常"""

    def __init__(self, message: Optional[str] = None):
        super().__init__(ErrorCode.ADAPTER_ERROR, message)


class RetryExhaustedException(GatewayException):
    """重试耗尽异常"""

    def __init__(self, model: Optional[str] = None):
        msg = f"模型 '{model}' 重试耗尽" if model else None
        super().__init__(ErrorCode.RETRY_EXHAUSTED, msg)