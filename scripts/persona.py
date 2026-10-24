#!/usr/bin/env python3
"""麦门人格判定模块(9 种人格 + MBTI 式四字母代码).

根据 3 道题的答案计算 6 个维度得分, 再按优先级矩阵判定麦门人格,
并输出 MBTI 式四字母代码(如 LSGU)与对应称号.
维度/计分/人格矩阵的完整说明见 references/persona-matrix.md.

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
# 3. "麦淇淋甜蜜派" 与 "麦当劳效率侠" 为 v2 新增人格, 分别覆盖嗜甜与
#    高效率低仪式维度, 排在特异性更高的经典人格之后;
# 4. 全部未命中时使用兜底人格"随心配体验官"(保证任何答题都有结果).
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
    {
        "type": "麦淇淋甜蜜派",
        "emoji": "🍦",
        "condition": lambda s: s["sweet"] >= 2,
        "description": (
            "生活已经够苦了, 代码就要全糖。你的世界由甜筒、麦旋风和双倍糖构成, "
            "review 你的 PR 请自备胰岛素。"
        ),
    },
    {
        "type": "麦当劳效率侠",
        "emoji": "⚡",
        "condition": lambda s: s["efficient"] >= 2 and s["ritual"] <= 1,
        "description": (
            "90 秒出餐记录保持者。你点餐不纠结, 出活不拖更, "
            "人生的点餐台前永远排最短的队。"
        ),
    },
)

#: 兜底人格: 以上规则均未命中时使用(v2 起独立为正式人格, 不再借用巨无霸)
_FALLBACK_PERSONA: dict[str, Any] = {
    "type": "随心配体验官",
    "emoji": "🎲",
    "description": (
        "没有标签能定义你——1+1 随心配, 随机才是你的主场。"
        "每次刷新都有惊喜, 包括你的人生。"
    ),
}

# --------------------------------------------------------------------------
# MBTI 式四字母代码(4 个二分维度, 共 16 种组合)
# --------------------------------------------------------------------------
#: (维度名, 高侧字母, 低侧字母, 高侧标签, 低侧标签)
MBTI_DIMENSIONS: tuple[tuple[str, str, str, str, str], ...] = (
    ("late_night", "L", "D", "凌晨型", "养生型"),
    ("spicy", "S", "B", "嗜辣型", "原味型"),
    ("thrifty", "F", "G", "省钱型", "豪横型"),
    ("ritual", "U", "C", "仪式型", "随性型"),
)

#: 高侧字母阈值(维度得分 >= 2 取高侧, 否则取低侧)
MBTI_HIGH_THRESHOLD: int = 2

#: 合法四字母字符集合
MBTI_LETTERS: frozenset[str] = frozenset(
    letter for _, high, low, _, _ in MBTI_DIMENSIONS for letter in (high, low)
)

#: 16 种组合称号表(键为四字母代码, 顺序: L/D + S/B + F/G + U/C)
_MBTI_TITLES: dict[str, str] = {
    "LSFU": "凌晨四点·辣味守夜人",
    "LSFC": "午夜辣妹·券王",
    "LSGU": "深夜食堂主理人",
    "LSGC": "凌晨放纵派掌门",
    "LBFU": "夜班经典守护者",
    "LBFC": "午夜性价比散人",
    "LBGU": "深夜全餐鉴赏家",
    "LBGC": "凌晨随机干饭王",
    "DSFU": "晨间辣味卷王",
    "DSFC": "晨间辣妹效率派",
    "DSGU": "晨间全餐仪式党",
    "DSGC": "晨间豪横干饭人",
    "DBFU": "晨间省典守味人",
    "DBFC": "清晨性价比散人",
    "DBGU": "晨间原味鉴赏家",
    "DBGC": "清晨随缘干饭人",
}

#: 单个字母释义(用于拼接四字母描述)
_MBTI_LETTER_DESCS: dict[str, str] = {
    "L": "凌晨型: 凌晨的麦门才是正统麦门, 你的生物钟跟着出餐时间走",
    "D": "养生型: 早睡早起身体好, 早餐卡和麦满分是你的老伙计",
    "S": "嗜辣型: 无辣不欢, 辣度就是你对生活的态度",
    "B": "原味型: 经典原味永流传, 你的字典里没有花里胡哨",
    "F": "省钱型: 券包比代码仓库还整洁, 每一分钱都要跑出性价比",
    "G": "豪横型: 想吃就点, 预算管理不存在的",
    "U": "仪式型: 老配方老位置老时间, 你是兼容性拉满的活日历",
    "C": "随性型: 随机刷新隐藏吃法, 惊喜是你人生的主旋律",
}

#: 未知四字母代码的兜底称号
_MBTI_TITLE_DEFAULT: str = "麦门均衡发展主义者"


def calculate_persona(answers: dict[str, str]) -> dict[str, Any]:
    """根据答题结果计算维度得分, 判定麦门人格并生成 MBTI 式四字母代码.

    Args:
        answers: 形如 {"q1": "B", "q2": "A", "q3": "C"} 的答案字典,
                 答案与 key 均大小写不敏感, 自动去除首尾空白.

    Returns:
        包含以下键的字典(JSON 序列化友好):
        - persona_type: 人格类型(中文名, 共 9 种)
        - persona_emoji: 人格 Emoji
        - description: 人格描述
        - scores: 6 个维度的得分 dict
        - mbti_code: MBTI 式四字母代码(如 "LSGU")
        - mbti_title: 四字母组合称号
        - mbti_desc: 四个字母的释义拼接

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
    code = mbti_code(scores)
    return {
        "persona_type": persona["type"],
        "persona_emoji": persona["emoji"],
        "description": persona["description"],
        "scores": scores,
        "mbti_code": code,
        "mbti_title": mbti_title(code),
        "mbti_desc": mbti_desc(code),
    }


