#!/usr/bin/env python3
"""mcd-vibe-commit 交付自检脚本.

检查项:
1. 必需文件完整性(与大赛报名要求对齐);
2. calculate_persona() 示例(覆盖 9 种人格 + 兜底 + 非法输入 + 选项可达性枚举);
3. generate_commit() 示例(模板完备性 + mock 降级 + 无未填充占位符);
4. save_token_to_env() + mask_token()(使用一次性假 Token, 临时目录);
5. 无 Token 时降级正常(只读调用安静返回 [], 不发任何网络请求);
6. Token 安全扫描(提交文件中不得出现 Bearer/长串明文);
7. CONTEST_DECLARATION.md 为官方原文(非占位内容);
8. mcp-config.example.json 仅使用环境变量占位符.

本脚本 **不依赖真实 Token 与网络**, 可在任意离线环境重复运行.
用法: cd mcd-vibe-commit && python verify.py
全部通过时输出 "✅ All checks passed!" 并以退出码 0 结束.
"""

from __future__ import annotations

import json
import os
import random
import re
import sys
import tempfile
from pathlib import Path
from typing import Callable

PROJECT_ROOT: Path = Path(__file__).resolve().parent
sys.path.insert(0, str(PROJECT_ROOT / "scripts"))

import commit_gen  # noqa: E402
import easter_eggs  # noqa: E402
import init  # noqa: E402
import mcp_client  # noqa: E402
import persona  # noqa: E402

#: 一次性假 Token(仅本脚本测试用, 长度 >= 20 且纯字母数字, 非任何真实凭证)
FAKE_TOKEN: str = "VibeCheckLocal000011"
FAKE_TOKEN_2: str = "RotateVibeCheck00002"

#: 人格判定预期表: (答题, 人格类型, Emoji), 覆盖全部 9 种人格
_PERSONA_EXPECTATIONS: tuple[tuple[dict[str, str], str, str], ...] = (
    ({"q1": "D", "q2": "C", "q3": "C"}, "凌晨四点麦门人", "🌙"),
    ({"q1": "B", "q2": "A", "q3": "C"}, "麦辣嗜辣者", "🌶️"),
    ({"q1": "A", "q2": "C", "q3": "A"}, "巨无霸原教旨派", "🍔"),
    ({"q1": "A", "q2": "C", "q3": "F"}, "薯条原教旨主义者", "🍟"),
    ({"q1": "A", "q2": "A", "q3": "A"}, "券包仓鼠", "🐹"),
    ({"q1": "C", "q2": "B", "q3": "A"}, "麦咖啡续命党", "🥤"),
    ({"q1": "A", "q2": "D", "q3": "E"}, "麦咖啡续命党", "🥤"),  # 咖啡因路径
    ({"q1": "A", "q2": "D", "q3": "B"}, "麦淇淋甜蜜派", "🍦"),
    ({"q1": "A", "q2": "B", "q3": "A"}, "麦当劳效率侠", "⚡"),
    ({"q1": "A", "q2": "D", "q3": "A"}, "随心配体验官", "🎲"),  # 兜底
)

#: MBTI 四字母预期表: (答题, 四字母代码)
_MBTI_EXPECTATIONS: tuple[tuple[dict[str, str], str], ...] = (
    ({"q1": "D", "q2": "C", "q3": "C"}, "LSGU"),  # 凌晨四点麦门人
    ({"q1": "B", "q2": "A", "q3": "C"}, "DSFC"),  # 麦辣嗜辣者
    ({"q1": "A", "q2": "A", "q3": "A"}, "DBFC"),  # 券包仓鼠
    ({"q1": "C", "q2": "B", "q3": "A"}, "LBGC"),  # 麦咖啡续命党(熬夜路径)
    ({"q1": "A", "q2": "D", "q3": "A"}, "DBGC"),  # 随心配体验官
    ({"q1": "A", "q2": "B", "q3": "A"}, "DBGC"),  # 麦当劳效率侠
    ({"q1": "C", "q2": "F", "q3": "B"}, "LSFU"),  # 麦辣嗜辣者, F+U 组合可达
)

