#!/usr/bin/env python3
"""彩蛋(easter eggs)定义与触发判断模块.

彩蛋是 mcd-vibe-commit 的趣味层, 不干扰主流程(答题 -> 人格 -> commit),
由 Agent 在对话中根据触发条件判断并输出对应奖励文案.

彩蛋分两类:
- 对话型: 依赖用户的发言/答案/人格/生成次数, 由 Agent 对照 trigger 判断;
- 日期型: 依赖当天日期, 可用 date_triggered_eggs() 自动判断.

彩蛋文案仅为娱乐, 不涉及任何真实交易引导.

可独立运行: python scripts/easter_eggs.py
仅使用标准库, 兼容 Python 3.10+.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class EasterEgg:
    """单个彩蛋定义.

    Attributes:
        id: 唯一标识(蛇形命名).
        name: 彩蛋名称(给人看).
        trigger: 触发条件描述(Agent 判断依据).
        reward: 命中后输出的奖励文案.
        kind: 彩蛋类型, "dialogue"(对话型) 或 "date"(日期型).
    """

    id: str
    name: str
    trigger: str
    reward: str
    kind: str = "dialogue"


#: 全部彩蛋清单(v2 共 12 个)
EASTER_EGGS: tuple[EasterEgg, ...] = (
    EasterEgg(
        id="burger_art",
        name="汉堡字符画",
        trigger="同一会话内累计生成满 5 次 commit(含「再来一条」「全部人格」)",
        reward=(
            "🍔 连续 commit 5 次, 奖励一个汉堡! "
            "(展示 assets/ascii_burger.txt 字符画, 随后计数清零)"
        ),
    ),
    EasterEgg(
        id="programmer_day",
        name="1024 程序员节",
        trigger="当天日期为 10 月 24 日(程序员节)且为本次会话首次生成 commit",
        reward=(
            "🎂 1024 程序员节快乐! 今天不写 bug, 只写 commit——"
            "每一个 commit 都是写给计算机的情书。"
        ),
        kind="date",
    ),
    EasterEgg(
        id="all_d_answers",
        name="全都选 D 的狠人",
        trigger="三道题的答案全部为 D",
        reward=(
            "🎰 三道题全选 D——麦当劳听了都想问: 这位顾客, 您全是隐藏菜单啊! "
            "获得称号「全都选 D 的狠人」。"
        ),
    ),
    EasterEgg(
        id="copycat_answer",
        name="抄答案选手",
        trigger="用户答案恰好是 SKILL.md 示例中的 B A C",
        reward=(
            "📋 答案和示例一模一样——抄答案选手! "
            "不过抄得挺有品味, 奖励「标准答案」认证一份。"
        ),
    ),
    EasterEgg(
        id="late_night_greeting",
        name="凌晨同类检测",
        trigger="人格判定结果为「凌晨四点麦门人」",
        reward=(
            "🌙 检测到同类: 凌晨四点的麦门人。"
            "你的 commit 带着 Wi-Fi 信号和麦满分的味道。"
        ),
    ),
    EasterEgg(
        id="hamster_hoard",
        name="仓鼠的私藏",
        trigger="人格判定结果为「券包仓鼠」, 或用户发言提到省钱/优惠券/满减",
        reward=(
            "🐹 仓鼠の私藏: 满 30 减 15 的哲学, "
            "就是把每个 service 都抽成可复用模块。"
        ),
    ),
    EasterEgg(
        id="spicy_overload",
        name="辣度超标",
        trigger="Q3 选择了 C(无辣不欢, 辣度拉满)",
        reward="🌶️ 辣度检测: 超标! 建议立即来杯可乐, 顺便给 commit 降降温。",
    ),
    EasterEgg(
        id="sugar_rush",
        name="甜度超标",
        trigger="人格判定结果为「麦淇淋甜蜜派」",
        reward="🍦 甜度超标警告: 该人格的 PR 默认全糖, reviewer 请自备胰岛素。",
    ),
    EasterEgg(
        id="speed_demon",
        name="90 秒传说",
        trigger="人格判定结果为「麦当劳效率侠」",
        reward="⚡ 90 秒出餐记录保持者: 你的 CI 跑得比麦乐送还快。",
    ),
    EasterEgg(
        id="random_42",
        name="宇宙终极答案",
        trigger="人格为「随心配体验官」, 且本次生成的随机数恰好为 42",
        reward="🎲 恭喜触发宇宙终极答案 42! 该餐品的隐藏吃法已解锁。",
    ),
    EasterEgg(
        id="countdown_final",
        name="报名倒计时",
        trigger="当天日期为 10 月 25 日(报名截止日)",
        reward=(
            "⏰ 报名截止倒计时: 今天 23:59 大门关闭, "
            "现在去提 Issue 还来得及! (排行榜 2026-10-26 00:00 定榜)"
        ),
        kind="date",
    ),
    EasterEgg(
        id="coffee_refill",
        name="第三杯续杯",
        trigger="同一会话内累计生成满 3 次「麦咖啡续命党」人格的 commit",
        reward="☕ 第 3 杯了: 自动续杯已触发, 间隔 90 分钟的传统艺能, 诚信互刷。",
    ),
)


def list_easter_eggs() -> list[EasterEgg]:
    """返回全部彩蛋清单(按定义顺序)."""
    return list(EASTER_EGGS)


def get_egg(egg_id: str) -> EasterEgg | None:
    """按 id 查找彩蛋, 不存在返回 None."""
    for egg in EASTER_EGGS:
        if egg.id == egg_id:
            return egg
    return None


def date_triggered_eggs(today: date | None = None) -> list[str]:
    """返回当天应触发的日期型彩蛋 id 列表.

    Args:
        today: 指定日期(测试用), 默认取今天.

    Returns:
        日期型彩蛋 id 列表, 如 ["programmer_day"].
    """
    today = today or date.today()
    triggered: list[str] = []
    if (today.month, today.day) == (10, 24):
        triggered.append("programmer_day")
    if (today.month, today.day) == (10, 25):
        triggered.append("countdown_final")
    return triggered


def main() -> int:
    """独立运行入口: 打印彩蛋清单与今日日期型彩蛋."""
    print(f"共 {len(EASTER_EGGS)} 个彩蛋:")
    for egg in EASTER_EGGS:
        kind = "日期型" if egg.kind == "date" else "对话型"
        print(f"  [{kind}] {egg.id} · {egg.name}")
        print(f"      触发: {egg.trigger}")
    today = date_triggered_eggs()
    print(f"今日日期型彩蛋: {today or '无'}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
