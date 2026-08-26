# LLM Gateway

统一 LLM Gateway 服务，通过适配器模式封装不同模型 API 协议差异，提供流式/非流式对话、提示词模板管理、可观测性、限流与重试等能力。

## 功能特性

| 功能 | 说明 |
|------|------|
| **多协议适配** | 通过适配器模式屏蔽 OpenAI Responses API 与 Anthropic Messages API 的协议差异 |
| **流式/非流式** | `stream=true` 开启 SSE 流式响应，`stream=false` 返回标准 JSON |
| **提示词模板** | Jinja2 模板引擎，支持版本化存储（v1/v2）和变量替换 |
| **可观测性** | 记录每次调用的 Token 消耗（含分类统计）和延迟（含首字延迟 TTFT） |
| **指数退避重试** | 最多 3 次重试，延迟 1s→2s→4s |
| **TPM 限流** | 按模型维度独立限流，通过 `config.yaml` 管理，超限返回 429 |
| **统一错误码** | 标准化错误码分类：客户端错误(1xxx) / 限流(2xxx) / 服务端(3xxx) / 重试耗尽(4xxx) |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd llm-gateway

# 创建虚拟环境
python3 -m venv .venv
source .venv/bin/activate

# 安装依赖
pip install -e ".[dev]"
```

### 2. 配置 API Key

```bash
cp .env.example .env
# 编辑 .env 填入真实的 API Key
```

`.env` 内容：

```ini
DEEPSEEK_V4_PRO_API_KEY=sk-your-deepseek-v4-pro-key
DEEPSEEK_V4_FLASH_API_KEY=sk-your-deepseek-v4-flash-key
```

### 3. 启动服务

```bash
python -m app.main
```

服务启动后访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

### 4. 验证

```bash
python scripts/verify.py
```

## 架构设计

```
                  ┌──────────────────────────────────────┐
                  │            FastAPI 入口               │
                  │  middleware: request_id / rate_limit  │
                  │  error_handler（全局异常捕获）         │
                  └──────────────────┬───────────────────┘
                                     │
                  ┌──────────────────┴───────────────────┐
                  │         POST /v1/chat                │
                  │   stream=true → SSE 流式              │
                  │   stream=false → JSON 响应            │
                  └──────────────────┬───────────────────┘
                                     │
                  ┌──────────────────┴───────────────────┐
                  │     ChatService（业务编排）             │
                  │  1. 校验参数                           │
                  │  2. 加载模板（Jinja2）                  │
                  │  3. 构建 UnifiedRequest               │
                  │  4. 路由 adapter                       │
                  │  5. 记录可观测数据                      │
                  └──────────────────┬───────────────────┘
                                     │
        ┌────────────────────────────┼────────────────────────────┐
        │                            │                            │
        ▼                            ▼                            │
┌──────────────────┐    ┌──────────────────────┐                 │
│ OpenAIResponses  │    │ AnthropicMessages    │                 │
│ Adapter          │    │ Adapter              │                 │
│                  │    │                      │                 │
│ POST /v1/        │    │ POST /v1/messages    │                 │
│   responses      │    │                      │                 │
│                  │    │ system → 顶层字段      │                 │
│ instructions →   │    │ messages → 数组       │                 │
│   系统提示词      │    │                      │                 │
│ input → 用户输入  │    │                      │                 │
│                  │    │                      │                 │
│ 适用:            │    │ 适用:                │                 │
│ deepseek-v4-pro  │    │ deepseek-v4-flash    │                 │
└──────────────────┘    └──────────────────────┘                 │
```

## API 接口

### 对话（统一入口）

**POST** `/v1/chat`

```bash
# 非流式对话
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": "你好，请介绍自己"}],
    "stream": false
  }'

# 流式对话
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-flash",
    "messages": [{"role": "user", "content": "介绍一下人工智能"}],
    "stream": true
  }'

# 使用模板引用
curl -X POST http://localhost:8000/v1/chat \
  -H "Content-Type: application/json" \
  -d '{
    "model": "deepseek-v4-pro",
    "messages": [{"role": "user", "content": "帮我写一个快排"}],
    "stream": false,
    "template_ref": "v1:code_review",
    "template_vars": {
      "language": "Go",
      "code": "func QuickSort(arr []int) []int { return arr }"
    }
  }'