#: 安全扫描: 提交文件中不允许出现的 Token 明文模式
_TOKEN_PATTERNS: tuple[re.Pattern[str], ...] = (
    re.compile(r"(?i)bearer\s+[\"']?[A-Za-z0-9]{20,}"),
    re.compile(r"(?i)mcp_token\s*=\s*[\"']?[A-Za-z0-9]{20,}"),
)
_SCAN_SKIP_DIRS: frozenset[str] = frozenset(
    {".git", "__pycache__", ".egg-info", ".venv", "node_modules", ".pytest_cache"}
)
_SCAN_SUFFIXES: frozenset[str] = frozenset(
    {".py", ".md", ".json", ".yaml", ".yml", ".txt", ".example"}
)


# --------------------------------------------------------------------------
# 检查项
# --------------------------------------------------------------------------

def check_files_exist() -> str:
    """检查交付必需文件齐全."""
    missing = init.missing_files()
    assert not missing, f"缺少文件: {missing}"
    return f"{len(init.REQUIRED_FILES)} 个必需文件全部存在"


def check_persona_matrix() -> str:
    """测试 calculate_persona(): 9 种人格(含兜底)判定正确."""
    assert len(persona.list_persona_types()) == 9, persona.list_persona_types()
    for answers, expected_type, expected_emoji in _PERSONA_EXPECTATIONS:
        result = persona.calculate_persona(answers)
        assert result["persona_type"] == expected_type, (
            f"{answers} 预期 {expected_type}, 实际 {result['persona_type']}"
        )
        assert result["persona_emoji"] == expected_emoji
        assert isinstance(result["description"], str) and result["description"]
        assert set(result["scores"]) == set(persona.DIMENSIONS)
    return f"{len(_PERSONA_EXPECTATIONS)} 组答题覆盖全部 9 种人格, 判定全部正确"


def check_option_coverage() -> str:
    """v3 选项扩容校验: 6 个选项全部合法; 枚举 216 组合, 9 人格与 16 四字母全部可达."""
    import itertools

    letters = list(persona.VALID_ANSWERS)
    assert letters == ["A", "B", "C", "D", "E", "F"], letters
    personas_hit: set[str] = set()
    codes_hit: set[str] = set()
    for q1, q2, q3 in itertools.product(letters, repeat=3):
        result = persona.calculate_persona({"q1": q1, "q2": q2, "q3": q3})
        personas_hit.add(result["persona_type"])
        codes_hit.add(result["mbti_code"])
    assert personas_hit == set(persona.list_persona_types()), (
        f"存在不可达人格: {set(persona.list_persona_types()) - personas_hit}"
    )
    expected_codes = {
        "".join(combo)
        for combo in itertools.product(
            *[(high, low) for _, high, low, _, _ in persona.MBTI_DIMENSIONS]
        )
    }
    assert codes_hit == expected_codes, (
        f"存在不可达四字母代码: {sorted(expected_codes - codes_hit)}"
    )
    return "6 个选项全部合法, 216 种组合覆盖全部 9 人格与 16 种四字母代码"


def check_mbti_code() -> str:
    """测试 MBTI 式四字母代码: 长度/字符集/预期代码/称号/释义."""
    import itertools

    for combo in itertools.product(
        *[(high, low) for _, high, low, _, _ in persona.MBTI_DIMENSIONS]
    ):
        code = "".join(combo)
        assert len(code) == 4
        assert set(code) <= persona.MBTI_LETTERS
        title = persona.mbti_title(code)
        assert title and title != persona._MBTI_TITLE_DEFAULT, f"{code} 缺少称号"
        desc = persona.mbti_desc(code)
        assert desc.count("；") == 3, f"{code} 释义应拼接 4 句: {desc}"
    # 2. 预期代码
    for answers, expected_code in _MBTI_EXPECTATIONS:
        result = persona.calculate_persona(answers)
        assert result["mbti_code"] == expected_code, (
            f"{answers} 预期 {expected_code}, 实际 {result['mbti_code']}"
        )
        assert result["mbti_title"] == persona.mbti_title(expected_code)
        assert result["mbti_desc"] == persona.mbti_desc(expected_code)
    # 3. 阈值边界: 得分 1 取低侧, 2 取高侧
    base = {dim: 0 for dim in persona.DIMENSIONS}
    assert persona.mbti_code({**base, "late_night": 1})[0] == "D"
    assert persona.mbti_code({**base, "late_night": 2})[0] == "L"
    # 4. 未知代码兜底
    assert persona.mbti_title("ZZZZ") == persona._MBTI_TITLE_DEFAULT
    return "16 种组合称号齐全, 7 组预期代码正确, 阈值与兜底正常"


