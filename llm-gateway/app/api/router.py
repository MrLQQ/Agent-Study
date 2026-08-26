"""主路由聚合器"""

from fastapi import APIRouter

from app.api.v1.chat import router as chat_router
from app.api.v1.prompt import router as prompt_router
from app.api.v1.observability import router as observability_router

router = APIRouter(prefix="/v1")

router.include_router(chat_router)
router.include_router(prompt_router)
router.include_router(observability_router)