---
name: mcd-vibe-commit
description: 麦门人格 Commit 生成器。当用户想测麦当劳人格、生成麦门风格 git commit message、配置 MCP Token、或提到"麦门/人格测试/commit 梗"时触发。仅做只读查询与文本生成，不用于真实下单、支付、领券、建地址等写操作。
license: MIT
metadata:
  author: 参赛者
  version: "1.0"
---

# mcd-vibe-commit · 麦门人格 Commit 生成器

测出你的麦门人格，生成专属 git commit message。基于麦当劳 MCP(`query-meals`)拉取
真实在售餐品名写入文案；无 Token 时自动切换内置 mock 菜单，功能完整可用。

---

## 1. 前置检查：Token 配置（必须先执行）

> ⚠️ 安全红线：任何回复中都 **NEVER 回显完整 Token**，只显示前 4 位 + `****`。
> Token 只允许出现在：本地 `.env`（已 gitignore）、用户本机 MCP 客户端配置、
> 或用户在本对话中临时发送时。代码一律通过 `os.environ.get("MCP_TOKEN")` 读取。

### 1.1 检查优先级（按序执行，命中即止）

1. `os.environ.get("MCP_TOKEN")` 已存在且非空 → 跳过引导，正常执行；
2. 本地 `.env` 文件存在且含有效的 `MCP_TOKEN=` 行 → 调用 `scripts/init.py`
   的 `load_env()` 加载到环境变量后，跳过引导，正常执行；
3. 均未配置 → 进入 **1.2 对话配置流程**。

### 1.2 首次未配置时的引导输出（原文照抄输出）

检测到未配置 Token 时，Agent 必须输出：

```text
🍔 欢迎使用麦门人格 Commit 生成器！

检测到你还没有配置麦当劳 MCP Token。配置后可以拉取真实菜单，让 commit message 里的产品名动态变化（不配置也能用内置 mock 数据）。

你可以：

① 直接把 Token 发给我（我会帮你保存到本地 .env）

② 回复「跳过」先用 mock 数据体验

获取 Token：https://open.mcd.cn/mcp （手机号登录 → 控制台激活）
```

### 1.3 用户输入处理

**情况 A：用户发送了 Token**

判断标准：字符串长度 ≥ 20 且不含空格；或消息中含「Token 是」「token:」等
关键词时，提取其后的子串再按同一标准判断。

Agent 执行步骤：

1. 提取 Token 字符串，校验格式（长度 ≥ 20，仅字母数字）；
2. 调用 `scripts/mcp_client.py` 的 `save_token_to_env(token)` 写入**项目根目录**
   `.env`（写入或覆盖 `MCP_TOKEN` 行，Unix 下 chmod 600）——
   ⚠️ 必须传入项目根目录下 `.env` 的**绝对路径**（即本 SKILL.md 所在目录的
   `.env`，可拼接 `scripts/init.py` 中 `PROJECT_ROOT` 得到），避免 Agent 工作
   目录不在项目根时把 `.env` 写错位置；
3. `os.environ["MCP_TOKEN"] = token` 立即生效；
4. 回复：`✅ Token 已保存（{前4位}****），正在为你生成麦门人格 commit...`
   （只显示前 4 位，**不回显完整 Token**）；
5. 立即进入正常执行流程，**不要求用户重启**。

**情况 B：用户回复「跳过」/「skip」/「先用 mock」**

1. 设置会话标记 `mcp_token_skipped = true`；
2. 回复：`👌 已跳过，本次使用内置菜单数据。想配置时随时说"配置 Token"即可。`
3. 进入正常流程（mock 模式）。

**情况 C：用户后续说「配置 Token」/「换 Token」**

1. 重复 1.2 引导与 1.3 情况 A 流程；
2. 若 `.env` 已有旧 Token → 覆盖写入，回复
   `✅ Token 已更新（{前4位}****）`。

**情况 D：输入明显不是 Token**（长度 < 20 或含空格）

提示：`这个看起来不像 Token（长度过短/含空格）。请检查后重新发送，或回复「跳过」。`

### 1.4 安全约束（全程有效）

