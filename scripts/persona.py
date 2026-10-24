#!/usr/bin/env python3
"""麦门人格判定模块.

根据 3 道题的答案计算 6 个维度得分, 再按优先级矩阵判定麦门人格.
维度与计分规则的完整说明见 references/persona-matrix.md.

可独立运行: python scripts/persona.py
仅使用标准库, 兼容 Python 3.10+.
"""

from __future__ import annotations

from typing import Any

#: 合法答案(大小写不敏感)
VALID_ANSWERS: tuple[str, ...] = ("A", "B", "C", "D")

#: 6 个测评维度
DIMENSIONS: tuple[str, ...] = (
    "late_night",  # 凌晨浓度
    "spicy",       # 嗜辣程度
    "sweet",       # 嗜甜程度
    "thrifty",     # 精打细算
    "efficient",   # 效率优先
    "ritual",      # 仪式感
)

# --------------------------------------------------------------------------
# 计分规则(与 references/persona-matrix.md 保持一致, 改规则请同步改文档)
# --------------------------------------------------------------------------

#: Q1 -> late_night(凌晨一点的你在干嘛)
_Q1_LATE_NIGHT: dict[str, int] = {"A": 0, "B": 1, "C": 2, "D": 3}

#: Q2 -> thrifty / efficient / ritual(点餐决策风格)
_Q2_SCORES: dict[str, dict[str, int]] = {
    "A": {"thrifty": 3},
    "B": {"efficient": 3},
    "C": {"ritual": 3},
    "D": {},
}

#: Q3 -> spicy / sweet / efficient / ritual(本命口味组合)
_Q3_SCORES: dict[str, dict[str, int]] = {
    "A": {},
    "B": {"spicy": 2, "sweet": 2},
    "C": {"spicy": 3, "sweet": 3},
    "D": {"efficient": 2, "ritual": 1},
}

# --------------------------------------------------------------------------
# 人格判定矩阵(按优先级从高到低排列, 首个命中的规则生效)
# --------------------------------------------------------------------------
# 优先级说明:
# 1. "凌晨四点麦门人" 条件最苛刻(late_night 精确等于 3), 优先级最高;
# 2. "巨无霸原教旨派" 的条件是 "薯条原教旨主义者" 的严格子集
#    (ritual>=2 且 spicy<=1 且 efficient<=1), 若先判定薯条, 巨无霸将永远
#    无法命中, 因此巨无霸必须先判定;
# 3. 其余规则按特异性从高到低排列;
# 4. 全部未命中时使用兜底人格(经典默认款).
_PERSONA_RULES: tuple[dict[str, Any], ...] = (
    {
        "type": "凌晨四点麦门人",
        "emoji": "🌙",
        "condition": lambda s: s["late_night"] == 3,
        "description": (
            "城市睡了, 麦门不睡。你的 commit 永远带着凌晨四点的 Wi-Fi 信号, "
            "和一份刚出锅的麦满分。"
        ),
    },
    {
        "type": "麦辣嗜辣者",
        "emoji": "🌶️",
        "condition": lambda s: s["spicy"] >= 2 and s["late_night"] >= 1,
        "description": (
            "无辣不欢, 火力全开。你的代码像麦辣鸡腿堡一样直接、炽热、后劲十足。"
        ),
    },
    {
        "type": "巨无霸原教旨派",
        "emoji": "🍔",
        "condition": lambda s: (
            s["ritual"] >= 2 and s["efficient"] <= 1 and s["spicy"] == 0
        ),
        "description": (
            "经典即正义。你信奉双层架构与经典配方, 哪怕 breaking changes "
            "也挡不住你对原版的忠诚。"
        ),
    },
    {
        "type": "薯条原教旨主义者",
        "emoji": "🍟",
        "condition": lambda s: s["ritual"] >= 2 and s["spicy"] <= 1,
        "description": (
            "一切系统最终都应该回滚到标准盐量。你对细节的执念, "
            "比薯条刚出锅的三分钟更严苛。"
        ),
    },
    {
        "type": "券包仓鼠",
        "emoji": "🐹",
        "condition": lambda s: s["thrifty"] >= 2,
        "description": (
            "每一行代码都要精打细算。满减逻辑抽成独立 service, 预算节省 42%。"
        ),
    },
    {
        "type": "麦咖啡续命党",
        "emoji": "🥤",
        "condition": lambda s: s["late_night"] >= 2,
        "description": (
            "咖啡因是编译器的第一燃料。你的 CI 管道里流淌的不是日志, 是浓缩咖啡。"
        ),
    },
)

