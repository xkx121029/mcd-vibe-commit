# workbuddy.md — 使用 WorkBuddy 的开发过程记录

> 本文件用于麦当劳程序员创意开发大赛「WorkBuddy 专项奖励」核验
> （排行榜前 100 名且提交本文件，可获得 WorkBuddy 3,000 积分）。
> 记录 mcd-vibe-commit 从构思到交付的完整 WorkBuddy 协作过程。

## 1. 项目概述

- 项目：mcd-vibe-commit（麦门人格 Commit 生成器）
- 形态：遵循 Agent Skills 标准的 Skill（SKILL.md + scripts/ + references/ + assets/）
- 技术栈：Python 3.10+ 纯标准库（urllib / json / random / pathlib），零第三方依赖
- MCP：麦当劳 MCP Server（https://mcp.mcd.cn，Streamable HTTP，Bearer Token）

## 2. 连接器配置（WorkBuddy 自定义连接器）

1. 左侧边栏进入【专家·技能·连接器】→【连接器】页签；
2. 右上角【自定义连接器】→【配置 MCP】；
3. 填入官方配置 JSON（与本仓库 `mcp-config.example.json` 一致）：

   ```json
   {
     "mcpServers": {
       "mcd-mcp": {
         "type": "streamablehttp",
         "url": "https://mcp.mcd.cn",
         "headers": {
           "Authorization": "Bearer ${MCP_TOKEN}"
         }
       }
     }
   }
   ```

4. 保存后回到【自定义连接器】将 `mcd-mcp` 启用；
5. 对话中即可让 AI 调用只读工具（query-meals / query-nearby-stores / list-nutrition-foods）。

## 3. 对话上下文（开发过程中的关键协作节点）

| 阶段 | 对话内容 | 产出 |
|---|---|---|
| 需求确认 | 明确「麦门人格 + commit 生成」创意、只读红线、Token 安全硬约束 | SKILL.md 前置检查与拒绝场景设计 |
| 官方规范对齐 | 抓取大赛主仓库 README / activityGuidelines / CONTEST_DECLARATION 原文 | 必需文件清单、报名 Issue 格式、CONTEST_DECLARATION.md 官方原文 |
| MCP 协议验证 | 用 `tools/list` 读取官方 schema，发现 `query-meals` 必填 storeCode/orderType/beType；实测「查门店→拉菜单」全流程 | `mcp_client.py` 的真实调用链与混合文本 JSON 解析 |
| 编码 | 人格判定矩阵、commit 模板池、Token 掩码/落盘工具 | `scripts/persona.py`、`commit_gen.py`、`mcp_client.py`、`init.py` |
| 自检 | 离线运行 `verify.py`（不依赖真实 Token 与网络） | 全绿 ✅ All checks passed!（14 项检查） |
| 端到端 | 测试 Token 写入本地 `.env`（chmod 600，gitignored）后跑通「答题→人格→MCP 真实菜单→commit」 | 拉取 12 个真实餐品名，commit 成功填充 |
| 交付 | git 初始化与首次提交 | `68d5b90 init: mcd-vibe-commit skill`；git 全历史无 Token 明文 |

### 第 2 轮迭代（同日）

| 阶段 | 对话内容 | 产出 |
|---|---|---|
| 需求 | 「加上至少十个彩蛋，更多人格，类似 MBTI 的四个字母结果」 | 12 个彩蛋 + 人格 6→9 + MBTI 四字母体系 |
| 编码 | 新增 `scripts/easter_eggs.py`；`persona.py` 增加 3 种人格（麦淇淋甜蜜派/麦当劳效率侠/随心配体验官兜底独立化）与 16 组合四字母称号表；`commit_gen.py` 增加 3 组模板 | v2 代码 |
| 文档同步 | SKILL.md 彩蛋机制、persona-matrix.md 人格/四字母矩阵、README 功能与示例 | 文档表格经代码交叉验证 9/9 一致 |
| 自检扩容 | verify.py 从 14 项扩展到 20 项（新增 MBTI、彩蛋、人格/模板对齐检查） | 全绿 ✅ 20/20 |

### 第 3 轮迭代（GitHub 发布）

