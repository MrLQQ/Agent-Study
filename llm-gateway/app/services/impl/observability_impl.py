"""可观测性服务实现"""

from datetime import datetime
from typing import Any, Dict, List, Optional

from app.infrastructure.store.memory import usage_store
from app.services.interfaces.observability import ObservabilityService


class ObservabilityServiceImpl(ObservabilityService):
    """可观测性服务实现"""

    def record(self, record: Dict[str, Any]) -> None:
        usage_store.save(record)

    def query(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        return usage_store.query(
            model=model,
            start_time=start_time,
            end_time=end_time,
            limit=limit,
        )

    def stats(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        return usage_store.stats(
            model=model,
            start_time=start_time,
            end_time=end_time,
        )