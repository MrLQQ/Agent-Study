"""存储抽象接口"""

from abc import ABC, abstractmethod
from datetime import datetime
from typing import Any, Dict, List, Optional


class UsageRecordStore(ABC):
    """用量记录存储接口"""

    @abstractmethod
    def save(self, record: Dict[str, Any]) -> None:
        """保存一条用量记录"""
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