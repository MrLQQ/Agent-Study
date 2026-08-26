#!/bin/bash
# LLM Gateway 启动脚本

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

cd "$PROJECT_DIR"

# 检查虚拟环境
if [ ! -d ".venv" ]; then
    echo "创建虚拟环境..."
    python3 -m venv .venv
fi

# 激活虚拟环境
source .venv/bin/activate

# 安装依赖
echo "安装依赖..."
pip install -e ".[dev]" -q

# 检查 .env 文件
if [ ! -f ".env" ]; then
    echo "警告: .env 文件不存在，请从 .env.example 复制并填入 API Key"
    echo "    cp .env.example .env"
    exit 1
fi

# 启动服务
echo "启动 LLM Gateway..."
python -m app.main