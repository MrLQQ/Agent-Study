"""高精度计时器 —— 用于测量首字延迟和总延迟"""

import time


class Clock:
    """高精度计时器

    通俗理解：
    - 就像秒表，按下 start() 开始计时
    - mark_first() 记录"第一个字出现"的时刻
    - stop() 记录"全部完成"的时刻
    - ttft_ms 就是 "从开始到第一个字出现" 的时间差
    """

    def __init__(self) -> None:
        self._start_ns: int = 0
        self._first_token_ns: int = 0
        self._end_ns: int = 0
        self._first_token_seen = False

    def start(self) -> None:
        """开始计时"""
        self._start_ns = time.perf_counter_ns()

    def mark_first_token(self) -> None:
        """标记首字到达"""
        if not self._first_token_seen:
            self._first_token_ns = time.perf_counter_ns()
            self._first_token_seen = True

    def stop(self) -> None:
        """停止计时"""
        self._end_ns = time.perf_counter_ns()

    @property
    def ttft_ms(self) -> float:
        """首字延迟（毫秒）"""
        if not self._first_token_seen:
            return 0.0
        return (self._first_token_ns - self._start_ns) / 1_000_000

    @property
    def total_ms(self) -> float:
        """总延迟（毫秒）"""
        if self._end_ns == 0:
            self._end_ns = time.perf_counter_ns()
        return (self._end_ns - self._start_ns) / 1_000_000