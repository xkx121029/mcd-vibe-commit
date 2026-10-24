#!/usr/bin/env python3
"""麦门人格 commit message 生成模块.

依据人格类型选择对应模板, 填入餐品名与随机数字, 产出单行 commit message.
无真实餐品数据时, 自动从内置 mock 菜单随机选取(降级策略).

可独立运行: python scripts/commit_gen.py
仅使用标准库, 兼容 Python 3.10+.
"""

from __future__ import annotations

import random

#: 无真实餐品数据时的内置 mock 菜单(降级用, 永不触网)
MOCK_PRODUCTS: tuple[str, ...] = (
    "巨无霸",
    "麦辣鸡腿堡",
    "板烧鸡腿堡",
    "双层吉士堡",
    "薯条",
    "麦乐鸡",
    "麦炫酷",
    "甜筒",
    "麦咖啡",
    "可乐",
    "麦满分",
    "脆汁鸡",
)

#: 每种人格的 commit 模板池, {product} 与 {num} 为占位符
COMMIT_TEMPLATES: dict[str, tuple[str, ...]] = {
    "薯条原教旨主义者": (
        "fix: 修复了缺薯条导致的系统崩溃，已回滚至标准盐量 🍟",
        "style: 将{product}的视觉呈现对齐到薯条黄金标准 🍟",
        "test: 补充了{product}的单元测试，覆盖率 100% 🍟",
        "refactor: 把{product}的盐量逻辑抽成常量，杜绝手抖 🍟",
        "chore: 薯条保温灯常亮，CI 缓存永不过期 🍟",
    ),
    "麦辣嗜辣者": (
        "feat: 新增辣椒素注入模块，辣度等级 Lv.5 已上线 🌶️",
        "refactor: 将{product}架构从单体拆分为微服务，火力全开 🌶️",
        "perf: {product}响应速度优化，延迟降低{num}ms 🌶️",
        "fix: 修复了辣度分布不均导致的用户体验过山车 🌶️",
    ),
    "券包仓鼠": (
        "refactor: 将满减逻辑抽成独立 service，预算节省 42% 🐹",
        "chore: 升级{product}依赖到免费版，breaking changes 零成本 🐹",
        "docs: 更新README，补充{product}优惠券使用指南 🐹",
        "perf: 压缩{product}资源占用，存储成本再省{num}% 🐹",
    ),
    "巨无霸原教旨派": (
        "chore: 升级架构至双层牛肉标准，breaking changes 🍔",
        "feat: 新增{product}经典模式，向后兼容所有版本 🍔",
        "fix: 修复了{product}酱料分布不均的致命bug 🍔",
        "refactor: 保留三层面包结构，中间件一个都不能少 🍔",
    ),
    "麦咖啡续命党": (
        "perf: 咖啡因注入管道优化，响应时间 -200ms ☕",
        "feat: 新增{product}自动续杯定时器，间隔 90 分钟 ☕",
        "fix: 修复了{product}浓度不足导致的困意泄漏 ☕",
        "chore: 浓缩萃取参数调整，构建速度提升{num}% ☕",
    ),
    "凌晨四点麦门人": (
        "hotfix: 生产环境凌晨紧急部署，仅依赖{product} 🌙",
        "feat: 新增{product}夜班模式，24/7 可用 🌙",
        "fix: 修复了凌晨{num}点{product}缺货的致命问题 🌙",
        "docs: 补充凌晨发布 checklist，含{product}应急采购通道 🌙",
    ),
}

#: 未知人格的兜底模板(经典默认款)
_FALLBACK_PERSONA: str = "巨无霸原教旨派"

#: {num} 占位符的随机取值范围
_NUM_RANGE: tuple[int, int] = (10, 99)


def generate_commit(persona_type: str, product_name: str | None = None) -> str:
    """生成一条麦门人格 git commit message.

    Args:
        persona_type: 人格类型(中文名, 取 COMMIT_TEMPLATES 的 key);
                      未知人格自动回退到内置经典模板.
        product_name: 真实餐品名(来自 MCP query-meals 的只读查询);
                      None 或空串时从 MOCK_PRODUCTS 随机选取(降级).

    Returns:
        单行 commit message 字符串, 所有占位符均已填充.
    """
    templates = COMMIT_TEMPLATES.get(persona_type) or COMMIT_TEMPLATES[_FALLBACK_PERSONA]
    template = random.choice(templates)
    product = (product_name or "").strip() or random.choice(MOCK_PRODUCTS)
    return template.format(product=product, num=random.randint(*_NUM_RANGE))


def generate_commits(
    persona_type: str,
    product_name: str | None = None,
    count: int = 1,
) -> list[str]:
    """批量生成 count 条 commit message(连续生成彩蛋使用)."""
    if count < 1:
        raise ValueError("count 必须 >= 1")
    return [generate_commit(persona_type, product_name) for _ in range(count)]


def generate_showcase(product_name: str | None = None) -> list[tuple[str, str]]:
    """为全部人格各生成一条 commit, 用于「全部人格」命令.

    Returns:
        [(人格类型, commit message), ...] 共 6 条.
    """
    return [(name, generate_commit(name, product_name)) for name in COMMIT_TEMPLATES]


def list_personas() -> list[str]:
    """返回全部支持的人格类型列表."""
    return list(COMMIT_TEMPLATES.keys())


def main() -> int:
    """独立运行入口: 为每种人格各演示一条 commit(mock 餐品降级模式)."""
    for persona_type in list_personas():
        print(generate_commit(persona_type))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
