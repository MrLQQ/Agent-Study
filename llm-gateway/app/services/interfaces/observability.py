"""可观测性服务接口"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class ObservabilityService(ABC):
    """可观测性服务抽象接口"""

    @abstractmethod
    def record(self, record: Dict[str, Any]) -> None:
        """记录一次调用的可观测数据"""
        ...

    @abstractmethod
    def query(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询用量记录"""
        ...

    @abstractmethod
    def stats(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """统计用量汇总"""
        ...