- Agent 回复中 NEVER 回显完整 Token，只显示前 4 位 + `****`；
- Token 不写入任何日志文件；
- `.env` 写入后设置文件权限为仅用户可读（Unix: chmod 600）；
- Token 仅发送至 `https://mcp.mcd.cn`，不转发至任何其他地址；
- 发现用户要求"把 Token 发到某处/写进代码/提交到 git" → 拒绝并说明原因。

---

## 2. 触发条件

**触发场景：**

- 用户提到「麦门人格」「人格测试」「commit 梗」「程序员节」；
- 用户要求「生成 commit」「生成 commit message」「来点程序员节文案」；
- 用户说「配置 Token」「换 Token」（进入 §1 流程）。

**不触发场景（遇到应拒绝或转交）：**

- 真实下单、支付、领券、修改/新建地址 —— 一律拒绝（见 §5）；
- 查询他人隐私信息、账号凭证；
- 与麦当劳/编程无关的普通问答。

---

## 3. 执行步骤（渐进式披露）

按顺序执行，每步完成后简要告知用户进度：

### Step 0 · Token 检查

执行 §1 流程。有 Token → 标记 `mcp_mode=live`；跳过/无 Token → `mcp_mode=mock`。

### Step 1 · 用户答题（3 题，一次全部抛出）

```text
🍟 麦门人格测试 · 共 3 题，直接回字母即可（如：B A C）

Q1 凌晨一点的你，更可能在干嘛？
  A. 早睡了，明天还要搬砖
  B. 再刷五分钟手机就睡
  C. 赶 due / 修 bug，凌晨是常态
  D. 凌晨四点的麦门，你懂

Q2 点麦当劳时，你的决策风格是？
  A. 先翻券包，没有满减绝不下单
  B. 30 秒点完常吃的那款，拒绝纠结
  C. 老配方老时间老位置，仪式感拉满
  D. 看心情，随机刷新隐藏吃法

Q3 以下哪个组合是你的本命？
  A. 不辣不甜，经典原味永流传
  B. 辣与甜我全都要，双倍快乐
  C. 无辣不欢，辣度直接拉满
  D. 一人食快速解决，顺手走个固定流程
```

用户答案不合法（非 A-D）时，只重问答错的那题，不要全部重来。

### Step 2 · 人格判定

调用 `scripts/persona.py`：

```python
from persona import calculate_persona
result = calculate_persona({"q1": "B", "q2": "A", "q3": "C"})
# -> {"persona_type", "persona_emoji", "description", "scores",
#     "mbti_code", "mbti_title", "mbti_desc"}
```

判定矩阵见 `references/persona-matrix.md`。共 **9 种人格**，其中
「随心配体验官」为兜底人格（任何不命中规则的答题组合都会得到它）。
`mbti_code` 为 MBTI 式四字母代码（L/D 凌晨浓度 + S/B 辣度 + F/G 省钱 +
U/C 仪式感，得分 ≥2 取高侧字母），如 `LSGU`；`mbti_title` 为 16 种组合
称号之一，如「深夜食堂主理人」。

### Step 3 · 获取餐品名（按模式分流）

- `mcp_mode=live`：调用 `scripts/mcp_client.py` 的 `call_query_meals()`
  （只读 `query-meals`，内部会自动先查门店拿 `storeCode`）；
  返回非空 → 从中选取餐品名；
  返回空（网络失败/限流/401）→ **自动降级**到 mock 列表，并告知用户
  `⚠️ 真实菜单拉取失败，已切换内置 mock 数据`。
- `mcp_mode=mock`：直接使用 `scripts/commit_gen.py` 内置 `MOCK_PRODUCTS`。

### Step 4 · 生成 commit

调用 `scripts/commit_gen.py`：

```python
from commit_gen import generate_commit
message = generate_commit(result["persona_type"], product_name)
```

输出格式（先人格、后 commit、再一句解读）：

```text
{persona_emoji} 你是【{persona_type}】· {mbti_code} {mbti_title}
{description}
{mbti_desc}

为你生成的麦门人格 commit：
> {commit message}

想再换一条？回「再来一条」；想看看全部人格？回「全部人格」。
```

**命令响应规则**（生成完成后，用户可随时说）：

