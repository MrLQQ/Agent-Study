"""pytest 配置与 Fixtures"""

import pytest
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))


@pytest.fixture
def sample_chat_request_nonstream():
    """非流式对话请求示例"""
    return {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "user", "content": "你好，请用一句话介绍自己"}
        ],
        "stream": False,
    }


@pytest.fixture
def sample_chat_request_stream():
    """流式对话请求示例"""
    return {
        "model": "deepseek-v4-flash",
        "messages": [
            {"role": "user", "content": "请用一句话介绍自己"}
        ],
        "stream": True,
        "parameters": {"temperature": 0.7},
    }


@pytest.fixture
def sample_chat_request_template():
    """模板引用请求示例"""
    return {
        "model": "deepseek-v4-pro",
        "messages": [
            {"role": "user", "content": "帮我写一个快排"}
        ],
        "stream": False,
        "template_ref": "v1:code_review",
        "template_vars": {
            "language": "Go",
            "code": "func QuickSort(arr []int) []int { ... }",
        },
    }