"""TPM限流引擎 —— 滑动窗口 + 令牌桶

通俗理解：
- 就像高速公路收费站，每分钟只能放行 N 辆车（Token）
- 如果当前分钟内的 Token 已经用完，后续请求返回 429
- 每分钟重置一次计数器
"""

import time
import threading
import logging
from collections import defaultdict
from typing import Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)


class RateLimitStore:
    """限流状态存储（内存实现）"""

    def __init__(self) -> None:
        # model → [(timestamp, token_count), ...]
        self._windows: Dict[str, List[Tuple[float, int]]] = defaultdict(list)
        self._lock = threading.Lock()

    def record_and_check(
        self, model: str, tokens: int, tpm_limit: int
    ) -> bool:
        """记录Token消耗并检查是否超限

        Returns:
            True: 未超限，允许通过
            False: 已超限，应拒绝
        """
        now = time.time()
        window_start = now - 60  # 60秒滑动窗口

        with self._lock:
            window = self._windows[model]

            # 清理过期记录
            self._windows[model] = [
                (ts, count) for ts, count in window if ts > window_start
            ]
            window = self._windows[model]

            # 计算当前窗口内总Token数
            current_tokens = sum(count for _, count in window)

            if current_tokens + tokens > tpm_limit:
                logger.warning(
                    "模型 %s 触发限流: 当前=%d, 本次=%d, 限制=%d",
                    model, current_tokens, tokens, tpm_limit,
                )
                return False

            # 记录本次消耗
            window.append((now, tokens))
            return True

    def get_current_usage(self, model: str) -> int:
        """获取当前窗口内已使用的Token数"""
        now = time.time()
        window_start = now - 60
        with self._lock:
            window = self._windows[model]
            return sum(
                count for ts, count in window if ts > window_start
            )


class TPMLimiter:
    """TPM限流器

    使用示例:
        limiter = TPMLimiter()
        limiter.set_limit("deepseek-v4-pro", 60000)

        if limiter.acquire("deepseek-v4-pro", 100):
            # 允许调用
            pass
        else:
            # 返回 429
            pass
    """

    def __init__(self) -> None:
        self._store = RateLimitStore()
        self._limits: Dict[str, int] = {}  # model → tpm

    def set_limit(self, model: str, tpm: int) -> None:
        """设置模型的TPM限制"""
        self._limits[model] = tpm
        logger.info("设置限流: model=%s, tpm=%d", model, tpm)

    def acquire(self, model: str, estimated_tokens: int) -> bool:
        """尝试获取Token配额

        Args:
            model: 模型名称
            estimated_tokens: 预估本次请求消耗的Token数

        Returns:
            True: 允许通过
            False: 触发限流
        """
        tpm = self._limits.get(model)
        if tpm is None:
            # 未配置限流的模型，默认放行
            return True
        return self._store.record_and_check(model, estimated_tokens, tpm)

    def get_usage(self, model: str) -> int:
        """获取当前窗口使用量"""
        return self._store.get_current_usage(model)

    def get_limit(self, model: str) -> Optional[int]:
        """获取模型的TPM限制"""
        return self._limits.get(model)


# 全局单例
tpm_limiter = TPMLimiter()