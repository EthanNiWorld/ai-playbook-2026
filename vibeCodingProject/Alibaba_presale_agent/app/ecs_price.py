"""
ECS 服务器询价 — 确定性数值层（与 price_verifier 同级，数字不经模型）
====================================================================
数据源：国际站定价计算器底层询价 API（buy-api.alibabacloud.com，无需登录，
返回匿名 USD 列表价）。2026-11-18 实测验证：
  - 乌兰察布 ecs.g9i.large 纯算力包月 $32.290，与官方计算器一致；
  - 响应 data.order.orderLines.0.moduleInstance 按模块拆分（instance_type
    即纯算力价，systemdisk 独立），payFee 单位为分，/100 得 USD；
  - 时长折扣自动生效（12 个月总价低于 12×月价）。
请求结构两个必踩坑（缺了就报错）：
  - instance_type 组件必须附带 instance_type_family 属性；
  - 必须带 vm_os 组件（至少 vm_os_kind=linux），否则 PRICE_DETAIL_NOT_FOUND。
该 API 为计算器内部接口、无官方 SLA：超时/失败时降级引导官方计算器页，
禁止模型凭记忆补数。探针脚本：tests/ecs_price_probe.py（不进镜像）。
"""

import asyncio
import logging
import re
import time

import httpx

log = logging.getLogger("ecs_price")

CALCULATOR_URL = "https://www.alibabacloud.com/zh/pricing-calculator?/commodity/vm_intl"
_API_URL = ("https://buy-api.alibabacloud.com/price/getLightWeightPrice2.json"
            "?tenant=TenantCalculator")
_HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.alibabacloud.com",
    "Referer": "https://www.alibabacloud.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
}
_TIMEOUT = 15.0

# 地域归一两级策略（同 price_verifier “目录优先 ID 裁决”哲学，零维护）：
#   1) 静态别名表：常见中文口语/英文/region id，离线命中、零开销；
#   2) 未命中时动态拉官方在售地域全量列表（getCommodity，24h 内存缓存），
#      按 regionId/localName 精确 + 包含匹配（“柔佛”⊂“马来西亚（柔佛州）”），
#      多命中（如“马来西亚”）时返回候选让模型反问，不猜。
# 静态表同时承载英文口语（regionList 的 localName 仅中文）。
_REGION_ALIASES: dict[str, tuple[str, str]] = {}


def _reg(region_id: str, label: str, *aliases: str) -> None:
    for a in (region_id, label, *aliases):
        _REGION_ALIASES[a.lower()] = (region_id, label)


_reg("cn-wulanchabu", "华北6（乌兰察布）", "乌兰察布", "ulanqab")
_reg("cn-hongkong", "中国香港", "香港", "hong kong", "hongkong", "hk")
_reg("ap-southeast-1", "新加坡", "singapore", "sg")
_reg("cn-beijing", "华北2（北京）", "北京", "beijing")
_reg("cn-hangzhou", "华东1（杭州）", "杭州", "hangzhou")
_reg("cn-shanghai", "华东2（上海）", "上海", "shanghai")
_reg("cn-shenzhen", "华南1（深圳）", "深圳", "shenzhen")
_reg("cn-zhangjiakou", "华北3（张家口）", "张家口", "zhangjiakou")
_reg("cn-chengdu", "西南1（成都）", "成都", "chengdu")
_reg("cn-heyuan", "华南2（河源）", "河源", "heyuan")
_reg("us-east-1", "美国（弗吉尼亚）", "弗吉尼亚", "美东", "virginia", "us east")
_reg("us-west-1", "美国（硅谷）", "硅谷", "美西", "silicon valley", "us west")
_reg("ap-northeast-1", "日本（东京）", "东京", "日本", "tokyo", "japan")
_reg("ap-southeast-3", "马来西亚（吉隆坡）", "吉隆坡", "kuala lumpur")
_reg("ap-southeast-8", "马来西亚（柔佛州）", "柔佛", "柔佛州", "johor")
_reg("ap-southeast-5", "印度尼西亚（雅加达）", "雅加达", "jakarta")
_reg("ap-southeast-7", "泰国（曼谷）", "曼谷", "泰国", "bangkok", "thailand")
_reg("ap-southeast-6", "菲律宾（马尼拉）", "马尼拉", "菲律宾", "manila", "philippines")
_reg("ap-northeast-2", "韩国（首尔）", "首尔", "韩国", "seoul", "korea")
_reg("eu-central-1", "德国（法兰克福）", "法兰克福", "德国", "frankfurt")
_reg("eu-west-1", "英国（伦敦）", "伦敦", "london")
_reg("me-east-1", "阿联酋（迪拜）", "迪拜", "dubai")

