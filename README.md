# mcd-vibe-commit 🍔

**麦门人格 Commit 生成器** —— 测出你的麦门人格，生成专属 git commit message。

基于麦当劳 MCP 的只读能力拉取真实在售餐品名，写入你的专属 commit 文案；
没有 Token 也能用内置 mock 菜单完整跑通。程序员节参赛作品，纯娱乐向，
不构成任何点餐建议。

## ✨ 功能列表

- 🧠 **3 题麦门人格测试**：7 个维度打分，判定 9 种麦门人格
  （凌晨四点麦门人 / 麦辣嗜辣者 / 巨无霸原教旨派 / 薯条原教旨主义者 / 券包仓鼠 /
  麦咖啡续命党 / 麦淇淋甜蜜派 / 麦当劳效率侠 / 随心配体验官）
- 🔤 **MBTI 式四字母结果**：输出如 `LSGU` 的四字母代码与专属称号
  （16 种组合，如「深夜食堂主理人」），截图晒圈必备
- 🍟 **人格专属 commit 生成**：每种人格 4-5 套模板，`{product}` 动态填充
- 🥚 **12 个彩蛋**：1024 程序员节、报名倒计时、全选 D 狠人、抄答案选手、
  辣度超标、甜度超标、90 秒传说、宇宙终极答案 42、第三杯续杯……
- 🔁 **「再来一条 / 全部人格」**：同人格换一条，或一次看全 6 种人格的专属 commit
- 📡 **真实菜单联动**：有 Token 时调用 MCP 只读工具 `query-meals` 拉取真实在售餐品名
- 🛡️ **零依赖降级**：无 Token / MCP 不可达时自动切换内置 mock 菜单，功能完整可用
- 💬 **对话式配 Token**：直接把 Token 发给 Agent，自动写入 `.env` 立即生效
- 🎁 **连续生成彩蛋**：同一会话生成满 5 次 commit，掉落 ASCII 汉堡字符画
- 🔒 **只读安全红线**：只用 `query-meals` / `list-nutrition-foods` / `query-nearby-stores`
  三个只读工具，严禁任何下单、领券、建地址等写操作

## 📁 目录结构

```text
mcd-vibe-commit/
├── SKILL.md                      # Skill 定义（Agent 执行规范）
├── scripts/
│   ├── init.py                   # .env 加载 / 环境自检 / 横幅
│   ├── persona.py                # calculate_persona() 人格判定
│   ├── commit_gen.py             # generate_commit() commit 生成
│   ├── mcp_client.py             # MCP 只读客户端 + Token 工具
│   └── easter_eggs.py            # 12 个彩蛋定义与日期型判断
├── references/
│   ├── tools.md                  # 只读工具白名单与拒绝清单
│   └── persona-matrix.md         # 计分规则与人格判定矩阵
├── assets/
│   └── ascii_burger.txt          # 彩蛋字符画
├── README.md
├── CONTEST_DECLARATION.md        # 参赛声明（官方原文，不可改动）
├── MCP_INTEGRATION.md            # MCP 接入说明
├── mcp-config.example.json       # MCP 配置示例（环境变量占位符）
├── .env.example                  # Token 配置模板
├── .gitignore
├── verify.py                     # 交付自检脚本
└── workbuddy.md                  # WorkBuddy 开发过程记录
```

## 🚀 安装方式

把整个 `mcd-vibe-commit/` 目录放入你的 Agent skills 目录即可，例如：

```bash
# WorkBuddy / CodeBuddy 类 Agent
cp -r mcd-vibe-commit ~/.codebuddy/skills/

# 或其他遵循 Agent Skills 标准的客户端, 放入其 skills 目录
```

无需安装第三方依赖（Python 3.10+ 标准库即可运行全部脚本）。

## ⚙️ 配置说明

### 方式一：对话配置（推荐，最省事）

直接对 Agent 说：`测一下我的麦门人格`，首次运行时会引导你：

```text
🍔 欢迎使用麦门人格 Commit 生成器！
检测到你还没有配置麦当劳 MCP Token。...
① 直接把 Token 发给我（我会帮你保存到本地 .env）
② 回复「跳过」先用 mock 数据体验
获取 Token：https://open.mcd.cn/mcp （手机号登录 → 控制台激活）
```

把 Token 直接发给 Agent，它会自动写入本地 `.env`（chmod 600）并立即生效，
全程只显示掩码（前 4 位 + `****`），不回显完整 Token。之后随时可以说
「配置 Token」或「换 Token」重新配置。

### 方式二：手动配置 `.env`

```bash
cp .env.example .env
# 编辑 .env, 填入你申请的 Token:
# MCP_TOKEN=your_token_here
```

### 方式三：MCP 客户端配置（可选）

把 `mcp-config.example.json` 内容复制到你本机 MCP 客户端
（WorkBuddy：连接器 → 自定义连接器 → 配置 MCP），替换 `${MCP_TOKEN}`：

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

