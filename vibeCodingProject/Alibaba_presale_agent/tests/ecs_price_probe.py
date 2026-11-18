#!/usr/bin/env python3
"""探测国际站定价计算器底层询价 API（buy-api.alibabacloud.com）。

已验证：无需登录，响应 data.order.orderLines.0.moduleInstance 按模块返回分项价
（payFee 单位为分，/100 得 USD），instance_type 模块即纯算力价。
关键请求结构：components[].instanceProperty 数组，instance_type 组件必须附带
instance_type_family 属性，否则报"配件属性 instanceProperty 为空"。
用法：python3 tests/ecs_price_probe.py [region] [instance_type]
示例：python3 tests/ecs_price_probe.py cn-hongkong ecs.ebmg9ae.48xlarge
"""
import json
import sys
import time
import urllib.request

URL = ("https://buy-api.alibabacloud.com/price/getLightWeightPrice2.json"
       "?tenant=TenantCalculator")
HEADERS = {
    "Content-Type": "application/json",
    "Origin": "https://www.alibabacloud.com",
    "Referer": "https://www.alibabacloud.com/",
    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                  "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/130.0 Safari/537.36",
}


def comp(code, props):
    return {"componentCode": code,
            "instanceProperty": [{"code": k, "value": v} for k, v in props]}


def probe(name, components, duration="1"):
    body = {
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
            "duration": duration,
            "useTimeUnit": "Month",
            "useTimeQuantity": duration,
            "components": components,
        }],
    }
    req = urllib.request.Request(
        URL, data=json.dumps(body).encode(), headers=HEADERS, method="POST")
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=30) as r:
            data = json.loads(r.read())
    except urllib.error.HTTPError as e:
        print(f"== {name} == HTTP {e.code}: {e.read().decode()[:300]}\n")
        return
    dt = time.time() - t0
    if not data.get("success"):
        print(f"== {name} == 业务失败({dt:.2f}s): {data.get('message')}\n")
        return
    order = data["data"]["order"]
    line = order["orderLines"]["0"]
    print(f"== {name} == 成功 耗时{dt:.2f}s 总价 ${order['tradeAmount']}")
    for m in line.get("moduleInstance", []):
        print(f"  {m['moduleCode']:<16} ${m['payFee']/100:.3f}"
              f"  ({m.get('priceType', '-')})")
    print()


region_id = sys.argv[1] if len(sys.argv) > 1 else "cn-wulanchabu"
instance_type = sys.argv[2] if len(sys.argv) > 2 else "ecs.g9i.large"
family = instance_type.rsplit(".", 1)[0]  # ecs.g9i.large -> ecs.g9i

REGION = comp("vm_region_no", [("vm_region_no", region_id)])
INSTANCE = comp("instance_type", [("instance_type", instance_type),
                                  ("instance_type_family", family)])
OS = comp("vm_os", [("vm_os_kind", "linux"), ("vm_os_bit", "64")])
DISK = comp("systemdisk", [("systemdisk_category", "cloud_auto"),
                           ("systemdisk_size", "40")])

probe(f"{region_id} {instance_type} 纯算力 1个月", [REGION, INSTANCE, OS])
probe(f"{region_id} {instance_type} 纯算力 12个月", [REGION, INSTANCE, OS],
      duration="12")
probe(f"{region_id} {instance_type} +40G盘 1个月", [REGION, INSTANCE, OS, DISK])