def check_persona_scores() -> str:
    """测试维度计分准确性(含 v3 新增 coffee 维度与新选项)."""
    result = persona.calculate_persona({"q1": "B", "q2": "A", "q3": "C"})
    expected = {
        "late_night": 1,
        "spicy": 3,
        "sweet": 0,
        "thrifty": 3,
        "efficient": 0,
        "ritual": 0,
        "coffee": 0,
    }
    assert result["scores"] == expected, f"得分 {result['scores']} != {expected}"
    # 新选项计分: Q1E(早餐档, coffee+1) + Q2F(老位置用券) + Q3E(咖啡因优先)
    result2 = persona.calculate_persona({"q1": "E", "q2": "F", "q3": "E"})
    expected2 = {
        "late_night": 0,
        "spicy": 0,
        "sweet": 0,
        "thrifty": 2,
        "efficient": 0,
        "ritual": 2,
        "coffee": 4,
    }
    assert result2["scores"] == expected2, f"得分 {result2['scores']} != {expected2}"
    # 大小写与空白容忍
    result3 = persona.calculate_persona({"q1": " b ", "q2": "a", "q3": "c"})
    assert result3["persona_type"] == "麦辣嗜辣者"
    return "Q1/Q2/Q3 计分(含新选项与 coffee 维度)与大小写容忍验证通过"


def check_persona_invalid() -> str:
    """测试非法输入抛出 ValueError."""
    for bad in (
        {"q1": "G", "q2": "A", "q3": "C"},
        {"q1": "A", "q2": "B"},
        {"q1": "1", "q2": "2", "q3": "3"},
        "not-a-dict",
    ):
        try:
            persona.calculate_persona(bad)  # type: ignore[arg-type]
        except ValueError:
            continue
        raise AssertionError(f"非法输入 {bad!r} 未抛出 ValueError")
    return "4 类非法输入均正确抛出 ValueError"


def check_commit_templates() -> str:
    """测试 commit 模板完备性与占位符填充."""
    personas = commit_gen.list_personas()
    assert len(personas) == 9, f"人格模板应有 9 种, 实际 {len(personas)}"
    for name in personas:
        templates = commit_gen.COMMIT_TEMPLATES[name]
        assert 3 <= len(templates) <= 5, f"{name} 模板数 {len(templates)} 不在 3-5"
        for template in templates:
            assert template.strip(), f"{name} 存在空模板"
            if "{product}" in template:
                assert "巨无霸" in template.format(product="巨无霸", num=42)
            if "{num}" in template:
                filled = template.format(product="X", num=42)
                assert "{num}" not in filled and "42" in filled
    for _ in range(50):
        message = commit_gen.generate_commit(random.choice(personas), "麦辣鸡腿堡")
        assert message and "{" not in message and "}" not in message, message
    return "9 种人格模板 3-5 条/种, 占位符填充完整, 随机生成 50 次无残留"