> Token 申请入口：https://open.mcd.cn/mcp （手机号登录 → 控制台 → 激活）

## 💬 使用示例

```text
你：测一下我的麦门人格

Agent：🍟 麦门人格测试 · 共 3 题，直接回字母即可（如：B A C）
       Q1 一天中的哪个时刻，你最想来一口麦当劳？
          A. 早睡了… E. 早餐档：麦满分+鲜煮咖啡… F. 夜宵中场
       Q2 点麦当劳时，你的决策风格是？
          A. 先翻券包… E. 新品/限定先行… F. 老位置老配方，券也必须张张用上
       Q3 以下哪个组合是你的本命？
          A. 经典原味… D. 甜食优先… E. 咖啡因优先… F. 一人食快速解决

你：B A C

Agent：🌶️ 你是【麦辣嗜辣者】· DSFC 晨间辣妹效率派
       无辣不欢，火力全开。你的代码像麦辣鸡腿堡一样直接、炽热、后劲十足。
       养生型：早睡早起身体好，早餐卡和麦满分是你的老伙计；嗜辣型：无辣不欢，辣度就是你对生活的态度；省钱型：券包比代码仓库还整洁，每一分钱都要跑出性价比；随性型：随机刷新隐藏吃法，惊喜是你人生的主旋律

       为你生成的麦门人格 commit：
       > feat: 新增辣椒素注入模块，辣度等级 Lv.5 已上线 🌶️
```

mock 模式（未配置 Token）下输出完全一致，仅餐品名来自内置菜单。

```text
你：再来一条

Agent：> test: 补充了麦辣鸡腿汉堡三件套的单元测试，覆盖率 100% 🌶️

你：全部人格

Agent：🍟 薯条原教旨主义者：fix: 修复了缺薯条导致的系统崩溃，已回滚至标准盐量 🍟
       🌶️ 麦辣嗜辣者：feat: 新增辣椒素注入模块，辣度等级 Lv.5 已上线 🌶️
       🐹 券包仓鼠：refactor: 将满减逻辑抽成独立 service，预算节省 42% 🐹
       🍔 巨无霸原教旨派：chore: 升级架构至双层牛肉标准，breaking changes 🍔
       🥤 麦咖啡续命党：perf: 咖啡因注入管道优化，响应时间 -200ms ☕
       🌙 凌晨四点麦门人：hotfix: 生产环境凌晨紧急部署，仅依赖麦乐鸡 🌙
```

> 🎁 彩蛋：同一会话内连续生成满 5 次 commit，会掉落一个 ASCII 汉堡字符画。

## 📡 MCP 说明（只读 + 降级）

- **只读工具**：`query-meals`（必用，拉在售餐品名）、`list-nutrition-foods`（可选）、
  `query-nearby-stores`（辅助，获取 `query-meals` 必需的 `storeCode`）
- **写操作一律拒绝**：下单、领券、建地址、支付、取消订单、抽奖等，见
  `references/tools.md` 拒绝清单
- **降级策略**：无 Token / 网络不可达 / 超时 8s / 401 / 429 / 400 参数错误时，
  自动切换内置 mock 菜单，答题、人格判定、commit 生成、彩蛋全部不受影响
- 详见 [MCP_INTEGRATION.md](MCP_INTEGRATION.md)

## 🏆 参赛信息

- 大赛：麦当劳程序员创意开发大赛（MCP 专项）
- 主仓库（规则 / 报名 / 排行榜）：https://github.com/M-China/mcd-developer-innovation-challenge
- 活动指南：https://github.com/M-China/mcd-developer-innovation-challenge/blob/main/activityGuidelines.md
- MCP Server 仓库：https://github.com/M-China/mcd-mcp-server
- MCP 开放平台（申请 Token）：https://open.mcd.cn/mcp
- 报名及排名截止：2026-10-25 23:59（北京时间）；排行榜以 2026-10-26 00:00 数据定榜
- License：MIT

## 🎯 目标用户

- 想要程序员节文案/梗图的开发者
- 觉得 commit message 太枯燥、想给团队整点活的 Team Leader
- 麦当劳爱好者 & MCP 玩法探索者
- 需要"最小可运行 MCP Skill 模板"参考的参赛者

## 🐛 Issue 提交提醒

提交参赛 Issue 时请务必注意（官方校验逻辑严格）：

- 标题与正文之间**不留多余空行**
- 项目地址使用**裸链接**（不要用 Markdown 格式）
- 报名截止：2026-10-25 23:59（北京时间），排行榜 2026-10-26 00:00 结算
- Issue 格式：

```text
Issue 标题：自定义报名标题
Issue 正文：
【参赛申请】
项目名称：mcd-vibe-commit
项目地址：https://github.com/<你的账号>/mcd-vibe-commit
项目简介：测出你的麦门人格，生成专属 git commit message
```