def mbti_code(scores: dict[str, int]) -> str:
    """由维度得分生成 MBTI 式四字母代码.

    每个二分维度得分 >= MBTI_HIGH_THRESHOLD 取高侧字母, 否则取低侧字母.
    顺序: L/D(凌晨) + S/B(辣度) + F/G(省钱) + U/C(仪式).
    """
    return "".join(
        high if scores.get(dim, 0) >= MBTI_HIGH_THRESHOLD else low
        for dim, high, low, _, _ in MBTI_DIMENSIONS
    )


def mbti_title(code: str) -> str:
    """返回四字母代码对应的称号; 未知代码返回兜底称号."""
    return _MBTI_TITLES.get(code.strip().upper(), _MBTI_TITLE_DEFAULT)


def mbti_desc(code: str) -> str:
    """返回四字母代码的释义拼接(每个字母一句, 分号连接)."""
    parts = [
        _MBTI_LETTER_DESCS[letter]
        for letter in code.strip().upper()
        if letter in _MBTI_LETTER_DESCS
    ]
    return "；".join(parts)


def list_persona_types() -> list[str]:
    """返回全部 9 种人格类型(规则人格 + 兜底人格, 去重保序)."""
    seen: list[str] = []
    for rule in _PERSONA_RULES:
        if rule["type"] not in seen:
            seen.append(rule["type"])
    if _FALLBACK_PERSONA["type"] not in seen:
        seen.append(_FALLBACK_PERSONA["type"])
    return seen


def _normalize_answers(answers: dict[str, str]) -> dict[str, str]:
    """校验并规范化答题输入(key 大小写不敏感, 如 Q1/q1 均可)."""
    if not isinstance(answers, dict):
        raise ValueError(
            "answers 必须是 dict, 形如 {'q1': 'A', 'q2': 'B', 'q3': 'C'}"
        )
    # key 宽松化: 去空白 + 转小写, 兼容用户输入 "Q1"
    lowered = {str(key).strip().lower(): value for key, value in answers.items()}
    normalized: dict[str, str] = {}
    for question in ("q1", "q2", "q3"):
        if question not in lowered:
            raise ValueError(f"缺少答题 {question}, 需要 q1/q2/q3 三道题的答案")
        answer = str(lowered[question]).strip().upper()
        if answer not in VALID_ANSWERS:
            raise ValueError(
                f"{question} 的答案 {lowered[question]!r} 不合法, 只能是 A/B/C/D"
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
    """独立运行入口: 演示三组答题的人格判定与四字母代码."""
    demos = (
        {"q1": "D", "q2": "C", "q3": "C"},  # -> 凌晨四点麦门人 / LSGU
        {"q1": "B", "q2": "A", "q3": "C"},  # -> 麦辣嗜辣者 / DSFC
        {"q1": "A", "q2": "D", "q3": "A"},  # -> 随心配体验官(兜底) / DBGC
    )
    for answers in demos:
        result = calculate_persona(answers)
        print(
            f"{answers} -> {result['persona_emoji']} {result['persona_type']}"
            f" | {result['mbti_code']} {result['mbti_title']}"
        )
        print(f"  scores: {result['scores']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