def check_commit_mock_fallback() -> str:
    """测试无餐品名时从 MOCK_PRODUCTS 随机降级."""
    assert len(commit_gen.MOCK_PRODUCTS) >= 6
    hits: set[str] = set()
    for _ in range(50):
        message = commit_gen.generate_commit("巨无霸原教旨派", None)
        for name in commit_gen.MOCK_PRODUCTS:
            if name in message:
                hits.add(name)
    assert hits, "mock 降级 50 次未命中任何 MOCK_PRODUCTS"
    batch = commit_gen.generate_commits("券包仓鼠", None, count=5)
    assert len(batch) == 5 and all(batch)
    return f"mock 菜单 {len(commit_gen.MOCK_PRODUCTS)} 款, 降级命中 {len(hits)} 款, 批量生成正常"


def check_commit_showcase() -> str:
    """测试「全部人格」命令: generate_showcase 覆盖全部人格且与人格判定对齐."""
    showcase = commit_gen.generate_showcase("巨无霸")
    template_personas = set(commit_gen.COMMIT_TEMPLATES)
    judged_personas = set(persona.list_persona_types())
    assert template_personas == judged_personas, (
        f"人格与模板不同步: 仅模板有 {template_personas - judged_personas}, "
        f"仅判定有 {judged_personas - template_personas}"
    )
    assert len(showcase) == 9, len(showcase)
    for persona_type, message in showcase:
        assert message and "{" not in message and "}" not in message, message
    return "generate_showcase 为 9 种人格各生成一条, 人格/模板集合完全一致"


def check_persona_key_case() -> str:
    """测试答题 key 大小写不敏感(Q1/q1 均可)."""
    upper = persona.calculate_persona({"Q1": "B", "Q2": "A", "Q3": "C"})
    lower = persona.calculate_persona({"q1": "B", "q2": "A", "q3": "C"})
    assert upper == lower, "Q1/q1 大小写结果不一致"
    assert upper["persona_type"] == "麦辣嗜辣者"
    return "答题 key 大小写不敏感验证通过"


def check_readonly_tool_whitelist() -> str:
    """测试 MCP 客户端只读白名单不含任何写操作工具."""
    allowed = {
        "query-meals",
        "list-nutrition-foods",
        "query-nearby-stores",
    }
    forbidden = {
        "create-order",
        "cancel-order",
        "auto-bind-coupons",
        "delivery-create-address",
        "calculate-price",
        "mall-create-order",
        "party-order-create",
        "draw-lottery",
    }
    assert set(mcp_client.READONLY_TOOLS) == allowed, mcp_client.READONLY_TOOLS
    assert not (set(mcp_client.READONLY_TOOLS) & forbidden)
    return "只读白名单仅含 3 个官方只读工具, 无任何写操作工具"


def check_token_utils() -> str:
    """测试 mask_token() 与 Token 格式校验(使用一次性假 Token)."""
    assert mcp_client.mask_token(FAKE_TOKEN) == "Vibe****"
    assert mcp_client.mask_token("") == "****"
    assert mcp_client.mask_token("abc") == "abc****"
    assert mcp_client.is_valid_token_format(FAKE_TOKEN)
    assert not mcp_client.is_valid_token_format("short")
    assert not mcp_client.is_valid_token_format("has space token 12345678")
    assert not mcp_client.is_valid_token_format(None)
    return "mask_token 掩码与格式校验(长度>=20/纯字母数字)全部正确"


def check_save_token_to_env() -> str:
    """测试 save_token_to_env(): 写入/覆盖/拒绝非法/chmod 600."""
    with tempfile.TemporaryDirectory() as tmp:
        env_path = Path(tmp) / ".env"
        assert mcp_client.save_token_to_env(FAKE_TOKEN, str(env_path))
        assert f"MCP_TOKEN={FAKE_TOKEN}" in env_path.read_text(encoding="utf-8")
        # 覆盖写入, 不产生重复行
        assert mcp_client.save_token_to_env(FAKE_TOKEN_2, str(env_path))
        lines = env_path.read_text(encoding="utf-8").splitlines()
        token_lines = [line for line in lines if line.strip().startswith("MCP_TOKEN")]
        assert token_lines == [f"MCP_TOKEN={FAKE_TOKEN_2}"], token_lines
        # 非法 Token 拒绝写入
        assert not mcp_client.save_token_to_env("bad", str(env_path))
        assert not mcp_client.save_token_to_env("", str(env_path))
        # Unix 下权限为 600
        if os.name == "posix":
            mode = oct(env_path.stat().st_mode & 0o777)
            assert mode == "0o600", f".env 权限 {mode} 应为 0o600"
    return "写入/覆盖/拒非法/chmod 600 全部正确(假 Token, 临时目录)"


