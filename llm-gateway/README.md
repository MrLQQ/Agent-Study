# LLM Gateway

统一 LLM Gateway 服务，通过适配器模式封装不同模型 API 协议差异，提供流式/非流式对话、提示词模板管理、可观测性、限流与重试等能力。

## 功能特性

| 功能 | 说明 |
|------|------|
| **多协议适配** | 通过适配器模式屏蔽 OpenAI Responses API 与 Chat Completions API 的协议差异 |
| **流式/非流式** | `stream=true` 开启 SSE 流式响应，`stream=false` 返回标准 JSON |
| **提示词模板** | Jinja2 模板引擎，支持版本化存储（v1/v2）和变量替换 |
| **模板即调用** | 模板接口可直接指定模型并调用，无需构造完整 ChatRequest |
| **可观测性** | 记录每次调用的 Token 消耗（含分类统计）和延迟（含首字延迟 TTFT） |
| **指数退避重试** | 最多 3 次重试，延迟 1s → 2s → 4s，可配置重试条件和上限 |
| **TPM 限流** | 按模型维度独立限流，滑动窗口算法，超限返回 429 |
| **统一错误码** | 标准化错误码分类：客户端错误(1xxx) / 限流(2xxx) / 服务端(3xxx) / 重试耗尽(4xxx) |
| **请求追踪** | 每个请求自动生成/透传 `X-Request-ID`，全链路可追踪 |

## 快速开始

### 1. 环境准备

```bash
# 克隆项目
cd llm-gateway

# 创建虚拟环境（需要 Python 3.11+）
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
# DeepSeek API Keys
DEEPSEEK_V4_PRO_API_KEY=sk-your-deepseek-v4-pro-key
DEEPSEEK_V4_FLASH_API_KEY=sk-your-deepseek-v4-flash-key

# 日志级别（DEBUG / INFO / WARNING / ERROR）
LOG_LEVEL=INFO
```

### 3. 启动服务

```bash
python -m app.main
```

服务启动后访问 `http://localhost:8000/docs` 查看 Swagger API 文档。

> 提示：`config.yaml` 修改后 Uvicorn 的 `reload` 机制会自动重启服务，无需手动操作。

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
│ POST /v1/        │    │ POST /v1/chat/       │                 │
│   responses      │    │   completions        │                 │
│                  │    │                      │                 │
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

**请求参数（ChatRequest）**：

| 字段 | 类型 | 必填 | 说明 |
|------|------|------|------|
| `model` | string | 是 | 模型标识，如 `deepseek-v4-pro` |
| `messages` | array | 是 | 对话消息列表，每条含 `role`（system/user/assistant/tool）和 `content` |
| `stream` | bool | 否 | 是否流式，默认 `false` |
| `system_prompt` | string | 否 | 系统提示词（与 `template_ref` 互斥） |
| `template_ref` | string | 否 | 模板引用，格式 `版本:名称`，如 `v1:chat_default` |
| `template_vars` | object | 否 | 模板变量键值对 |
| `parameters` | object | 否 | 模型参数，如 `temperature`、`max_tokens` |
| `context` | object | 否 | 会话上下文，如 `conversation_id`、`user_id`、`trace_id` |

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

**错误响应**：

```json
{
  "code": 1002,
  "message": "模型不存在",
  "data": null,
  "request_id": "a1b2c3d4e5f6g7h8"
}
```

### 模型列表

**GET** `/v1/models`

```bash
curl http://localhost:8000/v1/models
```

### 模板管理

#### 列出模板

**GET** `/v1/templates`

```bash
curl http://localhost:8000/v1/templates
```

响应示例：

```json
{
  "code": 0,
  "message": "success",
  "data": {
    "templates": ["v1:chat_default", "v1:code_review", "v2:chat_default", "v2:code_review"]
  },
  "request_id": "a1b2c3d4e5f6g7h8"
}
```

#### 渲染模板

**POST** `/v1/templates/render`

```bash
# 仅渲染模板（不调用模型）
curl -X POST "http://localhost:8000/v1/templates/render?template_ref=v1:chat_default" \
  -H "Content-Type: application/json" \
  -d '{"role": "助手", "language": "中文", "user_input": "解释闭包"}'

# 渲染模板 + 调用模型（非流式）
curl -X POST "http://localhost:8000/v1/templates/render?template_ref=v1:chat_default&model=deepseek-v4-pro" \
  -H "Content-Type: application/json" \
  -d '{"role": "助手", "language": "中文", "user_input": "解释闭包"}'

# 渲染模板 + 调用模型（流式）
curl -X POST "http://localhost:8000/v1/templates/render?template_ref=v1:chat_default&model=deepseek-v4-pro&stream=true" \
  -H "Content-Type: application/json" \
  -d '{"role": "助手", "language": "中文", "user_input": "解释闭包"}'
```

