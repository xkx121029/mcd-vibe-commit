#!/usr/bin/env python3
"""麦当劳 MCP 只读客户端(零第三方依赖).

仅封装只读工具调用:
- query-nearby-stores : 按城市+关键词查门店(用于获取 query-meals 必需的 storeCode)
- query-meals         : 拉取在售餐品名列表(核心只读工具)
- list-nutrition-foods: 餐品营养信息(可选辅助)

严禁通过本模块调用任何写操作工具(下单/领券/建地址/支付等),
本模块的工具白名单之外的 method 一律不会发出.

Token 安全:
- 只通过 os.environ.get("MCP_TOKEN") 读取, 源码中绝不出现明文 Token;
- 任何网络/协议异常都安静降级返回空列表, 由上层切换 mock 数据.

可独立运行: python scripts/mcp_client.py
仅使用标准库, 兼容 Python 3.10+.
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from json import JSONDecoder
from pathlib import Path
from typing import Any

#: MCP Server 接入地址(Streamable HTTP)
MCP_ENDPOINT: str = "https://mcp.mcd.cn"

#: 请求超时(秒)
REQUEST_TIMEOUT: int = 8

#: 只读工具白名单(本模块只会调用这三个)
TOOL_QUERY_NEARBY_STORES: str = "query-nearby-stores"
TOOL_QUERY_MEALS: str = "query-meals"
TOOL_LIST_NUTRITION_FOODS: str = "list-nutrition-foods"
READONLY_TOOLS: tuple[str, ...] = (
    TOOL_QUERY_NEARBY_STORES,
    TOOL_QUERY_MEALS,
    TOOL_LIST_NUTRITION_FOODS,
)

#: 查门店的默认参数(北京 + "麦当劳" 关键词, 经真实验证可用)
DEFAULT_CITY: str = "北京"
DEFAULT_KEYWORD: str = "麦当劳"

#: 兜底门店编码(麦当劳北京新王府井餐厅, 公开菜单数据, 非敏感信息);
#: 仅当门店查询失败时使用, 保证降级路径仍可能拉到真实菜单
DEFAULT_STORE_CODE: str = "1950059"

#: 项目根目录(scripts/ 的上一级), 用于定位本地 .env
PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent

#: JSON-RPC 请求自增 id
_request_id: int = 0

#: 餐品名最大长度(超过视为脏数据, 丢弃)
_MAX_NAME_LEN: int = 30

#: 最多返回的餐品名数量(commit 生成只需要少量样本)
_MAX_MEALS: int = 12


def get_token() -> str | None:
    """从环境变量读取 MCP_TOKEN, 未配置时返回 None."""
    token = os.environ.get("MCP_TOKEN", "").strip()
    return token or None


def _load_local_env() -> None:
    """把项目根目录 .env 中的 MCP_TOKEN 载入环境变量(不覆盖已有值).

    使 `python scripts/mcp_client.py` 可独立运行; 由 Agent 驱动时,
    SKILL.md 的前置检查会统一调用 scripts/init.py 的 load_env() 完成加载.
    """
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    try:
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key == "MCP_TOKEN" and value and not os.environ.get("MCP_TOKEN"):
                os.environ["MCP_TOKEN"] = value
    except OSError:
        pass


def is_valid_token_format(token: str | None) -> bool:
    """Token 格式校验: 长度 >= 20 且仅含字母数字(无空格/符号)."""
    return bool(token) and len(token) >= 20 and token.isalnum()


def mask_token(token: str) -> str:
    """返回 Token 掩码, 仅保留前 4 位, 绝不回显完整 Token."""
    if not token:
        return "****"
    return token[:4] + "****"


def save_token_to_env(token: str, env_path: str = ".env") -> bool:
    """把 Token 写入或覆盖 .env 中的 MCP_TOKEN 行.

    Args:
        token: 用户提供的 Token 明文(仅来自当前对话, 不落日志).
        env_path: .env 路径, 默认为当前工作目录下的 .env.

    Returns:
        True 表示写入成功; 格式不合法或写盘失败返回 False.

    安全说明:
        - 写入前先做格式校验(长度 >= 20 且仅字母数字);
        - Unix 下尝试 chmod 600, 仅用户可读;
        - Token 只写入 .env(已被 .gitignore 排除), 不写入任何其他文件.
    """
    token = (token or "").strip()
    if not is_valid_token_format(token):
        return False
    try:
        path = Path(env_path)
        lines = (
            path.read_text(encoding="utf-8").splitlines()
            if path.is_file()
            else []
        )
        replaced = False
        for index, line in enumerate(lines):
            if line.strip().startswith("MCP_TOKEN"):
                lines[index] = f"MCP_TOKEN={token}"
                replaced = True
                break
        if not replaced:
            lines.append(f"MCP_TOKEN={token}")
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            os.chmod(path, 0o600)  # Unix: 仅用户可读; Windows 下静默跳过
        except OSError:
            pass
        return True
    except OSError:
        return False


# --------------------------------------------------------------------------
# JSON-RPC 传输层
# --------------------------------------------------------------------------

def _next_request_id() -> int:
    """生成自增的 JSON-RPC 请求 id."""
    global _request_id
    _request_id += 1
    return _request_id


def _post_rpc(method: str, params: dict[str, Any], token: str) -> dict[str, Any] | None:
    """向 MCP Server 发送一次 JSON-RPC 请求, 返回解析后的 dict; 失败返回 None."""
    body = {
        "jsonrpc": "2.0",
        "id": _next_request_id(),
        "method": method,
        "params": params,
    }
    request = urllib.request.Request(
        MCP_ENDPOINT,
        data=json.dumps(body, ensure_ascii=False).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=REQUEST_TIMEOUT) as response:
            content_type = response.headers.get("Content-Type", "")
            payload = response.read().decode("utf-8", "replace")
    except (urllib.error.URLError, OSError, TimeoutError, ValueError):
        # 网络不可达 / 超时 / 限流(429) / 鉴权失败(401) 等一律安静降级
        return None
    return _parse_jsonrpc(payload, content_type)


def _parse_jsonrpc(payload: str, content_type: str) -> dict[str, Any] | None:
    """解析 JSON-RPC 响应, 兼容 application/json 与 text/event-stream(SSE)."""
    text = payload.strip()
    if "text/event-stream" in content_type or text.startswith(("event:", "data:")):
        for line in text.splitlines():
            if line.startswith("data:"):
                text = line[len("data:"):].strip()
                break
    try:
        data = json.loads(text)
    except json.JSONDecodeError:
        return None
    return data if isinstance(data, dict) else None


def _extract_payload(rpc: dict[str, Any] | None) -> dict[str, Any] | None:
    """从 tools/call 的 JSON-RPC 结果中提取内嵌的业务 JSON.

    MCP 返回的 result.content[0].text 是 "字段说明 + 内嵌 JSON" 的混合文本,
    用 JSONDecoder.raw_decode 定位其中第一个可解析的 JSON 对象.
    """
    if not isinstance(rpc, dict):
        return None
    result = rpc.get("result") or {}
    if not isinstance(result, dict):
        return None
    structured = result.get("structuredContent")
    if isinstance(structured, dict):
        return structured
    contents = result.get("content") or []
    texts = [
        item.get("text", "")
        for item in contents
        if isinstance(item, dict) and isinstance(item.get("text"), str)
    ]
    if not texts:
        return None
    return _find_embedded_json(texts[0])


def _find_embedded_json(text: str) -> dict[str, Any] | None:
    """在混合文本中定位第一个可解析的 JSON 对象."""
    decoder = JSONDecoder()
    index = text.find("{")
    while index != -1:
        try:
            obj, _ = decoder.raw_decode(text[index:])
        except json.JSONDecodeError:
            index = text.find("{", index + 1)
            continue
        if isinstance(obj, dict):
            return obj
        index = text.find("{", index + 1)
    return None


# --------------------------------------------------------------------------
# 只读工具封装
# --------------------------------------------------------------------------

def call_query_nearby_stores(
    city: str = DEFAULT_CITY,
    keyword: str = DEFAULT_KEYWORD,
    be_type: int = 1,
) -> list[dict[str, Any]]:
    """只读: 按城市+关键词查询附近门店, 返回门店 dict 列表; 失败返回 [].

    注意: 官方 schema 要求 searchType=2 时 city 与 keyword 需同时提供
    (仅传 city 会返回 "城市名或者关键词不能为空").
    """
    token = get_token()
    if not token:
        return []
    rpc = _post_rpc(
        "tools/call",
        {
            "name": TOOL_QUERY_NEARBY_STORES,
            "arguments": {
                "beType": be_type,
                "searchType": 2,
                "city": city,
                "keyword": keyword,
            },
        },
        token,
    )
    payload = _extract_payload(rpc)
    if not payload or not payload.get("success"):
        return []
    data = payload.get("data")
    return data if isinstance(data, list) else []


def call_query_meals(store_hint: str | None = None) -> list[str]:
    """只读: 拉取在售餐品名列表(生成 commit 前调用).

    流程: 解析 store_hint -> (如需)先查门店拿 storeCode -> query-meals
          -> 解析 data.meals 映射表中的餐品名.

    Args:
        store_hint: 门店编码(纯数字)或城市关键词(如 "上海");
                    None 时使用默认城市 + 关键词查门店.

    Returns:
        餐品名列表(去重, 最多 _MAX_MEALS 个);
        无 Token / 网络不可达 / 参数错误 / 限流等任何失败都返回 [],
        由上层 commit_gen 使用内置 mock 菜单降级, Skill 功能不受影响.
    """
    token = get_token()
    if not token:
        return []
    try:
        store_code = _resolve_store_code(store_hint)
        if not store_code:
            return []
        # 到店自取场景: orderType=1, beType=1, 不传 beCode
        rpc = _post_rpc(
            "tools/call",
            {
                "name": TOOL_QUERY_MEALS,
                "arguments": {
                    "storeCode": store_code,
                    "orderType": 1,
                    "beType": 1,
                },
            },
            token,
        )
        payload = _extract_payload(rpc)
        if not payload or not payload.get("success"):
            return []
        meals = (payload.get("data") or {}).get("meals") or {}
        if not isinstance(meals, dict):
            return []
        names: list[str] = []
        seen: set[str] = set()
        for meal in meals.values():
            if not isinstance(meal, dict):
                continue
            name = str(meal.get("name") or "").strip()
            if name and name not in seen and len(name) <= _MAX_NAME_LEN:
                seen.add(name)
                names.append(name)
        return names[:_MAX_MEALS]
    except Exception:
        # 兜底: 任何未预期异常都不允许冒泡到 Skill 主流程
        return []


def _resolve_store_code(store_hint: str | None) -> str | None:
    """解析门店编码: 纯数字 hint 直接用; 否则按城市查门店取第一个在营门店."""
    hint = (store_hint or "").strip()
    if hint.isdigit():
        return hint
    city = hint or DEFAULT_CITY
    try:
        stores = call_query_nearby_stores(city=city, keyword=DEFAULT_KEYWORD)
    except Exception:
        stores = []
    for store in stores:
        if store.get("businessStatus") and store.get("storeCode"):
            return str(store["storeCode"])
    if stores and stores[0].get("storeCode"):
        return str(stores[0]["storeCode"])
    # 门店查询失败时使用兜底门店, 尽量仍能拉到真实菜单
    return DEFAULT_STORE_CODE


def call_list_nutrition_foods() -> list[str]:
    """只读(可选): 拉取餐品营养信息中的餐品名列表; 失败返回 [].

    该工具无入参, 返回 data 为字符串化的营养数据, 仅做尽力解析.
    """
    token = get_token()
    if not token:
        return []
    try:
        rpc = _post_rpc(
            "tools/call",
            {"name": TOOL_LIST_NUTRITION_FOODS, "arguments": {}},
            token,
        )
        payload = _extract_payload(rpc)
        if not payload or not payload.get("success"):
            return []
        data = payload.get("data")
        if isinstance(data, str):
            try:
                data = json.loads(data)
            except json.JSONDecodeError:
                return []
        if not isinstance(data, list):
            return []
        names = [
            str(item.get("name") or item.get("foodName") or "").strip()
            for item in data
            if isinstance(item, dict)
        ]
        return [name for name in names if name][:_MAX_MEALS]
    except Exception:
        return []


def main() -> int:
    """独立运行入口: 打印 Token 状态(掩码)并尝试拉取真实菜单(失败自动降级)."""
    _load_local_env()
    token = get_token()
    if not token:
        print("MCP_TOKEN: 未配置, 跳过真实菜单拉取(将使用 mock 数据)")
        return 0
    print(f"MCP_TOKEN: 已配置({mask_token(token)})")
    meals = call_query_meals()
    if meals:
        print(f"query-meals 拉取到 {len(meals)} 个餐品: {meals}")
    else:
        print("query-meals 调用失败或返回为空, 已降级(返回 [])")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
