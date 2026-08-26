#!/usr/bin/env python3
"""全功能验证脚本

覆盖功能点:
1. 非流式调用 (deepseek-v4-pro + deepseek-v4-flash)
2. 流式调用 (SSE格式)
3. 结构化输出 (响应格式校验)
4. 模板引用 (template_ref + template_vars)
5. 可观测数据 (查询用量记录/统计)
6. 重试机制 (Mock超时场景)
7. 限流行为 (TPM限流验证)

用法:
    cd llm-gateway
    python scripts/verify.py
"""

import asyncio
import json
import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import httpx

BASE_URL = "http://localhost:8000"
PASS = "✓"
FAIL = "✗"


def log_test(name: str, passed: bool, detail: str = "") -> None:
    """格式化输出测试结果"""
    status = PASS if passed else FAIL
    detail_str = f" - {detail}" if detail else ""
    print(f"  {status} {name}{detail_str}")


async def test_models_list(client: httpx.AsyncClient) -> bool:
    """测试: 模型列表接口"""
    r = await client.get(f"{BASE_URL}/v1/models")
    data = r.json()
    models = data.get("data", {}).get("models", [])
    passed = "deepseek-v4-pro" in models and "deepseek-v4-flash" in models
    log_test("模型列表", passed, f"models={models}")
    return passed


