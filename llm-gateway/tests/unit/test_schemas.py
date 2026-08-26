"""Schema 校验测试"""

import pytest
from pydantic import ValidationError

from app.schemas.request.chat import ChatRequest
from app.schemas.model.message import Message
from app.core.constants import Role


class TestChatRequest:
    """对话请求Schema测试"""

    def test_valid_request(self, sample_chat_request_nonstream):
        """测试合法请求"""
        req = ChatRequest(**sample_chat_request_nonstream)
        assert req.model == "deepseek-v4-pro"
        assert req.stream is False
        assert len(req.messages) == 1

    def test_missing_model(self):
        """测试缺少必填字段 model"""
        with pytest.raises(ValidationError):
            ChatRequest(messages=[])

    def test_invalid_role(self):
        """测试非法消息角色"""
        with pytest.raises(ValidationError):
            Message(role="invalid_role", content="test")

    def test_valid_roles(self):
        """测试合法消息角色"""
        for role in Role:
            msg = Message(role=role, content="test")
            assert msg.role == role

    def test_stream_default_false(self):
        """测试 stream 默认值为 False"""
        req = ChatRequest(model="test-model", messages=[])
        assert req.stream is False

    def test_template_ref_format(self):
        """测试模板引用格式"""
        req = ChatRequest(
            model="test-model",
            messages=[],
            template_ref="v1:chat_default",
            template_vars={"role": "助手"},
        )
        assert req.template_ref == "v1:chat_default"
        assert req.template_vars == {"role": "助手"}