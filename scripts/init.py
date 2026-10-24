#!/usr/bin/env python3
"""mcd-vibe-commit 初始化引导模块.

职责:
1. ``load_env()``: 把项目根目录 .env 中的 KEY=VALUE 载入进程环境变量
   (仅在本进程内生效, 全程不打印、不写日志);
2. 环境自检: Python 版本、必需文件是否齐全;
3. ``banner()``: 输出 ASCII 汉堡与当前 Token 配置状态(仅显示掩码).

可独立运行: python scripts/init.py
仅使用标准库, 兼容 Python 3.10+.
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

#: 项目根目录(scripts/ 的上一级)
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

#: .env 文件路径(已加入 .gitignore, 永不上传)
ENV_PATH: Path = PROJECT_ROOT / ".env"

#: 最低 Python 版本要求
MIN_PYTHON: tuple[int, int] = (3, 10)

#: 交付必需文件清单(与大赛报名要求对齐)
REQUIRED_FILES: tuple[str, ...] = (
    "SKILL.md",
    "README.md",
    "CONTEST_DECLARATION.md",
    "MCP_INTEGRATION.md",
    "mcp-config.example.json",
    "workbuddy.md",
    "scripts/init.py",
    "scripts/persona.py",
    "scripts/commit_gen.py",
    "scripts/mcp_client.py",
    "references/tools.md",
    "references/persona-matrix.md",
    "assets/ascii_burger.txt",
    ".env.example",
    ".gitignore",
)


def load_env(env_path: Path | str = ENV_PATH) -> bool:
    """把 .env 文件中的 KEY=VALUE 载入 os.environ(不覆盖已有变量).

    Args:
        env_path: .env 路径, 默认为项目根目录下的 .env.

    Returns:
        True 表示文件存在且已加载; 文件不存在或读取失败返回 False.

    安全说明:
        Token 值只进入进程内存环境变量, 不做任何打印, 不写入任何日志.
    """
    env_path = Path(env_path)
    if not env_path.is_file():
        return False
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value
        return True
    except OSError:
        return False


def check_python_version() -> bool:
    """检查当前 Python 版本是否满足 >= 3.10."""
    return sys.version_info >= MIN_PYTHON


def missing_files() -> list[str]:
    """返回缺失的必需文件列表(空列表表示齐全)."""
    return [rel for rel in REQUIRED_FILES if not (PROJECT_ROOT / rel).is_file()]


def token_status() -> str:
    """返回 Token 配置状态描述(只显示掩码, 绝不回显完整 Token)."""
    token = os.environ.get("MCP_TOKEN", "").strip()
    if not token:
        return "未配置(将使用内置 mock 菜单数据)"
    return f"已配置({token[:4]}****)"


def banner() -> str:
    """组装欢迎横幅: ASCII 汉堡 + 环境状态."""
    art_path = PROJECT_ROOT / "assets" / "ascii_burger.txt"
    try:
        art = art_path.read_text(encoding="utf-8").rstrip("\n")
    except OSError:
        art = "(assets/ascii_burger.txt 缺失)"
    missing = missing_files()
    layout = "文件齐全" if not missing else f"缺少: {', '.join(missing)}"
    return (
        f"{art}\n\n"
        f"mcd-vibe-commit | 麦门人格 Commit 生成器\n"
        f"Python: {check_python_version()} | {layout}\n"
        f"MCP_TOKEN: {token_status()}"
    )


def bootstrap() -> dict:
    """一键初始化: 加载 .env 并返回环境状态摘要(JSON 序列化友好)."""
    env_loaded = load_env()
    return {
        "python_ok": check_python_version(),
        "env_loaded": env_loaded,
        "token_configured": bool(os.environ.get("MCP_TOKEN", "").strip()),
        "missing_files": missing_files(),
    }


def main() -> int:
    """独立运行入口: 打印横幅与自检结果."""
    print(banner())
    return 0 if check_python_version() and not missing_files() else 1


if __name__ == "__main__":
    raise SystemExit(main())
