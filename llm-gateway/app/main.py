"""LLM Gateway 应用入口

启动: cd llm-gateway && python -m app.main
"""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.router import router as api_router
from app.adapters.providers.anthropic_messages import AnthropicMessagesAdapter
from app.adapters.providers.openai_responses import OpenAIResponsesAdapter
from app.adapters.registry import registry
from app.core.config import settings, get_api_key
from app.core.logging import setup_logging
from app.infrastructure.rate_limiter.engine import tpm_limiter
from app.middleware.error_handler import error_handler_middleware
from app.middleware.rate_limiter import RateLimiterMiddleware
from app.middleware.request_id import RequestIDMiddleware

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    # ── 启动阶段 ──
    setup_logging()

    # 注册适配器
    _register_adapters()

    # 初始化限流配置
    _init_rate_limits()

    logger.info("LLM Gateway 启动完成")
    yield
    # ── 关闭阶段 ──
    logger.info("LLM Gateway 关闭")


def _register_adapters() -> None:
    """注册所有模型适配器到注册表"""
    for model_config in settings.models:
        if model_config.provider == "openai_responses":
            adapter = OpenAIResponsesAdapter(model_config)
        elif model_config.provider == "anthropic_messages":
            adapter = AnthropicMessagesAdapter(model_config)
        else:
            logger.warning(
                "未知的适配器类型: %s，跳过模型 %s",
                model_config.provider,
                model_config.name,
            )
            continue
        registry.register(
            model_name=model_config.name,
            provider_type=model_config.provider,
            adapter=adapter,
        )


def _init_rate_limits() -> None:
    """初始化限流配置"""
    for rl_config in settings.rate_limits:
        tpm_limiter.set_limit(rl_config.model, rl_config.tpm)


def create_app() -> FastAPI:
    """创建 FastAPI 应用"""
    app = FastAPI(
        title="LLM Gateway",
        description="统一LLM Gateway服务 —— 支持多模型适配、流式/非流式、模板管理、可观测性",
        version="0.1.0",
        lifespan=lifespan,
    )

    # ── 中间件注册（后注册的先执行）──
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(RequestIDMiddleware)
    app.add_middleware(RateLimiterMiddleware)
    app.middleware("http")(error_handler_middleware)

    # ── 路由注册 ──
    app.include_router(api_router)

    return app


app = create_app()

if __name__ == "__main__":
    import uvicorn

    uvicorn.run(
        "app.main:app",
        host=settings.server.host,
        port=settings.server.port,
        reload=True,
        log_level=settings.log_level.lower(),
    )