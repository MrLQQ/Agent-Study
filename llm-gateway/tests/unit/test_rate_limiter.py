"""限流引擎测试"""

import pytest

from app.infrastructure.rate_limiter.engine import TPMLimiter


class TestTPMLimiter:
    """TPM 限流器测试"""

    def test_acquire_within_limit(self):
        """测试在限额内可以通过"""
        limiter = TPMLimiter()
        limiter.set_limit("test-model", 1000)
        assert limiter.acquire("test-model", 100) is True

    def test_acquire_exceed_limit(self):
        """测试超限被拒绝"""
        limiter = TPMLimiter()
        limiter.set_limit("test-model", 100)
        limiter.acquire("test-model", 90)  # 先消耗 90
        assert limiter.acquire("test-model", 20) is False  # 再消耗 20，超限

    def test_unconfigured_model_passes(self):
        """测试未配置限流的模型默认放行"""
        limiter = TPMLimiter()
        assert limiter.acquire("unknown-model", 10000) is True

    def test_get_usage(self):
        """测试获取当前用量"""
        limiter = TPMLimiter()
        limiter.set_limit("test-model", 1000)
        limiter.acquire("test-model", 300)
        usage = limiter.get_usage("test-model")
        assert usage >= 300

    def test_get_limit(self):
        """测试获取限流配置"""
        limiter = TPMLimiter()
        limiter.set_limit("test-model", 5000)
        assert limiter.get_limit("test-model") == 5000
        assert limiter.get_limit("unknown") is None