**请求参数**：

| 参数 | 位置 | 类型 | 必填 | 说明 |
|------|------|------|------|------|
| `template_ref` | Query | string | 是 | 模板引用，如 `v1:chat_default` |
| `variables` | Body | object | 是 | 模板变量键值对 |
| `model` | Query | string | 否 | 指定模型名称则直接调用模型，不传则仅渲染模板 |
| `stream` | Query | bool | 否 | 是否流式返回，仅 `model` 不为空时生效，默认 `false` |

**响应说明**：

- 不传 `model`：返回 `{"rendered": "渲染后的模板文本"}`
- 传入 `model` + `stream=false`：返回与 `/v1/chat` 一致的 `ChatResponse`
- 传入 `model` + `stream=true`：返回 SSE 流式响应

#### 内置模板

| 模板引用 | 文件 | 变量 | 说明 |
|----------|------|------|------|
| `v1:chat_default` | `prompts/v1/chat_default.j2` | `role`, `language`, `context`, `user_input` | 基础对话模板 |
| `v1:code_review` | `prompts/v1/code_review.j2` | `language`, `code` | 基础代码审查（逻辑/性能/命名/错误处理） |
| `v2:chat_default` | `prompts/v2/chat_default.j2` | `role`, `skills`, `language`, `output_format`, `user_input` | 增强对话（角色扮演、技能列表、输出格式控制） |
| `v2:code_review` | `prompts/v2/code_review.j2` | `language`, `code` | 增强代码审查（增加安全审查、评分机制） |

模板文件使用 Jinja2 语法，存放在 `prompts/` 目录下，按版本（v1/v2）组织。你可以通过添加 `.j2` 文件来自定义模板，`GET /v1/templates` 会自动发现新模板。

### 可观测性

**GET** `/v1/observability/records?model=deepseek-v4-pro&limit=10`

```bash
curl "http://localhost:8000/v1/observability/records?limit=10"
```

**GET** `/v1/observability/stats`

```bash
curl "http://localhost:8000/v1/observability/stats"
```

## 配置说明

### config.yaml

```yaml
# ── 模型配置 ──
models:
  - name: "deepseek-v4-pro"          # 模型名称
    provider: "openai_responses"     # 适配器类型: openai_responses / anthropic_messages
    api_base: "https://api.deepseek.com"
    api_key_env: "DEEPSEEK_V4_PRO_API_KEY"  # 从 .env 读取的 Key 名
  - name: "deepseek-v4-flash"
    provider: "anthropic_messages"
    api_base: "https://api.deepseek.com"
    api_key_env: "DEEPSEEK_V4_FLASH_API_KEY"

# ── 限流配置（TPM: 每分钟Token处理量）──
rate_limits:
  - model: "deepseek-v4-pro"
    tpm: 60000
  - model: "deepseek-v4-flash"
    tpm: 120000

# ── 重试配置（指数退避）──
retry:
  max_attempts: 3                    # 最大重试次数（含首次）
  backoff_base_seconds: 1.0          # 初始等待时间
  backoff_multiplier: 2.0            # 每次乘 2（1s → 2s → 4s）
  max_backoff_seconds: 10.0          # 单次等待上限
  retryable_statuses: [429, 500, 502, 503, 504]  # 重试的 HTTP 状态码

# ── 超时配置 ──
timeout:
  request_seconds: 120.0             # 请求总超时
  connect_seconds: 10.0              # 连接超时

# ── 模板配置 ──
templates:
  base_dir: "prompts"                # 模板文件目录
  default_version: "v1"              # 默认版本

# ── 服务配置 ──
server:
  host: "0.0.0.0"
  port: 8000
```

### .env

```ini
# API Keys（按模型配置的 api_key_env 字段对应）
DEEPSEEK_V4_PRO_API_KEY=sk-your-key
DEEPSEEK_V4_FLASH_API_KEY=sk-your-key

# 日志级别（DEBUG / INFO / WARNING / ERROR）
LOG_LEVEL=INFO
```

## 错误码

| 错误码 | 分类 | 说明 | HTTP 状态码 |
|--------|------|------|-------------|
| 0 | 成功 | 请求成功 | 200 |
| 1001 | 客户端错误 | 参数校验失败 | 400 |
| 1002 | 客户端错误 | 模型不存在 | 404 |
| 1003 | 客户端错误 | 模板不存在 | 404 |
| 1004 | 客户端错误 | 模板渲染失败 | 400 |
| 2001 | 限流错误 | 触发限流 | 429 |
| 3001 | 服务端错误 | 内部错误 | 500 |
| 3002 | 服务端错误 | 供应商错误 | 502 |
| 3003 | 服务端错误 | 模型超时 | 504 |
| 4001 | 重试耗尽 | 重试耗尽 | 500 |

## 目录结构

