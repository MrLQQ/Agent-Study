"""适配器协议转换测试"""

import pytest

from app.adapters.protocol import UnifiedRequest
from app.schemas.model.message import Message
from app.core.constants import Role


class TestOpenAIResponsesAdapter:
    """OpenAI Responses 适配器测试"""

    def test_build_request_payload_basic(self):
        """测试基本请求构建"""
        from app.adapters.providers.openai_responses import OpenAIResponsesAdapter
        from unittest.mock import MagicMock

        # 使用 mock model_config
        adapter = OpenAIResponsesAdapter.__new__(OpenAIResponsesAdapter)
        adapter.model_config = MagicMock()
        adapter.model_config.api_base = "https://test.com"
        adapter.model_config.api_key_env = "TEST_KEY"
        adapter.api_key = "test_key"
        adapter._client = None

        req = UnifiedRequest(
            model="deepseek-v4-pro",
            messages=[
                Message(role=Role.USER, content="你好"),
            ],
            system_prompt="你是一个助手",
            stream=False,
            parameters={"temperature": 0.7},
        )

        payload = adapter.build_request_payload(req)
        assert payload["model"] == "deepseek-v4-pro"
        assert payload["stream"] is False
        assert payload["instructions"] == "你是一个助手"
        assert "temperature" in payload

    def test_extract_usage(self):
        """测试用量提取"""
        from app.adapters.providers.openai_responses import OpenAIResponsesAdapter
        from unittest.mock import MagicMock

        adapter = OpenAIResponsesAdapter.__new__(OpenAIResponsesAdapter)
        adapter.model_config = MagicMock()
        adapter.model_config.api_base = "https://test.com"
        adapter.model_config.api_key_env = "TEST_KEY"
        adapter.api_key = "test_key"
        adapter._client = None

        raw = {
            "usage": {
                "input_tokens": 100,
                "output_tokens": 50,
                "total_tokens": 150,
            }
        }
        usage = adapter.extract_usage(raw)
        assert usage.prompt_tokens == 100
        assert usage.completion_tokens == 50
        assert usage.total_tokens == 150


class TestAnthropicMessagesAdapter:
    """Anthropic Messages 适配器测试"""

    def test_build_request_payload_basic(self):
        """测试基本请求构建"""
        from app.adapters.providers.anthropic_messages import (
            AnthropicMessagesAdapter,
        )
        from unittest.mock import MagicMock

        adapter = AnthropicMessagesAdapter.__new__(AnthropicMessagesAdapter)
        adapter.model_config = MagicMock()
        adapter.model_config.api_base = "https://test.com"
        adapter.model_config.api_key_env = "TEST_KEY"
        adapter.api_key = "test_key"
        adapter._client = None

        req = UnifiedRequest(
            model="deepseek-v4-flash",
            messages=[
                Message(role=Role.USER, content="你好"),
            ],
            system_prompt="你是一个助手",
            stream=False,
            parameters={"max_tokens": 2048},
        )

        payload = adapter.build_request_payload(req)
        assert payload["model"] == "deepseek-v4-flash"
        assert payload["stream"] is False
        assert payload["system"] == "你是一个助手"
        assert len(payload["messages"]) == 1

    def test_extract_usage(self):
        """测试用量提取"""
        from app.adapters.providers.anthropic_messages import (
            AnthropicMessagesAdapter,
        )
        from unittest.mock import MagicMock

        adapter = AnthropicMessagesAdapter.__new__(AnthropicMessagesAdapter)
        adapter.model_config = MagicMock()
        adapter.model_config.api_base = "https://test.com"
        adapter.model_config.api_key_env = "TEST_KEY"
        adapter.api_key = "test_key"
        adapter._client = None

        raw = {
            "usage": {
                "input_tokens": 200,
                "output_tokens": 80,
            }
        }
        usage = adapter.extract_usage(raw)
        assert usage.prompt_tokens == 200
        assert usage.completion_tokens == 80
        assert usage.total_tokens == 280