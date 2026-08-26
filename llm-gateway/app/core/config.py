"""配置管理 —— 加载 config.yaml + .env 环境变量"""

import os
from pathlib import Path
from typing import Any, Dict, List

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings

# 加载 .env 文件
load_dotenv()

# 项目根目录
PROJECT_ROOT = Path(__file__).parent.parent.parent


class ModelConfig(BaseModel):
    """单个模型配置"""
    name: str
    provider: str                # 适配器类型: openai_responses / anthropic_messages
    api_base: str
    api_key_env: str             # 环境变量名，从 .env 读取 API Key


class RateLimitConfig(BaseModel):
    """限流配置"""
    model: str
    tpm: int                     # 每分钟 Token 数


class RetryConfig(BaseModel):
    """重试配置"""
    max_attempts: int = 3
    backoff_base_seconds: float = 1.0
    backoff_multiplier: float = 2.0
    max_backoff_seconds: float = 10.0
    retryable_statuses: List[int] = [429, 500, 502, 503, 504]


class TimeoutConfig(BaseModel):
    """超时配置"""
    request_seconds: float = 120.0
    connect_seconds: float = 10.0


class TemplateConfig(BaseModel):
    """模板配置"""
    base_dir: str = "prompts"
    default_version: str = "v1"


class ServerConfig(BaseModel):
    """服务配置"""
    host: str = "0.0.0.0"
    port: int = 8000


class Settings(BaseSettings):
    """全局配置聚合"""
    models: List[ModelConfig] = []
    rate_limits: List[RateLimitConfig] = []
    retry: RetryConfig = RetryConfig()
    timeout: TimeoutConfig = TimeoutConfig()
    templates: TemplateConfig = TemplateConfig()
    server: ServerConfig = ServerConfig()

    # 环境变量（从 .env 读取）
    log_level: str = "INFO"

    model_config = ConfigDict(env_file=".env", env_file_encoding="utf-8")


def _load_yaml_config() -> Dict[str, Any]:
    """加载 config.yaml 并解析为字典"""
    config_path = PROJECT_ROOT / "config.yaml"
    if not config_path.exists():
        return {}
    with open(config_path, "r", encoding="utf-8") as f:
        return yaml.safe_load(f) or {}


def get_settings() -> Settings:
    """获取全局配置实例（单例）"""
    raw = _load_yaml_config()
    settings = Settings(**raw)
    return settings


def get_api_key(api_key_env: str) -> str:
    """从环境变量获取 API Key"""
    key = os.getenv(api_key_env, "")
    if not key:
        raise ValueError(f"环境变量 {api_key_env} 未设置，请检查 .env 文件")
    return key


# 全局配置单例
settings = get_settings()