# 实例型号形态：ecs.<家族>.<规格>（家族可含连字符，如 ecs.gn7i-c8g1）
_INSTANCE_RE = re.compile(r"^ecs\.[a-z0-9][a-z0-9-]*\.[a-z0-9]+$")


def normalize_instance(raw: str) -> str | None:
    """口语型号归一：'g9i.large' / 'ECS.G9I.LARGE' → 'ecs.g9i.large'。"""
    s = (raw or "").strip().lower()
    if not s:
        return None
    if not s.startswith("ecs."):
        s = "ecs." + s
    return s if _INSTANCE_RE.match(s) else None


def normalize_region(raw: str) -> tuple[str, str] | None:
    return _REGION_ALIASES.get((raw or "").strip().lower())


# 官方在售地域列表：动态兜底的数据源与内存缓存。
# 取询价同域的 getCommodity.json（data.components.vm_region_no，含全量地域
# value/text）。不用计算器前端的 query.alibabacloud.com/rest/sell.ecs.regionList：
# 该域名被办公网零信任策略拦截（2026-11-18 实测 403），而 buy-api 在放行
# 名单内且与价格主链路同源，零额外域名依赖、全程严格证书校验。
_REGION_LIST_URL = ("https://buy-api.alibabacloud.com/commodity/getCommodity.json"
                    "?commodityCode=vm_intl&orderType=BUY&channel=calculator")
_REGION_CACHE_TTL = 24 * 3600
_region_entries: list[tuple[str, str]] = []   # [(region_id, 展示名)]
_region_cache_ts = 0.0


def _parse_region_entries(data: dict) -> list[tuple[str, str]]:
    """从 getCommodity 响应抽地域表；过滤 POC/单测/OXS 专属地域（如
    cn-wulanchabu-acdr-ut-1 “China (Ulanqab) POC”、ap-southeast-7-oxs），
    不对外报价，也避免包含匹配时与公共地域构成假歧义。"""
    items = (data.get("data", {}).get("components", {})
             .get("vm_region_no", {}).get("vm_region_no", []))
    out = []
    for x in items:
        rid, label = str(x.get("value", "")), str(x.get("text", ""))
        if not rid or not label:
            continue
        low = label.lower()
        if ("poc" in low or "oxs" in low or "-ut-" in rid
                or rid.endswith(("-ut", "-oxs"))):
            continue
        out.append((rid, label))
    return out


async def _fetch_region_entries(client: httpx.AsyncClient) -> list[tuple[str, str]]:
    r = await client.get(_REGION_LIST_URL)
    r.raise_for_status()
    return _parse_region_entries(r.json())


def _match_region(raw: str, entries: list[tuple[str, str]]):
    """纯函数匹配：返回 (id, label) / 候选列表（多命中）/ None（未命中）。"""
    s = (raw or "").strip().lower()
    if not s:
        return None
    for rid, label in entries:
        if s == rid.lower() or s == label.lower():
            return (rid, label)
    hits = [(rid, label) for rid, label in entries if s in label.lower()]
    if len(hits) == 1:
        return hits[0]
    if len(hits) > 1:
        return hits
    return None


async def _resolve_region_dynamic(raw: str,
                                  client: httpx.AsyncClient) -> tuple[str, str]:
    """静态表未命中时的兜底：拉全量地域列表匹配。失败抛 LookupError（带引导话术）。"""
    global _region_entries, _region_cache_ts
    if not _region_entries or time.time() - _region_cache_ts > _REGION_CACHE_TTL:
        try:
            entries = await _fetch_region_entries(client)
            if entries:
                _region_entries, _region_cache_ts = entries, time.time()
        except Exception as e:
            log.warning("官方地域列表拉取失败: %s", e)
            if not _region_entries:
                raise LookupError(
                    f"地域「{raw}」未在常见地域表中，且官方地域列表暂不可用，"
                    "请改用官方 region id（如 ap-southeast-8）重试。") from e
    m = _match_region(raw, _region_entries)
    if isinstance(m, tuple):
        return m
    if isinstance(m, list):
        names = "、".join(label for _, label in m)
        raise LookupError(f"地域「{raw}」命中多个官方地域：{names}。"
                          "请向用户确认具体是哪一个，不要猜。")
    raise LookupError(f"官方在售地域列表中未找到「{raw}」。地域表部分条目仅英文名，"
                      "若用户用的是中文地域名，请译成英文（如 曼谷→Bangkok）"
                      "或用官方 region id 重试一次；仍未命中再向用户确认。")


def _comp(code: str, props: list[tuple[str, str]]) -> dict:
    return {"componentCode": code,
            "instanceProperty": [{"code": k, "value": v} for k, v in props]}