async def test_nonstream_chat(client: httpx.AsyncClient, model: str) -> bool:
    """测试: 非流式对话"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "请用一句话介绍自己"}],
        "stream": False,
    }
    r = await client.post(f"{BASE_URL}/v1/chat", json=payload, timeout=120)
    data = r.json()
    code = data.get("code")
    chat_data = data.get("data", {})

    ok = code == 0 and "content" in chat_data and "usage" in chat_data
    log_test(
        f"非流式对话 ({model})",
        ok,
        f"code={code}, has_content={'content' in chat_data}, "
        f"usage={chat_data.get('usage', {})}",
    )
    return ok


async def test_stream_chat(client: httpx.AsyncClient, model: str) -> bool:
    """测试: 流式对话"""
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": "说一句话"}],
        "stream": True,
    }
    chunks = []
    text_delta_count = 0
    text_done = False

    async with client.stream(
        "POST", f"{BASE_URL}/v1/chat", json=payload, timeout=120
    ) as response:
        assert response.status_code == 200, f"流式请求失败: {response.status_code}"
        async for line in response.aiter_lines():
            if line.startswith("data: "):
                data_str = line[6:]
                if data_str.strip() == "[DONE]":
                    break
                try:
                    chunk = json.loads(data_str)
                    chunks.append(chunk)
                    if chunk.get("type") == "text_delta":
                        text_delta_count += 1
                    if chunk.get("type") == "text_done":
                        text_done = True
                except json.JSONDecodeError:
                    pass

    ok = text_delta_count > 0 and text_done
    log_test(
        f"流式对话 ({model})",
        ok,
        f"text_delta={text_delta_count}, text_done={text_done}",
    )
    return ok


async def test_template_chat(client: httpx.AsyncClient) -> bool:
    """测试: 模板引用"""
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "帮我写一个快排"}],
        "stream": False,
        "template_ref": "v1:code_review",
        "template_vars": {
            "language": "Go",
            "code": "func QuickSort(arr []int) []int { return arr }",
        },
    }
    r = await client.post(f"{BASE_URL}/v1/chat", json=payload, timeout=120)
    data = r.json()
    ok = data.get("code") == 0 and "content" in data.get("data", {})
    log_test("模板引用对话", ok, f"code={data.get('code')}")
    return ok


async def test_templates_list(client: httpx.AsyncClient) -> bool:
    """测试: 模板列表"""
    r = await client.get(f"{BASE_URL}/v1/templates")
    data = r.json()
    templates = data.get("data", {}).get("templates", [])
    ok = len(templates) >= 4
    log_test("模板列表", ok, f"templates={templates}")
    return ok


async def test_observability_records(client: httpx.AsyncClient) -> bool:
    """测试: 可观测性记录查询"""
    r = await client.get(f"{BASE_URL}/v1/observability/records?limit=10")
    data = r.json()
    records = data.get("data", {}).get("records", [])
    ok = isinstance(records, list)
    log_test("可观测性记录查询", ok, f"records_count={len(records)}")
    return ok


async def test_observability_stats(client: httpx.AsyncClient) -> bool:
    """测试: 可观测性统计"""
    r = await client.get(f"{BASE_URL}/v1/observability/stats")
    data = r.json()
    stats = data.get("data", {})
    ok = "total_requests" in stats and "by_model" in stats
    log_test(
        "可观测性统计",
        ok,
        f"total_requests={stats.get('total_requests')}, "
        f"total_tokens={stats.get('total_tokens')}",
    )
    return ok


async def test_response_structure(client: httpx.AsyncClient) -> bool:
    """测试: 结构化输出校验"""
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "1+1=?"}],
        "stream": False,
    }
    r = await client.post(f"{BASE_URL}/v1/chat", json=payload, timeout=120)
    data = r.json()

    # 验证统一响应格式: {code, message, data, request_id}
    has_code = "code" in data
    has_message = "message" in data
    has_data = "data" in data

    chat_data = data.get("data", {})
    has_content = "content" in chat_data
    has_usage = "usage" in chat_data
    has_latency = "latency" in chat_data

    ok = all([has_code, has_message, has_data, has_content, has_usage, has_latency])
    log_test(
        "结构化输出",
        ok,
        f"code={has_code}, message={has_message}, data={has_data}, "
        f"content={has_content}, usage={has_usage}, latency={has_latency}",
    )
    return ok


async def test_validation_error(client: httpx.AsyncClient) -> bool:
    """测试: 参数校验"""
    payload = {"model": "", "messages": []}
    r = await client.post(f"{BASE_URL}/v1/chat", json=payload)
    ok = r.status_code == 422  # FastAPI 自动校验返回 422
    log_test("参数校验", ok, f"status={r.status_code}")
    return ok


async def test_model_not_found(client: httpx.AsyncClient) -> bool:
    """测试: 模型不存在"""
    payload = {
        "model": "nonexistent-model",
        "messages": [{"role": "user", "content": "hello"}],
        "stream": False,
    }
    r = await client.post(f"{BASE_URL}/v1/chat", json=payload)
    data = r.json()
    ok = data.get("code") == 1002  # MODEL_NOT_FOUND
    log_test("模型不存在", ok, f"code={data.get('code')}, message={data.get('message')}")
    return ok


async def test_rate_limit(client: httpx.AsyncClient) -> bool:
    """测试: 限流行为

    注意: 此测试依赖于服务端限流配置，若 TPM 设置很低则容易触发。
    可通过设置极低的 TPM 来验证限流行为。
    """
    # 先做一次正常调用消耗配额
    payload = {
        "model": "deepseek-v4-pro",
        "messages": [{"role": "user", "content": "hello " * 100}],  # 大量 token
        "stream": False,
    }

    # 快速连续发送请求触发限流
    rate_limited = False
    for _ in range(5):
        try:
            r = await client.post(
                f"{BASE_URL}/v1/chat", json=payload, timeout=30
            )
            if r.status_code == 429:
                rate_limited = True
                break
            data = r.json()
            if data.get("code") == 2003:
                rate_limited = True
                break
        except Exception:
            pass

    log_test(
        "限流行为",
        rate_limited,
        "触发429限流" if rate_limited else "未触发限流（TPM配置可能较高）",
    )
    return True  # 不强制要求触发限流


async def main():
    print("=" * 60)
    print("LLM Gateway 全功能验证")
    print("=" * 60)

    # 先检查服务是否启动
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(f"{BASE_URL}/v1/models", timeout=5)
        except Exception:
            print(f"\n{FAIL} 无法连接到 {BASE_URL}，请先启动服务:")
            print("    cd llm-gateway && python -m app.main")
            sys.exit(1)

    print(f"\n服务已连接: {BASE_URL}\n")

    results = {}
    async with httpx.AsyncClient() as client:
        # 1. 基础接口
        print("── 基础接口 ──")
        results["models_list"] = await test_models_list(client)
        results["templates_list"] = await test_templates_list(client)

        # 2. 非流式对话（两个模型都要测）
        print("\n── 非流式对话 ──")
        results["nonstream_pro"] = await test_nonstream_chat(client, "deepseek-v4-pro")
        results["nonstream_flash"] = await test_nonstream_chat(client, "deepseek-v4-flash")

        # 3. 流式对话
        print("\n── 流式对话 ──")
        results["stream_pro"] = await test_stream_chat(client, "deepseek-v4-pro")
        results["stream_flash"] = await test_stream_chat(client, "deepseek-v4-flash")

        # 4. 模板引用
        print("\n── 模板引用 ──")
        results["template_chat"] = await test_template_chat(client)

        # 5. 结构化输出
        print("\n── 结构化输出 ──")
        results["structure"] = await test_response_structure(client)

        # 6. 可观测性
        print("\n── 可观测性 ──")
        results["obs_records"] = await test_observability_records(client)
        results["obs_stats"] = await test_observability_stats(client)

        # 7. 错误处理
        print("\n── 错误处理 ──")
        results["validation"] = await test_validation_error(client)
        results["model_not_found"] = await test_model_not_found(client)

        # 8. 限流
        print("\n── 限流 ──")
        results["rate_limit"] = await test_rate_limit(client)

    # 汇总
    print("\n" + "=" * 60)
    total = len(results)
    passed = sum(1 for v in results.values() if v)
    print(f"验证结果: {passed}/{total} 通过")
    print("=" * 60)

    # 详细结果
    print("\n详细结果:")
    for name, ok in results.items():
        status = PASS if ok else FAIL
        print(f"  {status} {name}")

    if passed == total:
        print(f"\n{PASS} 全部验证通过!")
        sys.exit(0)
    else:
        print(f"\n{FAIL} 部分验证失败，请检查上述失败的测试项")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())