#: 兜底人格: 以上规则均未命中时使用(经典默认款, 保证任何答题都有结果)
_FALLBACK_PERSONA: dict[str, Any] = {
    "type": "巨无霸原教旨派",
    "emoji": "🍔",
    "description": (
        "没有明显倾向? 那便是经典本身。巨无霸原教旨派欢迎每一位均衡发展的开发者。"
    ),
}


def calculate_persona(answers: dict[str, str]) -> dict[str, Any]:
    """根据答题结果计算维度得分并判定麦门人格.

    Args:
        answers: 形如 {"q1": "B", "q2": "A", "q3": "C"} 的答案字典,
                 答案接受 A-D(大小写不敏感, 自动去除首尾空白).

    Returns:
        包含以下键的字典(JSON 序列化友好):
        - persona_type: 人格类型(中文名)
        - persona_emoji: 人格 Emoji
        - description: 人格描述
        - scores: 6 个维度的得分 dict

    Raises:
        ValueError: 缺少题目, 或答案不合法时.
    """
    normalized = _normalize_answers(answers)
    scores = {dim: 0 for dim in DIMENSIONS}

    # Q1: 仅影响 late_night
    scores["late_night"] += _Q1_LATE_NIGHT[normalized["q1"]]
    # Q2: 影响 thrifty / efficient / ritual 之一(或零)
    for dim, value in _Q2_SCORES[normalized["q2"]].items():
        scores[dim] += value
    # Q3: 影响 spicy / sweet / efficient / ritual
    for dim, value in _Q3_SCORES[normalized["q3"]].items():
        scores[dim] += value

    persona = _judge(scores)
    return {
        "persona_type": persona["type"],
        "persona_emoji": persona["emoji"],
        "description": persona["description"],
        "scores": scores,
    }


def _normalize_answers(answers: dict[str, str]) -> dict[str, str]:
    """校验并规范化答题输入."""
    if not isinstance(answers, dict):
        raise ValueError(
            "answers 必须是 dict, 形如 {'q1': 'A', 'q2': 'B', 'q3': 'C'}"
        )
    normalized: dict[str, str] = {}
    for question in ("q1", "q2", "q3"):
        if question not in answers:
            raise ValueError(f"缺少答题 {question}, 需要 q1/q2/q3 三道题的答案")
        answer = str(answers[question]).strip().upper()
        if answer not in VALID_ANSWERS:
            raise ValueError(
                f"{question} 的答案 {answers[question]!r} 不合法, 只能是 A/B/C/D"
            )
        normalized[question] = answer
    return normalized


def _judge(scores: dict[str, int]) -> dict[str, Any]:
    """按优先级矩阵遍历规则, 返回首个命中的人格; 均未命中则兜底."""
    for rule in _PERSONA_RULES:
        if rule["condition"](scores):
            return rule
    return _FALLBACK_PERSONA


def main() -> int:
    """独立运行入口: 演示三组不同答题的人格判定结果."""
    demos = (
        {"q1": "D", "q2": "C", "q3": "C"},  # -> 凌晨四点麦门人
        {"q1": "B", "q2": "A", "q3": "C"},  # -> 麦辣嗜辣者
        {"q1": "A", "q2": "C", "q3": "D"},  # -> 薯条原教旨主义者
    )
    for answers in demos:
        result = calculate_persona(answers)
        print(f"{answers} -> {result['persona_emoji']} {result['persona_type']}")
        print(f"  scores: {result['scores']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