def _build_body(instance: str, region_id: str, duration: int,
                disk_gib: int) -> dict:
    family = instance.rsplit(".", 1)[0]
    components = [
        _comp("vm_region_no", [("vm_region_no", region_id)]),
        _comp("instance_type", [("instance_type", instance),
                                ("instance_type_family", family)]),
        _comp("vm_os", [("vm_os_kind", "linux"), ("vm_os_bit", "64")]),
    ]
    if disk_gib > 0:
        components.append(_comp("systemdisk", [
            ("systemdisk_category", "cloud_auto"),
            ("systemdisk_size", str(disk_gib)),
        ]))
    return {
        "tenant": "TenantCalculator",
        "channel": "calculator",
        "bizOccasion": "calculator",
        "orderOrBilling": "order",
        "configurations": [{
            "commodityCode": "vm_intl",
            "specCode": "vm_intl",
            "chargeType": "PREPAY",
            "orderType": "BUY",
            "quantity": 1,
            "pricingCycle": "Month",
            "duration": str(duration),
            "useTimeUnit": "Month",
            "useTimeQuantity": str(duration),
            "components": components,
        }],
    }


async def _query_one(client: httpx.AsyncClient, instance: str, region_id: str,
                     duration: int, disk_gib: int) -> dict:
    """单次询价，返回 {module_code: usd_float}；业务失败抛 RuntimeError。
    注：moduleAttrs 里的规格名直连时仅为家族名（如 ecs.g9i），不带 vCPU/内存，
    配置信息另走规格目录 describeInstanceTypes（见 _fetch_spec_catalog）。"""
    r = await client.post(_API_URL, json=_build_body(instance, region_id,
                                                     duration, disk_gib))
    r.raise_for_status()
    data = r.json()
    if not data.get("success"):
        msg = str(data.get("message", ""))
        if "PRICE_DETAIL_NOT_FOUND" in msg:
            raise RuntimeError("官方定价库未找到该规格在该地域的价格"
                               "（可能未上架或规格名有误）")
        raise RuntimeError(msg[:200] or "询价接口返回失败")
    line = data["data"]["order"]["orderLines"]["0"]
    return {m["moduleCode"]: m["payFee"] / 100
            for m in line.get("moduleInstance", [])}


# 官方规格目录（计算器同源，ecs-buy 域名在办公网放行名单内）：含 cpuCoreCount/
# memorySize/physicalProcessorModel 全量 3000+ 规格，24h 内存缓存；拉取失败
# 不阻断报价，配置列降级为家族后缀推厂商（i=Intel、a/ae=AMD、y=倚天ARM）。
_SPEC_CATALOG_URL = ("https://ecs-buy.alibabacloud.com/api/v2/instance/"
                     "instanceType/describeInstanceTypes.jsonp")
_spec_catalog: dict[str, dict] = {}
_spec_cache_ts = 0.0


async def _fetch_spec_catalog(client: httpx.AsyncClient) -> dict[str, dict]:
    global _spec_catalog, _spec_cache_ts
    if _spec_catalog and time.time() - _spec_cache_ts <= _REGION_CACHE_TTL:
        return _spec_catalog
    try:
        r = await client.get(_SPEC_CATALOG_URL)
        r.raise_for_status()
        arr = (r.json().get("data", {}).get("components", {})
               .get("instance_type", {}).get("instance_type", []))
        cat = {x["instanceTypeId"]: x for x in arr if x.get("instanceTypeId")}
        if cat:
            _spec_catalog, _spec_cache_ts = cat, time.time()
    except Exception as e:
        log.warning("规格目录拉取失败（配置列降级）: %s", e)
    return _spec_catalog


def _spec_cell(instance: str, entry: dict | None) -> str:
    """配置列：vCPU/内存一行 + CPU 厂商型号一行（<br> 换行，前端 marked 直通）；
    目录缺失时降级为家族命名后缀推厂商，判不出则留空不猜。"""
    parts = []
    if entry and entry.get("cpuCoreCount"):
        mem = str(entry.get("memorySize", "?")).rstrip("0").rstrip(".") \
            if "." in str(entry.get("memorySize", "")) else str(entry.get("memorySize", "?"))
        parts.append(f"{entry['cpuCoreCount']} vCPU / {mem} GiB")
    cpu = str((entry or {}).get("physicalProcessorModel", "")).replace("(R)", "").strip()
    if cpu:
        parts.append(cpu)
    else:
        fam = instance.rsplit(".", 1)[0]
        suffix = re.sub(r"^ecs\.[a-z]*?\d+", "", fam)
        if "y" in suffix:
            parts.append("倚天 710（ARM）")
        elif "a" in suffix:
            parts.append("AMD")
        elif "i" in suffix:
            parts.append("Intel")
    return "<br>".join(parts) if parts else "—"


