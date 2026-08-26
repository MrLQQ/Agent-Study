"""用量统计对象"""

from pydantic import BaseModel, Field


class Usage(BaseModel):
    """Token用量统计"""
    prompt_tokens: int = Field(default=0, description="输入Token数")
    completion_tokens: int = Field(default=0, description="输出Token数")
    total_tokens: int = Field(default=0, description="总Token数")