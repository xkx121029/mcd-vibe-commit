# 工具清单与调用约束

> 本文件是 mcd-vibe-commit 对麦当劳 MCP Server 工具的**只读白名单**说明。
> Skill 执行时必须严格遵守: 仅调用下表中的只读工具, 严禁任何写操作。

## 允许调用(只读)

| 工具 | 用途 | 调用时机 | 降级策略 |
|---|---|---|---|
| `query-meals` | 拉取当前门店在售餐品名(分类、餐品编码等) | 生成 commit 前, 用真实餐品名填充 `{product}` 占位符 | 失败时使用 `scripts/commit_gen.py` 内置 `MOCK_PRODUCTS` 列表 |
| `list-nutrition-foods` | 餐品营养信息(能量、蛋白质等), 辅助人格判定话术 | 可选, 不强制 | 直接跳过, 不影响任何功能 |
| `query-nearby-stores` | 按城市+关键词查询门店, 获取 `query-meals` 必需的 `storeCode` | `query-meals` 之前(内部自动调用) | 门店查询失败时使用内置兜底门店编码 |

## query-meals 调用参数(经 2026-10-24 真实验证)

`query-meals` 的官方 inputSchema 要求 **必填** `storeCode` / `orderType` / `beType`,
空 `arguments` 会返回 `{"success": false, "code": 400, "message": "缺少参数"}`。
本 Skill 采用到店自取场景的最小参数集:

```json
{
  "name": "query-meals",
  "arguments": { "storeCode": "<门店编码>", "orderType": 1, "beType": 1 }
}
```

- `orderType=1`: 到店(含到店自取 + 得来速车道取餐)
- `beType=1`: 到店自取, 该场景不传 `beCode`
- `storeCode` 来源: `query-nearby-stores`(`beType=1, searchType=2, city, keyword`),
  或用户直接提供的门店编码(纯数字)
- 返回结构: `data.meals.<mapKey>.name` 即餐品名(实测单门店可达上百个餐品)

`query-nearby-stores` 注意: `searchType=2` 时 **city 与 keyword 需同时提供**,
仅传 city 会返回 "城市名或者关键词不能为空"。

## 明确不调用(写操作一律拒绝)

以下工具涉及资金、订单、账号写操作, **本 Skill 在任何情况下都不会调用**:

| 工具 | 写操作性质 |
|---|---|
| `create-order` | 创建订单(生成支付链接) |
| `cancel-order` | 取消订单 |
| `auto-bind-coupons` | 一键领券 |
| `delivery-create-address` | 新增配送地址 |
| `calculate-price` | 价格计算(为下单铺路, 本场景不需要) |
| `mall-create-order` | 积分商城下单 |
| `party-order-create` | 主题活动下单 |
| `draw-lottery` | 积分抽奖 |

如用户要求执行上述任何写操作, Agent 必须拒绝并说明: 本 Skill 仅用于人格测试与
commit 文案生成, 不做真实交易。

## 服务限制与错误码(官方说明)

| code | 原因 | 处理建议 |
|---|---|---|
| 401 | MCP Token 无效、已过期或未提供 | 引导用户重新配置 Token |
| 429 | 触发限流(每 Token 每分钟最多 600 次请求) | 降低请求频率; 本 Skill 单次执行最多 2 次请求 |
| 400 | 参数缺失(如 query-meals 未传 storeCode) | 按上文参数集修正 |

任何错误码出现时, `scripts/mcp_client.py` 均返回空列表, 由上层无缝切换 mock 数据。