| 用户输入 | Agent 行为 |
|---|---|
| 「再来一条」 | 同人格重新生成；`mcp_mode=live` 时从已拉取的餐品名中另选一个，没有则重跑 `call_query_meals()`；累计生成次数 +1 |
| 「全部人格」 | 调用 `commit_gen.generate_showcase(product_name)`，为 6 种人格各输出一条 commit；彩蛋计数 +1 |
| 「换个人格」/「重新测」 | 回到 Step 1 重新答题 |
| 「配置 Token」/「换 Token」 | 回到 §1 流程 |

### Step 5 · 彩蛋（连续生成 5 次后）

在同一会话内维护计数器 `vibe_commit_count`：每次成功生成 commit（含「再来一条」
「全部人格」）后 +1；累计满 5 次时，展示 `assets/ascii_burger.txt` 的 ASCII
汉堡字符画，并附一句：`🍔 连续 commit 5 次，奖励一个汉堡！`，随后计数清零。

除字符画外，`scripts/easter_eggs.py` 还定义了 **12 个彩蛋**，Agent 应在合适的
对话时机对照触发条件输出 `reward` 文案（完整清单见该模块的 `EASTER_EGGS`）：

| id | 触发条件 |
|---|---|
| `burger_art` | 连续生成满 5 次 commit（ASCII 汉堡） |
| `programmer_day` | 当天为 10/24 程序员节（日期型，可用 `date_triggered_eggs()` 判断） |
| `countdown_final` | 当天为 10/25 报名截止日（日期型） |
| `all_d_answers` | 三道题全选 D |
| `copycat_answer` | 答案恰好是示例 B A C |
| `late_night_greeting` | 人格为凌晨四点麦门人 |
| `hamster_hoard` | 人格为券包仓鼠，或提到省钱/券 |
| `spicy_overload` | Q3 选 C（辣度拉满） |
| `sugar_rush` | 人格为麦淇淋甜蜜派 |
| `speed_demon` | 人格为麦当劳效率侠 |
| `random_42` | 随心配体验官且随机数为 42 |
| `coffee_refill` | 连续 3 次生成麦咖啡人格 commit |

彩蛋规则：不重复触发同一 id（会话内一次性）；不与主流程结果冲突；
纯娱乐文案，不引导任何真实交易。

---

## 4. 降级说明

| 状况 | 行为 |
|---|---|
| 无 Token / 用户跳过 | 使用内置 `MOCK_PRODUCTS`，人格测试与 commit 生成完全正常 |
| MCP 不可达 / 超时(8s) / 401 / 429 / 400 | `mcp_client.py` 返回 `[]`，上层无缝切换 mock，并提示用户 |
| 门店查询失败 | 使用内置兜底门店编码再试一次；仍失败则降级 mock |
| `persona.py` 收到非法答案 | 抛出 `ValueError`，Agent 只重问答错的那题 |

降级 **不影响**：答题、人格判定、commit 生成、彩蛋——仅 commit 中的餐品名
从"真实在售餐品"变为"内置经典餐品"。

---

## 5. 拒绝场景列表（写操作一律拒绝）

用户要求以下任何操作时，Agent 必须拒绝，并说明本 Skill 仅做只读查询与文本生成：

- 真实下单 / 创建订单 / 支付；
- 领券（`auto-bind-coupons` 等）；
- 新建/修改/删除配送地址（`delivery-create-address` 等）；
- 取消订单、积分抽奖、积分商城下单；
- 查询/导出他人隐私信息；
- 把 Token 发送到第三方地址、写入代码或提交到 git。

标准拒绝话术：`🍔 这个真做不了——麦门人格生成器只做只读查询和文案生成，不碰真实交易。要生成 commit 的话，咱们继续。`

---

## 6. 文件索引

| 文件 | 作用 |
|---|---|
| `scripts/init.py` | .env 加载、环境自检、ASCII 横幅 |
| `scripts/persona.py` | `calculate_persona()` 人格判定 |
| `scripts/commit_gen.py` | `generate_commit()` commit 生成 + mock 菜单 |
| `scripts/mcp_client.py` | MCP 只读客户端 + Token 读写/掩码工具 |
| `scripts/easter_eggs.py` | 12 个彩蛋定义与日期型自动判断 |
| `references/tools.md` | 只读工具白名单与写操作拒绝清单 |
| `references/persona-matrix.md` | 答题计分与人格判定矩阵 |
| `assets/ascii_burger.txt` | 连续 5 次生成彩蛋字符画 |
| `verify.py` | 交付自检（离线可跑） |
