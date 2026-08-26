"""内存存储实现 —— 用量记录存储（后续可替换为数据库）"""

import threading
from datetime import datetime
from typing import Any, Dict, List, Optional

from app.infrastructure.store.base import UsageRecordStore


class MemoryUsageStore(UsageRecordStore):
    """内存存储实现"""

    def __init__(self) -> None:
        self._records: List[Dict[str, Any]] = []
        self._lock = threading.Lock()

    def save(self, record: Dict[str, Any]) -> None:
        """保存一条用量记录"""
        with self._lock:
            self._records.append(record)

    def query(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        limit: int = 100,
    ) -> List[Dict[str, Any]]:
        """查询用量记录"""
        with self._lock:
            results = self._records[:]

        # 按模型过滤
        if model:
            results = [r for r in results if r.get("model") == model]

        # 按时间范围过滤
        if start_time:
            results = [
                r
                for r in results
                if r.get("timestamp")
                and datetime.fromisoformat(r["timestamp"]) >= start_time
            ]
        if end_time:
            results = [
                r
                for r in results
                if r.get("timestamp")
                and datetime.fromisoformat(r["timestamp"]) <= end_time
            ]

        # 按时间倒序并限制数量
        results.sort(
            key=lambda r: r.get("timestamp", ""),
            reverse=True,
        )
        return results[:limit]

    def stats(
        self,
        model: Optional[str] = None,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> Dict[str, Any]:
        """统计用量汇总"""
        records = self.query(
            model=model, start_time=start_time, end_time=end_time, limit=10_000
        )

        total_prompt_tokens = sum(
            r.get("prompt_tokens", 0) for r in records
        )
        total_completion_tokens = sum(
            r.get("completion_tokens", 0) for r in records
        )
        total_requests = len(records)
        success_requests = sum(
            1 for r in records if r.get("success", False)
        )

        # 按模型分组统计
        by_model: Dict[str, Dict[str, int]] = {}
        for r in records:
            m = r.get("model", "unknown")
            if m not in by_model:
                by_model[m] = {
                    "requests": 0,
                    "prompt_tokens": 0,
                    "completion_tokens": 0,
                }
            by_model[m]["requests"] += 1
            by_model[m]["prompt_tokens"] += r.get("prompt_tokens", 0)
            by_model[m]["completion_tokens"] += r.get("completion_tokens", 0)

        return {
            "total_requests": total_requests,
            "success_requests": success_requests,
            "failed_requests": total_requests - success_requests,
            "total_prompt_tokens": total_prompt_tokens,
            "total_completion_tokens": total_completion_tokens,
            "total_tokens": total_prompt_tokens + total_completion_tokens,
            "by_model": by_model,
        }


# 全局单例
usage_store = MemoryUsageStore()