```

**请求参数**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型标识，如 `deepseek-v4-pro` |
| `messages` | array | 是 | 对话消息列表 |
| `stream` | bool | 否 | 是否流式，默认 `false` |
| `system_prompt` | string | 否 | 系统提示词（与 template_ref 互斥） |
| `template_ref` | string | 否 | 模板引用，格式 `版本:名称`，如 `v1:chat_default` |
| `template_vars` | object | 否 | 模板变量键值对 |
| `parameters` | object | 否 | 模型参数，如 `temperature`、`max_tokens` |

**非流式响应**：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "content": "你好！我是DeepSeek...",
    "model": "deepseek-v4-pro",
    "usage": {
      "prompt_tokens": 15,
      "completion_tokens": 42,
      "total_tokens": 57
    },
    "latency": {
      "ttft_ms": 0,
      "total_ms": 1234.56
    }
  },
  "request_id": "a1b2c3d4e5f6g7h8"
}
```

**流式响应（SSE）**：

```
data: {"type":"text_delta","content":"你好"}
data: {"type":"text_delta","content":"！我是"}
data: {"type":"text_done","usage":{"prompt_tokens":15,"completion_tokens":42,"total_tokens":57},"latency":{"ttft_ms":234.5,"total_ms":1234.5}}
data: [DONE]
```

### 模板管理

**GET** `/v1/templates` — 列出所有可用模板

```bash
curl http://localhost:8000/v1/templates
```

**POST** `/v1/templates/render` — 渲染模板

```bash
curl -X POST http://localhost:8000/v1/templates/render?template_ref=v1:chat_default \
  -H "Content-Type: application/json" \
  -d '{"role": "助手", "language": "中文", "user_input": "解释闭包"}'
```

### 可观测性

**GET** `/v1/observability/records?model=deepseek-v4-pro&limit=10`

```bash
curl "http://localhost:8000/v1/observability/records?limit=10"
```

**GET** `/v1/observability/stats`

```bash
curl "http://localhost:8000/v1/observability/stats"
```

### 模型列表

**GET** `/v1/models`

```bash
curl http://localhost:8000/v1/models
```

## 配置说明

### config.yaml

```yaml
# 模型配置
models:
  - name: "deepseek-v4-pro"
    provider: "openai_responses"       # 适配器类型
    api_base: "https://api.deepseek.com/v1"
    api_key_env: "DEEPSEEK_V4_PRO_API_KEY"

# 限流配置（TPM: 每分钟Token）
rate_limits:
  - model: "deepseek-v4-pro"
    tpm: 60000
  - model: "deepseek-v4-flash"
    tpm: 120000

# 重试配置
retry:
  max_attempts: 3
  backoff_base_seconds: 1.0
  backoff_multiplier: 2.0
```

## 目录结构

```
llm-gateway/
├── app/
│   ├── main.py                  # 应用入口
│   ├── api/v1/                  # API路由层
│   ├── core/                    # 核心层（配置/错误码/异常）
│   ├── middleware/               # 中间件层
│   ├── schemas/                 # 协议定义层
│   ├── adapters/                # 模型适配器层
│   │   ├── protocol.py          # 统一协议
│   │   ├── providers/           # 厂商适配器实现
│   │   │   ├── openai_responses.py
│   │   │   └── anthropic_messages.py
│   ├── services/                # 应用服务层
│   ├── infrastructure/          # 基础设施层
│   │   ├── rate_limiter/        # TPM限流
│   │   ├── template_loader.py   # Jinja2模板加载
│   │   └── store/               # 存储
│   └── utils/                   # 工具层
├── prompts/                     # 提示词模板
│   ├── v1/                      # 版本 v1
│   └── v2/                      # 版本 v2
├── config.yaml                  # 运行时配置
├── tests/                       # 测试
└── scripts/                     # 脚本
    ├── start.sh                 # 启动脚本
    └── verify.py                # 全功能验证
```

## 错误码

| 错误码 | 说明 |
|--------|------|
| 0 | 成功 |
| 1001 | 参数校验失败 |
| 1002 | 模型不存在 |
| 1003 | 模板不存在 |
| 2001 | 触发限流 |
| 3001 | 内部错误 |
| 3002 | 供应商错误 |
| 3003 | 模型超时 |
| 4001 | 重试耗尽 |

## 技术栈

- **框架**: FastAPI + Uvicorn
- **校验**: Pydantic v2
- **HTTP客户端**: httpx（异步 + 连接池）
- **模板引擎**: Jinja2
- **配置管理**: PyYAML + python-dotenv
- **流式传输**: SSE (Server-Sent Events)