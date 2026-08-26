"""可观测性数据查询API"""

import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, Query

from app.api.deps import get_observability_service
from app.schemas.response.base import BaseResponse
from app.services.interfaces.observability import ObservabilityService

logger = logging.getLogger(__name__)

router = APIRouter(tags=["可观测性"])


@router.get("/observability/records")
async def query_records(
    model: Optional[str] = Query(default=None, description="模型名称过滤"),
    limit: int = Query(default=100, ge=1, le=1000),
    obs: ObservabilityService = Depends(get_observability_service),
):
    """查询用量记录"""
    records = obs.query(model=model, limit=limit)
    return BaseResponse(
        code=0,
        message="success",
        data={"records": records, "total": len(records)},
    )


@router.get("/observability/stats")
async def query_stats(
    model: Optional[str] = Query(default=None, description="模型名称过滤"),
    obs: ObservabilityService = Depends(get_observability_service),
):
    """查询用量统计汇总"""
    stats = obs.stats(model=model)
    return BaseResponse(
        code=0,
        message="success",
        data=stats,
    )


@router.get("/models")
async def list_models():
    """列出所有可用模型"""
    from app.adapters.registry import registry

    models = registry.list_models()
    return BaseResponse(
        code=0,
        message="success",
        data={"models": models},
    )