#!/usr/bin/env python3
"""环境变量自检脚本"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from dotenv import load_dotenv

load_dotenv()

required_vars = [
    "DEEPSEEK_V4_PRO_API_KEY",
    "DEEPSEEK_V4_FLASH_API_KEY",
]

all_ok = True
for var in required_vars:
    val = os.getenv(var, "")
    if val and val != f"your_{var.lower()}_here":
        print(f"  [OK] {var} = {val[:8]}...")
    else:
        print(f"  [MISSING] {var} 未设置或使用了默认值")
        all_ok = False

if all_ok:
    print("\n所有环境变量配置正确!")
else:
    print("\n请编辑 .env 文件填入正确的 API Key")
    sys.exit(1)