```
llm-gateway/
├── app/
│   ├── main.py                  # 应用入口，FastAPI 创建与中间件注册
│   ├── adapters/                # 模型适配器层
│   │   ├── base.py              # 适配器基类（重试/超时/HTTP客户端）
│   │   ├── protocol.py          # 统一协议（UnifiedRequest/UnifiedResponse）
│   │   ├── registry.py          # 注册表（model → adapter 映射）
│   │   └── providers/           # 厂商适配器实现
│   │       ├── openai_responses.py    # OpenAI Responses API
│   │       └── anthropic_messages.py  # Chat Completions API
│   ├── api/
│   │   ├── deps.py              # 依赖注入（懒加载单例）
│   │   ├── router.py            # 路由聚合（/v1 前缀）
│   │   └── v1/
│   │       ├── chat.py          # POST /v1/chat
│   │       ├── prompt.py        # 模板管理 API
│   │       └── observability.py # 可观测性 API
│   ├── core/                    # 核心层
│   │   ├── config.py            # 配置加载（config.yaml + .env）
│   │   ├── constants.py         # 枚举常量（Role / StreamEventType）
│   │   ├── errors.py            # 错误码体系
│   │   ├── exceptions.py        # 自定义异常类
│   │   └── logging.py           # 日志配置
│   ├── infrastructure/          # 基础设施层
│   │   ├── rate_limiter/
│   │   │   └── engine.py        # TPM 滑动窗口限流
│   │   ├── store/
│   │   │   ├── base.py          # 存储抽象接口
│   │   │   └── memory.py        # 内存存储实现
│   │   └── template_loader.py   # Jinja2 模板加载器
│   ├── middleware/               # 中间件层
│   │   ├── error_handler.py     # 全局异常处理
│   │   ├── rate_limiter.py      # 限流中间件
│   │   └── request_id.py        # 请求ID注入
│   ├── schemas/                 # 数据模型层
│   │   ├── model/               # 领域模型（Message / Usage / Latency）
│   │   ├── request/             # 请求体（ChatRequest）
│   │   └── response/            # 响应体（BaseResponse / ChatResponse / StreamChunk）
│   ├── services/                # 服务层
│   │   ├── interfaces/          # 服务接口定义
│   │   └── impl/                # 服务实现
│   └── utils/                   # 工具层
│       ├── clock.py             # 高精度计时器
│       ├── id_gen.py            # ID 生成器
│       ├── sse.py               # SSE 格式化
│       └── validators.py        # 参数校验
├── prompts/                     # 提示词模板
│   ├── v1/                      # 版本 v1
│   │   ├── chat_default.j2      # 基础对话模板
│   │   └── code_review.j2       # 基础代码审查模板
│   └── v2/                      # 版本 v2（增强版）
│       ├── chat_default.j2      # 增强对话模板
│       └── code_review.j2       # 增强代码审查模板
├── config.yaml                  # 运行时配置
├── .env.example                 # 环境变量示例
├── pyproject.toml               # 项目依赖与构建配置
├── tests/                       # 测试
│   ├── unit/                    # 单元测试
│   └── integration/             # 集成测试
└── scripts/                     # 脚本工具
    ├── start.sh                 # 启动脚本
    └── verify.py                # 全功能验证
```

## 扩展指南

### 添加新模型适配器

1. 在 `app/adapters/providers/` 下新建适配器文件，继承 `BaseAdapter`：

```python
from app.adapters.base import BaseAdapter
from app.adapters.protocol import UnifiedRequest, UnifiedResponse

class MyNewAdapter(BaseAdapter):
    async def _do_call(self, request: UnifiedRequest) -> UnifiedResponse:
        # 实现非流式调用逻辑
        ...

    async def _do_stream(self, request: UnifiedRequest):
        # 实现流式调用逻辑
        ...
```

2. 在 `app/adapters/base.py` 的 `_build_adapter()` 中注册新适配器类型。

3. 在 `config.yaml` 的 `models` 中添加新模型配置，`provider` 字段指向新适配器。

### 添加自定义模板

在 `prompts/v1/` 或 `prompts/v2/` 目录下新建 `.j2` 文件即可，`GET /v1/templates` 会自动发现：

```jinja2
{# 自定义模板 #}
你是一个{{ role }}专家，请回答以下问题：

{{ user_input }}
```

### 运行测试

```bash
# 运行所有测试
pytest

# 运行指定测试文件
pytest tests/unit/test_template_loader.py -v

# 带覆盖率报告
pytest --cov=app --cov-report=term-missing
```

## 技术栈

- **框架**: FastAPI + Uvicorn
- **校验**: Pydantic v2
- **HTTP 客户端**: httpx（异步 + 连接池）
- **模板引擎**: Jinja2
- **配置管理**: PyYAML + python-dotenv
- **流式传输**: SSE (Server-Sent Events)
- **Python**: 3.11+