def check_degradation_no_token() -> str:
    """测试无 Token 时只读调用安静降级, 且不发起任何网络请求."""
    original = os.environ.pop("MCP_TOKEN", None)
    try:
        assert mcp_client.get_token() is None
        assert mcp_client.call_query_meals() == []
        assert mcp_client.call_query_nearby_stores() == []
        assert mcp_client.call_list_nutrition_foods() == []
        message = commit_gen.generate_commit("麦辣嗜辣者", None)
        assert message and "{" not in message
        return "无 Token 时只读调用返回 [], commit 生成走 mock 降级, 全程无网络请求"
    finally:
        if original is not None:
            os.environ["MCP_TOKEN"] = original


def check_security_scan() -> str:
    """扫描全部提交文件, 确保无 Token 明文/Bearer 长串."""
    scanned = 0
    for path in PROJECT_ROOT.rglob("*"):
        if not path.is_file() or path.name == ".env":
            continue
        if any(part in _SCAN_SKIP_DIRS for part in path.parts):
            continue
        if path.suffix not in _SCAN_SUFFIXES:
            continue
        text = path.read_text(encoding="utf-8", errors="replace")
        for pattern in _TOKEN_PATTERNS:
            match = pattern.search(text)
            assert match is None, f"{path} 疑似 Token 明文: {match.group(0)[:12]}..."
        scanned += 1
    return f"扫描 {scanned} 个提交文件, 无 Token 明文/Bearer 长串"


def check_declaration_official() -> str:
    """检查 CONTEST_DECLARATION.md 为官方原文(5 个声明段落齐全, 非占位)."""
    text = (PROJECT_ROOT / "CONTEST_DECLARATION.md").read_text(encoding="utf-8")
    for section in ("原创性声明", "合规声明", "信息安全声明", "使用提示", "规则遵守声明"):
        assert section in text, f"缺少官方声明段落: {section}"
    assert "提交前必须替换" not in text, "CONTEST_DECLARATION.md 仍是占位内容"
    return "CONTEST_DECLARATION.md 为官方原文(5 个声明段落齐全)"


def check_mcp_config_example() -> str:
    """检查 mcp-config.example.json 仅使用环境变量占位符."""
    config = json.loads(
        (PROJECT_ROOT / "mcp-config.example.json").read_text(encoding="utf-8")
    )
    server = config["mcpServers"]["mcd-mcp"]
    assert server["type"] == "streamablehttp"
    assert server["url"] == "https://mcp.mcd.cn"
    assert server["headers"]["Authorization"] == "Bearer ${MCP_TOKEN}"
    return "mcp-config.example.json 使用 ${MCP_TOKEN} 占位符, 无明文"