def _usd(v: float) -> str:
    return f"${v:,.2f}"


async def query_ecs_price_struct(instance_type: str, region: str,
                                 system_disk_gib: int = 0) -> dict:
    """结构化询价（问答证据渲染与分享卡片共用的数值层）。

    返回 {"ok": True, instance, region_id, region_label, spec, compute1,
    compute12, avg12, disk1} 或 {"ok": False, "error": 引导话术}。
    """
    instance = normalize_instance(instance_type)
    if not instance:
        return {"ok": False, "error": f"实例规格「{instance_type}」格式无法识别，"
                "请提供形如 ecs.g9i.large / ecs.ebmg9ae.48xlarge 的完整规格名。"}
    disk_gib = max(0, int(system_disk_gib or 0))

    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT, headers=_HEADERS) as client:
            reg = normalize_region(region)
            if not reg:
                try:
                    reg = await _resolve_region_dynamic(region, client)
                except LookupError as e:
                    return {"ok": False, "error": str(e)}
            region_id, region_label = reg
            m1, m12, catalog = await asyncio.gather(
                _query_one(client, instance, region_id, 1, disk_gib),
                _query_one(client, instance, region_id, 12, disk_gib),
                _fetch_spec_catalog(client),
            )
    except Exception as e:
        log.warning("ECS 询价失败 %s@%s: %s", instance, region_id, e)
        return {"ok": False, "error": f"未能核实 {instance} 在 {region_label} 的官方价格（{e}）。"
                f"请勿凭记忆报价，引导用户到官方定价计算器核对：{CALCULATOR_URL}"}

    compute1 = m1.get("instance_type", 0.0)
    compute12 = m12.get("instance_type", 0.0)
    return {
        "ok": True,
        "instance": instance,
        "region_id": region_id,
        "region_label": region_label,
        "spec": _spec_cell(instance, catalog.get(instance)),
        "compute1": compute1,
        "compute12": compute12,
        "avg12": round(compute12 / 12, 2),
        "disk1": m1.get("systemdisk", 0.0) if disk_gib > 0 else 0.0,
        "disk_gib": disk_gib,
    }


def render_price_md(r: dict) -> str:
    """结构化询价结果 → 证据 markdown（四列表，代码渲染、模型逐字搬运）。"""
    compute1, disk_gib = r["compute1"], r["disk_gib"]
    rows = [
        f"| {r['instance']}<br>{r['region_label']} | {r['spec']} "
        f"| {_usd(compute1)} /月 | {_usd(round(compute1 * 12, 2))} /年 |",
    ]
    if disk_gib > 0:
        disk1 = r["disk1"]
        rows.append(f"| 系统盘 ESSD AutoPL {disk_gib}GiB | — "
                    f"| {_usd(disk1)} /月 | {_usd(round(disk1 * 12, 2))} /年 |")
        total1 = compute1 + disk1
        rows.append(f"| 实例+系统盘合计 | — "
                    f"| {_usd(total1)} /月 | {_usd(round(total1 * 12, 2))} /年 |")
    return (
        "#### ECS 官方列表价（国际站 USD · 包年包月）\n"
        "| 规格 · 地域 | 配置 | 月度刊例价 | 年度成本（×12） |\n"
        "|---|---|---|---|\n"
        + "\n".join(rows)
        + f"\n\n说明：年度成本为月度刊例价×12（列表价口径，未含时长折扣）；"
        f"官方包年实付 {_usd(r['compute12'])}/年（折合 {_usd(r['avg12'])}/月）。"
        + "以上为国际站匿名 USD 列表价（不含账号/商务折扣），"
        + ("含所列系统盘，" if disk_gib > 0 else "不含存储、带宽与流量费用，")
        + f"数据来源为官方定价计算器询价接口，核对入口：{CALCULATOR_URL}"
    )


async def query_ecs_price(instance_type: str, region: str,
                          system_disk_gib: int = 0) -> dict:
    """问答主入口：返回 {"evidence_md", "sources"} 或 {"error": 引导话术}。"""
    r = await query_ecs_price_struct(instance_type, region, system_disk_gib)
    if not r.get("ok"):
        return {"error": r["error"]}
    return {
        "evidence_md": render_price_md(r),
        "sources": [{
            "title": f"ECS 定价计算器 · {r['instance']} · {r['region_label']}（官方列表价）",
            "url": CALCULATOR_URL,
            "kind": "official",
        }],
    }