| 阶段 | 对话内容 | 产出 |
|---|---|---|
| 需求 | 「发布到 github 再给我一份标题和简介」 | 仓库创建 + 推送 + 报名 Issue 文案 |
| 排障 | `git push` TLS 波动重试；git 不读 `GH_TOKEN` 环境变量（could not read Username）→ `gh auth setup-git` 配置凭据后推送成功 | 3 个提交完整推送到 master |
| 安全复核 | PAT 仅经环境变量使用未落盘；本地 `git grep -F` 扫全部历史 + 远端 tree 双重确认 `.env` 未推送 | git 历史与远端均无 Token 明文 |
| 内容校验 | raw.githubusercontent.com 逐文件 diff 遇网络超时，改用 `gh api contents` base64 解码逐字节比对 | 远端 17 个文件与本地逐字节一致 ✅ |

仓库地址：https://github.com/xkx121029/mcd-vibe-commit（PUBLIC，默认分支 master）。

### 第 4 轮迭代（选项扩容）

| 阶段 | 对话内容 | 产出 |
|---|---|---|
| 需求反馈 | 「选择的选项不够全面」——原问卷每题仅 A-D 四个选项，嗜甜不嗜辣/咖啡续命/早餐档/习惯+羊毛合一等画像无选项可落，`sweet` 无纯甜入口、`coffee` 维度不存在，部分人格与四字母组合实际不可达 | 定位为输入覆盖问题，非文案问题 |
| 设计 | 每题扩至 A-F 共 6 个选项（18 个选项）；新增第 7 维度 `coffee`；麦咖啡续命党改为「熬夜或咖啡因」双路径命中；Q2-F「老位置老配方+张张用券」打通 F+U（既省钱又重仪式）组合 | 计分表重构 |
| 编码 | `persona.py`：VALID_ANSWERS A-F、DIMENSIONS +coffee、三张计分表重写、麦咖啡条件放宽；SKILL.md 问卷/非法答案文案同步；`persona-matrix.md` 全节重写 | v3 代码与文档 |
| 自检扩容 | verify.py 从 20 项扩展到 21 项，新增「选项覆盖与可达性」：枚举 216 组合，断言 9 人格与 16 四字母全部可达；预期表演算示例扩至 10 组 | 全绿 ✅ 21/21；文档↔代码交叉验证 10/10 一致 |
| 顺手修复 | README 示例的四字母释义与代码真实输出不一致（误写「凌晨型」，实为「养生型」）；verify.py 遗留「6 种人格模板」过期文案 | 以代码实际输出为准修正 |

验证结果：216 组合下 9 人格命中率 4.6%~16.7% 分布均衡，16 种四字母代码 100% 可达。

## 4. Skill 调试方法

```bash
cd mcd-vibe-commit

# 离线全量自检（文件完整性 / 人格判定 / commit 生成 / Token 工具 / 降级 / 安全扫描）
python verify.py

# 各脚本独立运行
python scripts/init.py        # 横幅 + 环境自检（Token 只显示掩码）
python scripts/persona.py     # 三组答题的人格判定演示
python scripts/commit_gen.py  # 九种人格的 commit 演示（mock 模式）
python scripts/mcp_client.py  # 真实 MCP 调用（需 .env 配置 Token）
```

调试要点：所有脚本均可 `python scripts/xxx.py` 独立运行；`verify.py` 刻意不依赖
网络与真实 Token，保证任何环境可重复验证。

## 5. 安全约束落地记录

- 测试 Token 仅用于本地验证，未出现在任何提交文件中（`verify.py` 内置
  Bearer/`MCP_TOKEN=` 长串扫描检查，每次自检强制校验）；
- 代码统一 `os.environ.get("MCP_TOKEN")` 读取，配置示例统一 `${MCP_TOKEN}` 占位符；
- Agent 回复只显示 Token 前 4 位 + `****`；
- `.env` 已加入 `.gitignore`，写入时 chmod 600。

## 6. WorkBuddy 积分申请

- 本仓库已提交 `workbuddy.md`，且项目真实使用腾讯 WorkBuddy 智能体开发；
- 按大赛规则：进入排行榜（Star 排名前 100）且真实使用 WorkBuddy 并提交本文件，
  可获得 WorkBuddy 3,000 积分；前三名可获得 10,240 积分；
- 兑换方式：2026-11-14 前根据麦当劳邮箱通知的兑奖链路/兑换码进行兑换，
  同一 WorkBuddy 账号仅限兑换 1 份积分奖励；
- 积分问题联系：workbuddy@tencent.com（来信请注明活动名称
  「麦当劳程序员创意开发大赛活动」）。
