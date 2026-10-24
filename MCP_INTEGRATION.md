# MCP 集成说明（mcd-vibe-commit × 麦当劳 MCP）

## 1. Server 与认证

| 项 | 值 |
|---|---|
| Server 地址 | `https://mcp.mcd.cn` |
| 传输协议 | Streamable HTTP |
| 认证方式 | 请求头 `Authorization: Bearer ${MCP_TOKEN}` |
| Token 申请 | https://open.mcd.cn/mcp （手机号登录 → 控制台 → 激活） |
| 限流 | 每 Token 每分钟最多 600 次请求（本 Skill 单次执行最多 2 次只读请求） |

Token 在代码中只通过 `os.environ.get("MCP_TOKEN")` 读取，配置示例统一使用
`${MCP_TOKEN}` 环境变量占位符（见 `mcp-config.example.json`），
**任何提交文件中均无明文 Token**。

## 2. 使用的工具（全部只读）

| 工具 | 用途 | 是否必用 |
|---|---|---|
| `query-meals` | 拉取当前门店在售餐品名，填充 commit 文案的 `{product}` 占位符 | **必用** |
| `query-nearby-stores` | 按城市+关键词查门店，获取 `query-meals` 必需的 `storeCode` | 内部自动调用 |
| `list-nutrition-foods` | 餐品营养信息，辅助人格判定话术 | 可选 |

**明确不使用**任何写操作工具：`create-order` / `cancel-order` /
`auto-bind-coupons` / `delivery-create-address` / `calculate-price` /
`mall-create-order` / `party-order-create` / `draw-lottery` 等
（完整拒绝清单见 `references/tools.md`）。

## 3. 调用流程

```text
Agent(SKILL.md Step 3)
  │
  ├─ mcp_client.get_token()              读取 os.environ["MCP_TOKEN"]
  │     └─ 未配置 ────────────────────────> 返回 []，切换 mock 菜单（降级）
  │
  ├─ _resolve_store_code(store_hint)
  │     ├─ store_hint 为纯数字 ────────────> 直接作为 storeCode
  │     └─ 否则 call_query_nearby_stores(city, keyword="麦当劳")
  │           arguments: {"beType":1,"searchType":2,"city":...,"keyword":...}
  │           取第一个在营门店 storeCode；失败则用兜底门店编码
  │
  ├─ call_query_meals(store_hint)
  │     POST https://mcp.mcd.cn
  │     Header: Authorization: Bearer ${MCP_TOKEN}
  │     Body:   {"jsonrpc":"2.0","id":N,"method":"tools/call",
  │              "params":{"name":"query-meals",
  │                        "arguments":{"storeCode":"...","orderType":1,"beType":1}}}
  │     └─ 超时 8s；任何异常返回 []
  │
  └─ 解析 result.content[0].text 中内嵌的 JSON
        data.meals.<mapKey>.name → 餐品名列表（去重，最多 12 个）
        失败/为空 ───────────────────> 切换 mock 菜单（降级）
```

响应解析说明：MCP 返回的 `content[0].text` 是「字段说明 + 内嵌 JSON」的混合文本，
客户端用 `json.JSONDecoder.raw_decode` 定位其中第一个可解析的 JSON 对象，
再取 `data.meals` 映射表中的 `name` 字段。

### 已验证的真实调用记录（2026-10-24，本地验证）

| 步骤 | 工具 | 关键参数 | 结果 |
|---|---|---|---|
| 1 | `query-nearby-stores` | `beType=1, searchType=2, city=北京, keyword=麦当劳` | 返回北京新王府井餐厅等门店，`storeCode=1950059` |
| 2 | `query-meals` | `storeCode=1950059, orderType=1, beType=1` | `success=true`，解析出 122 个餐品名（巨无霸、麦辣鸡腿汉堡三件套、板烧鸡腿堡三件套等） |

注意：`query-meals` 的 `arguments` 不能为空——官方 schema 必填
`storeCode` / `orderType` / `beType`，空参数会返回
`{"success":false,"code":400,"message":"缺少参数"}`；
`query-nearby-stores` 在 `searchType=2` 时 `city` 与 `keyword` 需同时提供。

## 4. 业务价值

- **让文案"活"起来**：commit 里的餐品名不是写死的 mock，而是当前门店真实在售餐品，
  每次生成都有"今天的麦当劳"参与感；
- **最小只读闭环示范**：完整展示了「查门店 → 拉菜单 → 取餐品名」的只读调用链，
  以及混合文本响应（字段说明 + 内嵌 JSON）的稳健解析，可作为其他参赛项目的参考；
- **安全边界清晰**：只读白名单 + 写操作拒绝清单 + Token 全链路掩码，
  保证了娱乐向 Skill 不触碰任何真实交易。

## 5. 降级策略

| 状况 | 客户端行为 | Skill 表现 |
|---|---|---|
| 未配置 Token / 用户选择跳过 | `get_token()` 返回 None，不发任何请求 | 使用内置 `MOCK_PRODUCTS`，功能完整 |
| 网络不可达 / DNS 失败 / 超时（8s） | `urllib` 异常被捕获，返回 `[]` | 提示用户后切换 mock 菜单 |
| HTTP 401（Token 无效/过期） | 返回 `[]` | 引导用户重新配置 Token |
| HTTP 429（限流） | 返回 `[]` | 切换 mock，提示稍后再试 |
| HTTP 400（参数错误） | 返回 `[]` | 切换 mock（参数已按官方 schema 固化，正常不会出现） |
| 门店查询失败 | 使用内置兜底门店编码再试一次 | 仍失败则切换 mock |

降级只影响 commit 中餐品名的来源（真实在售 → 内置经典），
**不影响答题、人格判定、commit 生成与彩蛋**。