def check_gitignore() -> str:
    """检查 .gitignore 排除 .env 与缓存文件."""
    lines = (PROJECT_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    for entry in (".env", "__pycache__/", "*.pyc"):
        assert entry in lines, f".gitignore 缺少 {entry}"
    return ".gitignore 正确排除 .env / __pycache__ / *.pyc"


def check_easter_egg_asset() -> str:
    """检查彩蛋字符画为 15-20 行 ASCII 内容."""
    text = (PROJECT_ROOT / "assets" / "ascii_burger.txt").read_text(encoding="utf-8")
    lines = [line for line in text.splitlines() if line.strip()]
    assert 15 <= len(lines) <= 20, f"字符画 {len(lines)} 行, 要求 15-20 行"
    assert "BURGER" in text, "字符画应包含 BURGER 字样"
    return f"彩蛋字符画 {len(lines)} 行(要求 15-20), 内容完整"


def check_easter_eggs() -> str:
    """测试彩蛋清单: 至少 10 个, 字段完整, 日期型自动判断正确."""
    from datetime import date

    eggs = easter_eggs.list_easter_eggs()
    assert len(eggs) >= 10, f"彩蛋仅 {len(eggs)} 个, 要求 >= 10"
    ids = [egg.id for egg in eggs]
    assert len(ids) == len(set(ids)), "彩蛋 id 存在重复"
    for egg in eggs:
        assert egg.name and egg.trigger and egg.reward, f"{egg.id} 字段不完整"
        assert egg.kind in ("dialogue", "date"), f"{egg.id} 类型非法: {egg.kind}"
        assert easter_eggs.get_egg(egg.id) is egg
    assert easter_eggs.get_egg("not-exist") is None
    assert easter_eggs.date_triggered_eggs(date(2026, 10, 24)) == ["programmer_day"]
    assert easter_eggs.date_triggered_eggs(date(2026, 10, 25)) == ["countdown_final"]
    assert easter_eggs.date_triggered_eggs(date(2026, 10, 20)) == []
    date_kind = sum(1 for egg in eggs if egg.kind == "date")
    return f"{len(eggs)} 个彩蛋(含 {date_kind} 个日期型), 字段完整, 日期判断正确"


def check_skill_md_size() -> str:
    """检查 SKILL.md 正文不超过 500 行(规格硬约束)."""
    text = (PROJECT_ROOT / "SKILL.md").read_text(encoding="utf-8")
    total = len(text.splitlines())
    assert total <= 500, f"SKILL.md 共 {total} 行, 超过 500 行上限"
    return f"SKILL.md 共 {total} 行(上限 500)"


#: 检查项注册表(按执行顺序)
CHECKS: tuple[tuple[str, Callable[[], str]], ...] = (
    ("文件完整性", check_files_exist),
    ("人格判定矩阵", check_persona_matrix),
    ("选项覆盖与可达性", check_option_coverage),
    ("MBTI 四字母代码", check_mbti_code),
    ("人格维度计分", check_persona_scores),
    ("人格非法输入", check_persona_invalid),
    ("commit 模板与生成", check_commit_templates),
    ("commit mock 降级", check_commit_mock_fallback),
    ("全部人格 showcase", check_commit_showcase),
    ("人格 key 大小写", check_persona_key_case),
    ("Token 掩码工具", check_token_utils),
    ("Token 写入 .env", check_save_token_to_env),
    ("只读工具白名单", check_readonly_tool_whitelist),
    ("彩蛋清单", check_easter_eggs),
    ("无 Token 降级", check_degradation_no_token),
    ("Token 安全扫描", check_security_scan),
    ("参赛声明官方原文", check_declaration_official),
    ("MCP 配置示例", check_mcp_config_example),
    (".gitignore", check_gitignore),
    ("彩蛋字符画", check_easter_egg_asset),
    ("SKILL.md 行数上限", check_skill_md_size),
)


def main() -> int:
    """运行全部检查项并汇总结果."""
    print("=" * 62)
    print("mcd-vibe-commit 交付自检(离线, 不依赖真实 Token 与网络)")
    print("=" * 62)
    failures = 0
    for name, check in CHECKS:
        try:
            detail = check()
        except AssertionError as exc:
            failures += 1
            print(f"  x {name}: {exc}")
        except Exception as exc:  # noqa: BLE001 - 自检脚本需要兜底所有异常
            failures += 1
            print(f"  x {name}: 未预期异常 {type(exc).__name__}: {exc}")
        else:
            print(f"  + {name}: {detail}")
    print("-" * 62)
    if failures:
        print(f"x {failures}/{len(CHECKS)} 项检查未通过, 请修复后重跑 python verify.py")
        return 1
    print(f"+ {len(CHECKS)}/{len(CHECKS)} 项检查通过")
    print("✅ All checks passed!")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
