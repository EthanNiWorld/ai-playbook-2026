"""
自测套件 — 离线单测（不调 LLM、不打外部搜索）
运行: .venv/bin/python tests/test_self.py
"""

import asyncio
import json
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

PASS, FAIL = 0, 0


def check(name: str, cond: bool, detail: str = ""):
    global PASS, FAIL
    if cond:
        PASS += 1
        print(f"  ✅ {name}")
    else:
        FAIL += 1
        print(f"  ❌ {name}  {detail}")


def test_price_verifier_units():
    """价格校验：问题识别 / 模型名提取（不联网）"""
    print("[1] price_verifier 单元逻辑")
    from app import price_verifier as pv

    # 价格问题识别
    check("价格问题识别: 中文'价格'", pv.is_price_question("qwen3.8-max 价格是多少"))
    check("价格问题识别: '多少钱'", pv.is_price_question("wan3.0 多钱"))
    check("价格问题识别: 英文 pricing", pv.is_price_question("qwen3.8-max pricing"))
    check("价格问题识别: '$'符号", pv.is_price_question("deepseek cost in $"))
    check("非价格问题不触发", not pv.is_price_question("qwen3.8-max 和 deepseek 哪个强"))

    # 模型名提取
    check("模型名提取: qwen3.8-max", pv.extract_model_names("Qwen3.8-Max 的价格") == ["qwen3.8-max"])
    check("模型名提取: 空格归一 'qwen3.8 max'→'qwen3.8-max'",
          pv.extract_model_names("qwen3.8 max 定价") == ["qwen3.8-max"])
    check("模型名提取: 多模型去重",
          set(pv.extract_model_names("qwen3.8-max 与 deepseek-v4.1-flash 对比价格")) ==
          {"qwen3.8-max", "deepseek-v4.1-flash"})
    check("模型名提取: wan3.0", pv.extract_model_names("Wan3.0-Video 秒价") == ["wan3.0-video"])
    # wan 视频线档位后缀：漏掉 prime 会让详情页去抓 wan3-0（空壳页），
    # 拿不到分辨率分档价 → 模型在残缺证据上长篇内耗（思考 5818 字事故）
    check("模型名提取: 'wan3.0 prime'→'wan3.0-prime'",
          pv.extract_model_names("wan3.0 prime多少钱") == ["wan3.0-prime"])
    check("模型名提取: 'wan3.0 video prime' 多段后缀",
          pv.extract_model_names("wan3.0 video prime 多少钱") == ["wan3.0-video-prime"])
    check("模型名提取: 'wan2.2 t2v plus' 多段后缀",
          pv.extract_model_names("wan2.2 t2v plus 价格") == ["wan2.2-t2v-plus"])
    check("slug 候选: wan3.0-prime → wan3-0-video-prime",
          "wan3-0-video-prime" in pv._slug_candidates("wan3.0-prime"))
    check("slug 候选: 裸版本号同时对应 video / video-prime",
          pv._slug_candidates("wan3.0") == ["wan3-0", "wan3-0-video", "wan3-0-video-prime"])

    # 生图线：qwen-image-* 漏识别会退化成泛化 token "qwen"，把一整片模型扒进证据
    check("模型名提取: qwen-image-2.1-pro",
          pv.extract_model_names("qwen-image-2.1-pro 多少钱") == ["qwen-image-2.1-pro"])
    check("模型名提取: 'qwen image 2.1 pro' 口语写法",
          pv.extract_model_names("qwen image 2.1 pro 多少钱") == ["qwen-image-2.1-pro"])
    check("模型名提取: qwen-mt-image-2.0",
          pv.extract_model_names("qwen-mt-image-2.0 价格") == ["qwen-mt-image-2.0"])
    check("slug→ID: qwen-image-2-1-pro",
          pv._id_from_slug("qwen-image-2-1-pro") == "qwen-image-2.1-pro")

    # 生图详情页：输入图/输出图两个价，单价列必须取输出图价
    image_text = (
        "Pricing This page only shows the original pricing. "
        "China (Beijing) Billing Item Price (USD) Unit "
        "1KImageInput 0.00275 Per image 1KImage Generation 0.03438 Per image "
        "2KImage Generation 0.068761 Per image "
        "Singapore Scope: International Billing Item Price (USD) Unit "
        "1K Image Input 0.003 Per image 1K Image Output 0.04 Per image "
        "2K Image Output 0.075 Per image Rate limits"
    )
    img = pv._parse_media_pricing(image_text)
    img_block = pv._media_evidence("qwen-image-3.0-pro", img)[0]
    check("生图计费: 单价取输出图价而非输入图价",
          "$0.04/张" in img_block and "$0.003/张" not in img_block.split("输入图")[0])
    check("生图计费: 输入图价进备注", "输入图 $0.003/张" in img_block)
    check("生图计费: 分辨率档位保留（无空格写法也要认）",
          "1K" in img_block and "2K" in img_block and "$0.075/张" in img_block)

    # 视频模型详情页按秒计费（"Video generation (480P) 0.068 Per second"）
    media_text = (
        "Pricing This topic only shows the original price. "
        "China (Beijing) Billing item Price (USD) Unit "
        "Video generation (480P) 0.063600 Per second "
        "Video generation (720P) 0.127199 Per second "
        "Singapore Service scope: International Billing item Price (USD) Unit "
        "Video generation (480P) 0.068 Per second "
        "Video generation (1080P) 0.28 Per second "
        "Japan (Tokyo) Service scope: Global Billing item "
        "Video generation (480P) 0.999 Per second Rate limits"
    )
    media = pv._parse_media_pricing(media_text)
    check("视频计费解析: 取到 Singapore/Beijing 两节点",
          set(media) == {"Singapore", "China (Beijing)"}, list(media))
    check("视频计费解析: 分辨率与单位保留",
          media["Singapore"][0][0] == "480P" and media["Singapore"][0][2] == "$0.068/秒",
          media.get("Singapore"))
    check("视频计费解析: 不串入 Tokyo 等其他 region 价格",
          all("0.999" not in p for items in media.values() for _, _, p in items))
    block = pv._media_evidence("wan3.0-video-prime", media)[0]
    check("视频证据表: 只含模型/分辨率/单价，无 token 列",
          "分辨率" in block and "输入价格" not in block and "$0.28/秒" in block)
    check("视频证据表: 默认仅 Singapore",
          "Singapore" in block and "China (Beijing)" not in block)
    # 口语空格/前缀写法归一（'kimi k3.1 pro' 曾因提取失败回退挪用历史模型）
    check("模型名提取: 'kimi k3.1 pro'→'kimi-k3.1-pro'",
          pv.extract_model_names("kimi k3.1 pro的价格呢？") == ["kimi-k3.1-pro"])
    check("模型名提取: 'kimi k3.1-pro' 混合写法",
          pv.extract_model_names("kimi k3.1-pro多少钱") == ["kimi-k3.1-pro"])
    check("模型名提取: 'kimi k3.1' 无后缀",
          pv.extract_model_names("kimi k3.1 定价") == ["kimi-k3.1"])
    check("模型名提取: 'deepseek v4.1 flash'→'deepseek-v4.1-flash'",
          pv.extract_model_names("deepseek v4.1 flash 价格") == ["deepseek-v4.1-flash"])
    check("模型名提取: 'qwen 3.8 max'→'qwen3.8-max'",
          pv.extract_model_names("qwen 3.8 max 价格") == ["qwen3.8-max"])
    check("模型名提取: 规范 ID 不受归一化二次改写",
          pv.extract_model_names("kimi-k3.1-pro 价格") == ["kimi-k3.1-pro"])
    # 2026-11-09 事故：用户问 "deepseek4.1呢？" 抽不出型号 → 家族词守卫禁止挪用历史
    # → 无证据只能甩"暂未能联网核实"。省略 v 前缀/连字符的写法必须补齐。
    check("模型名提取: 'deepseek4.1呢？' 省略 v 与连字符",
          pv.extract_model_names("deepseek4.1呢？") == ["deepseek-v4.1"])
    check("模型名提取: 'deepseek 4.1' 空格写法",
          pv.extract_model_names("deepseek 4.1") == ["deepseek-v4.1"])
    check("模型名提取: 'deepseekv4.1' 连写",
          pv.extract_model_names("deepseekv4.1") == ["deepseek-v4.1"])
    check("模型名提取: 'deepseek4.1 flash呢' 带档位",
          pv.extract_model_names("deepseek4.1 flash呢") == ["deepseek-v4.1-flash"])
    check("模型名提取: deepseek 规范 ID 不被二次改写",
          pv.extract_model_names("deepseek-v4.1-flash 价格") == ["deepseek-v4.1-flash"])
    check("模型名提取: 'glm4.6' 省略连字符",
          pv.extract_model_names("glm4.6多少钱") == ["glm-4.6"])
    check("官方 ID 剥标记: 折扣/缓存后缀不进模型名",
          pv._official_id("qwen3.8-max 50% batch inference discount context caching discount") == "qwen3.8-max")
    # 2026-11-16 事故：qwen4-max 已上架，用户口语写 qwen4.0-max → slug 拼出
    # qwen4-0-max 空壳页、主表也失配 → LLM 凭旧 Prompt 清单断言"尚未上架"并改报 qwen3.8-max。
    check("模型名提取: 'qwen4.0-max' .0 别名归一",
          pv.extract_model_names("qwen4.0-max价格") == ["qwen4-max"])
    check("模型名提取: 'qwen4.0 max' 空格 + .0 别名",
          pv.extract_model_names("qwen4.0 max价格") == ["qwen4-max"])
    check("模型名提取: 'qwen4.0-max-preview' .0 别名带 preview",
          pv.extract_model_names("qwen4.0-max-preview价格") == ["qwen4-max-preview"])
    check("模型名提取: wan3.0 保留 .0（官方 ID 带 .0）",
          pv.extract_model_names("wan3.0-video价格") == ["wan3.0-video"])
    check("模型名提取: qwen3.8-max 不受 .0 规则影响",
          pv.extract_model_names("qwen3.8-max价格") == ["qwen3.8-max"])
    check("官方 ID 剥标记: Cache price 链接尾注不进模型名",
          pv._official_id("qwen4-max Cache price (per million tokens)") == "qwen4-max")
    # 实时在售目录候选召回（离线合成行，不联网）：知识库/Prompt 滞后时
    # 给 LLM 重核线索，而不是任其断言"尚未上架"
    cat_rows = [
        {"model_id": "qwen4-max Cache price (per million tokens)"},
        {"model_id": "qwen4-max-preview"},
        {"model_id": "qwen3.8-max context caching discount"},
        {"model_id": "qwen3.8-max-0902 context caching discount"},
        {"model_id": "qwen3.7-max-2026-06-08"},
        {"model_id": "deepseek-v4.1-flash"},
    ]
    check("目录候选: qwen4.0-max 召回 qwen4-max（.0 别名）",
          pv._catalog_candidates("qwen4.0-max", cat_rows) == ["qwen4-max"])
    check("目录候选: 裸版本号 qwen4.0 也能召回",
          pv._catalog_candidates("qwen4.0", cat_rows) == ["qwen4-max", "qwen4-max-preview"])
    check("目录候选: preview 问法精确命中 preview（不误带正式版）",
          pv._catalog_candidates("qwen4-max-preview", cat_rows) == ["qwen4-max-preview"])
    check("目录候选: 快照版本号不占名额",
          pv._catalog_candidates("qwen3.8-max", cat_rows) == ["qwen3.8-max"])
    check("目录候选: 跨家族不误召回",
          pv._catalog_candidates("glm-5.3", cat_rows) == [])
    check("目录候选: 泛化 token qwen 不召回",
          pv._catalog_candidates("qwen", cat_rows) == [])
    # 目录优先裁决（2026-11-17 事故）：参数量后缀 -27b / -2.4t-a95b 被正则
    # 白名单削成 qwen3.8，家族前缀"假命中"主表合并行又绕过候选兜底。
    # ID 裁决前移到实时行目录，正则降级为口语归一兜底。
    os_rows = cat_rows + [
        {"model_id": "qwen3.8-2.4t-a95b context caching discount"},
        {"model_id": "qwen3.8-27b context caching discount"},
        {"model_id": "qwen3.8-flash"},
    ]
    check("目录裁决: qwen3.8-27b 全串命中（不被削成 qwen3.8）",
          pv._resolve_official_ids("qwen3.8-27b", os_rows) == ["qwen3.8-27b"])
    check("目录裁决: qwen3.8-2.4t-a95b 全串命中",
          pv._resolve_official_ids("qwen3.8-2.4t-a95b", os_rows) == ["qwen3.8-2.4t-a95b"])
    check("目录裁决: 口语空格写法 'qwen3.8 27b'",
          pv._resolve_official_ids("qwen3.8 27b", os_rows) == ["qwen3.8-27b"])
    check("目录裁决: 汉字紧贴最长匹配优先",
          pv._resolve_official_ids("qwen3.8-27b价格", os_rows) == ["qwen3.8-27b"])
    check("目录裁决: 多模型句各自命中",
          pv._resolve_official_ids("qwen3.8-27b和qwen3.8-flash价格差多少", os_rows)
          == ["qwen3.8-27b", "qwen3.8-flash"])
    check("目录裁决: .0 别名 qwen4.0-max → qwen4-max",
          pv._resolve_official_ids("qwen4.0-max", os_rows) == ["qwen4-max"])
    check("目录裁决: preview 精确命中不误带正式版",
          pv._resolve_official_ids("qwen4-max-preview", os_rows) == ["qwen4-max-preview"])
    check("目录裁决: 目录未收录退回口语归一（竞品/未上架）",
          pv._resolve_official_ids("glm-5.3", os_rows) == ["glm-5.3"])
    check("目录裁决: 空目录降级正则路径",
          pv._resolve_official_ids("qwen3.8 max", []) == ["qwen3.8-max"])
    check("目录裁决: 泛化 qwen 不命中目录",
          pv._resolve_official_ids("qwen", os_rows) == ["qwen"])
    # 2026-11-22 事故：目录只有 kimi-k3 与 kimi-k3.1-pro，用户省略 -pro 写
    # kimi-k3.1，正向包含把版本号被截断的 kimi-k3（kimik3 ⊂ kimik31）当成
    # 裁决结果，LLM 思考流里自行发现并补调 pro 才救回。反向命中优先修复。
    kimi_rows = [
        {"model_id": "kimi-k2.5"},
        {"model_id": "kimi-k3"},
        {"model_id": "kimi-k3.1-pro"},
    ]
    check("目录裁决: kimi-k3.1 省略后缀收敛到 pro（不被截断成 kimi-k3）",
          pv._resolve_official_ids("kimi-k3.1", kimi_rows) == ["kimi-k3.1-pro"])
    check("目录裁决: kimi-k3.1-pro 精确命中不受反向规则影响",
          pv._resolve_official_ids("kimi-k3.1-pro", kimi_rows) == ["kimi-k3.1-pro"])
    check("目录裁决: kimi-k3 精确命中不误带 pro",
          pv._resolve_official_ids("kimi-k3", kimi_rows) == ["kimi-k3"])
    check("目录裁决: 裸家族名 kimi 不召回整个家族",
          pv._resolve_official_ids("kimi", kimi_rows) == ["kimi"])
    check("目录裁决: 带中文噪声问句也能收敛（归一 key 剥 CJK）",
          pv._resolve_official_ids("kimi-k3.1，多少钱", kimi_rows) == ["kimi-k3.1-pro"])
    snap_rows = [{"model_id": "qwen3.8-max-0902"}, {"model_id": "qwen3.8-flash"}]
    check("目录裁决: 反向命中不召回快照版本号",
          pv._resolve_official_ids("qwen3.8", snap_rows) == ["qwen3.8-flash"])
    # 开源线详情页把显式缓存读取价写作 "Explicit Cache Hit"（a95b 实测），
    # 不归一会静默丢价；Input (Cache Hit) 则归隐式命中列
    hit_text = (
        "original pricing for model API calls. "
        "Singapore Billing Item Price (USD) Unit "
        "Input 2 Per 1M tokens Output 6 Per 1M tokens "
        "Input (Cache Hit) 0.25 Per 1M tokens "
        "Explicit Cache Creation 2.5 Per 1M tokens "
        "Explicit Cache Hit 0.17 Per 1M tokens "
        "Rate Limits dynamic"
    )
    hp = pv._parse_model_pricing(hit_text)
    check("详情页缓存别名: Explicit Cache Hit 归一为读取价",
          hp.get("Singapore", {}).get("explicit cache read") == "$0.17")
    check("详情页缓存别名: Input (Cache Hit) 归隐式命中",
          hp.get("Singapore", {}).get("input(implicit cache)") == "$0.25")
    hev = pv._detail_evidence("qwen3.8-2.4t-a95b", "https://example.com", hp)
    check("详情页缓存别名: 读取价进备注列", "显式缓存读取 $0.17" in hev[0])
    # qwen4 代起缓存价独立成子表（紧跟同地域主表后）：不接住则缓存列全 "—"，
    # LLM 会反断言"该模型无缓存计费项"（2026-11-16 追问事故）
    cache_html = (
        "<h2>Singapore</h2>"
        "<table><tr><th>Model ID</th><th>Input price (per 1 million tokens)</th>"
        "<th>Output price (per 1 million tokens)</th></tr>"
        "<tr><td>qwen4-max Cache price (per million tokens)</td><td>$1.5</td><td>$4.5</td></tr></table>"
        # 真实页面每个 region 拆多张主表，缓存子表跟在最后一张后：
        # 中间插一张存量表，验证归属按 region 累积而非“最近一张主表”
        "<table><tr><th>Model ID</th><th>Input price (per 1 million tokens)</th>"
        "<th>Output price (per 1 million tokens)</th></tr>"
        "<tr><td>qwen3.8-max context caching discount</td><td>$2</td><td>$6</td></tr></table>"
        "<table><tr><th>Cache write (5m)</th><th>Cache write (1h)</th>"
        "<th>Explicit/implicit cache read</th></tr>"
        "<tr><td>$1.875</td><td>$3</td><td>$0.075</td></tr></table>"
        "<h2>China (Beijing)</h2>"
        "<table><tr><th>Model ID</th><th>Input price (per 1 million tokens)</th>"
        "<th>Output price (per 1 million tokens)</th></tr>"
        "<tr><td>qwen4-max Cache price (per million tokens)</td><td>$1.413</td><td>$4.24</td></tr></table>"
        "<table><tr><th>Model ID</th><th>Input price (per 1 million tokens)</th>"
        "<th>Output price (per 1 million tokens)</th></tr>"
        "<tr><td>qwen3.8-max context caching discount</td><td>$1.65</td><td>$4.951</td></tr></table>"
        "<table><tr><th>Cache write (5m)</th><th>Cache write (1h)</th>"
        "<th>Explicit/implicit cache read</th></tr>"
        "<tr><td>$1.767</td><td>$2.827</td><td>$0.071</td></tr></table>"
    )
    crows = pv._parse_pricing_rows(cache_html)
    check("缓存子表: 读价挂到带 Cache price 链接的行",
          crows[0].get("cache_prices", {}).get("read") == "$0.075")
    check("缓存子表: 地域归属不跨表（Beijing 读价）",
          next(r for r in crows if r["region"] == "China (Beijing)"
               and r["model_id"].startswith("qwen4")).get("cache_prices", {}).get("read") == "$0.071")
    cblock = pv._model_evidence(crows, "qwen4-max")[0]
    cblock_bj = pv._model_evidence(crows, "qwen4-max", "China (Beijing)")[0]
    check("节点选择: 默认主表仅 Singapore",
          "| Singapore" in cblock and "China (Beijing)" not in cblock)
    check("节点选择: 北京主表仅 Beijing",
          "| China (Beijing)" in cblock_bj and "Singapore" not in cblock_bj)
    check("节点选择: 中文别名等价归一",
          pv._model_evidence(crows, "qwen4-max", "北京节点")[0] == cblock_bj)
    check("缓存子表: 默认只带 Singapore 读价",
          "$0.075" in cblock and "$0.071" not in cblock)
    check("qwen4-max: Singapore Cache Input 列必须取到 $0.075",
          "| Singapore | $1.5 | $0.075 | $4.5 |" in cblock)
    check("缓存子表: 北京只带 Beijing 读价",
          "$0.071" in cblock_bj and "$0.075" not in cblock_bj)
    check("qwen4-max: Beijing Cache Input 列必须取到 $0.071",
          "| China (Beijing) | $1.413 | $0.071 | $4.24 |" in cblock_bj)
    check("缓存子表: 写价按 5m/1h 两档进 Cache Write 列",
          "$1.875 (5m) / $3 (1h)" in cblock)
    check("主表证据附来源 URL（Prompt 要求引用证据内 URL）",
          "model-studio/model-pricing" in cblock)
    check("缓存子表: 无缓存链接的 qwen3.8 主行不误挂",
          all("cache_prices" not in r for r in crows if r["model_id"].startswith("qwen3.8")))
    check("官方 ID: Cache unit price 尾注同样剥离",
          pv._official_id("qwen4-max Cache unit price (per million tokens)") == "qwen4-max")

    # 2026-11-18 id=179：官方将 Cache write 改为 Cache creation、Cache price 改为
    # Cache unit price。两处匹配独立，必须覆盖完整的 2×2 新旧文案组合。
    for main_label in ("Cache price", "Cache unit price"):
        for sub_label in ("Cache write", "Cache creation"):
            variant_html = cache_html.replace("Cache price", main_label).replace("Cache write", sub_label)
            vrows = pv._parse_pricing_rows(variant_html)
            sg = next(r for r in vrows if r["region"] == "Singapore" and r["model_id"].startswith("qwen4"))
            bj = next(r for r in vrows if r["region"] == "China (Beijing)" and r["model_id"].startswith("qwen4"))
            case = f"{main_label} × {sub_label}"
            check(f"缓存别名矩阵: {case} 双节点挂接",
                  sg.get("cache_prices") == {"write_5m": "$1.875", "write_1h": "$3", "read": "$0.075"}
                  and bj.get("cache_prices") == {"write_5m": "$1.767", "write_1h": "$2.827", "read": "$0.071"})
            sg_block = pv._model_evidence(vrows, "qwen4-max", "Singapore")[0]
            bj_block = pv._model_evidence(vrows, "qwen4-max", "China (Beijing)")[0]
            check(f"缓存别名矩阵: {case} 证据不跨地域",
                  "$0.075" in sg_block and "$1.875 (5m) / $3 (1h)" in sg_block
                  and "$0.071" not in sg_block
                  and "$0.071" in bj_block and "$1.767 (5m) / $2.827 (1h)" in bj_block
                  and "$0.075" not in bj_block)
    # 产品（非百炼模型）定价题不走百炼校验（Qoder 事故：百炼回落证据会误导 LLM 把
    # model-pricing 链接安到产品头上）；产品定价交给知识库检索回答
    check("产品定价题不触发模型校验: qoder", not pv.is_price_question("qoder是怎么计费的"))
    check("产品定价题不触发模型校验: Qoder Teams", not pv.is_price_question("Qoder Teams 多少钱"))
    check("产品定价题不触发模型校验: qoderwake", not pv.is_price_question("qoderwake 价格"))
    check("产品定价题不触发模型校验: 汉字紧贴", not pv.is_price_question("那qoder的价格呢？"))
    check("产品+模型混问仍触发（含模型名）", pv.is_price_question("qoder 和 kimi k3.1 pro 多少钱"))
    check("纯模型价格题仍触发", pv.is_price_question("qwen3.8-max 价格"))
    check("泛化价格题仍触发（无产品无模型）", pv.is_price_question("百炼怎么收费"))


def test_table_render_and_followup():
    """价格表代码渲染（排版一致性）+ 追问触发与历史模型名回退"""
    print("[1b] 标准表格渲染 / 追问触发")
    from app import price_verifier as pv

    pricing = {
        "Singapore": {
            "input": "$2",
            "output": "$6",
            "input(implicit cache)": "$0.25",
            "explicit cache creation": "$2.5",
            "explicit cache read": "$0.17",
            "input(batch file)": "$1",
        },
        "China (Beijing)": {
            "input|idle hours": "$1.6",
            "input|busy hours": "$1.65",
            "output|idle hours": "$4.8",
            "output|busy hours": "$4.951",
            "input(implicit cache)|idle hours": "$0.2",
            "input(implicit cache)|busy hours": "$0.206",
        },
    }
    tb = pv._detail_evidence("m1", "", pricing)[0]
    tb_bj = pv._detail_evidence("m1", "", pricing, "China (Beijing)")[0]
    check("节点选择: 详情页默认仅 Singapore",
          "| Singapore" in tb and "China (Beijing)" not in tb)
    check("节点选择: 详情页指定北京仅 Beijing",
          "| China (Beijing)" in tb_bj and "Singapore" not in tb_bj)
    check(
        "表头列序固定（Cache Write 在 Output 右侧）",
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) "
        "| 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |" in tb,
    )
    check("SG 行 Cache Input/Write 就位，显式读取进备注",
          "| Singapore | $2 | $0.25 | $6 | $2.5 | 显式缓存读取 $0.17 |" in tb)
    check("Batch 批次价不进备注（口径：一律忽略）", "Batch" not in tb)
    check("busy/idle 按 qualifier 拆行",
          "| China (Beijing) · idle hours | $1.6 | $0.2 | $4.8 | — | — |" in tb_bj
          and "| China (Beijing) · busy hours | $1.65 | $0.206 | $4.951 | — | — |" in tb_bj)

    hist = [
        {"role": "user", "content": "deepseek-v4.1-flash 的价格是多少？"},
        {"role": "assistant", "content": "价格如下..."},
    ]
    # v3 工具循环：“是否查价/追问锚定”由 LLM 决策，is_price_question 仅服务
    # 缺型号反问快路径；追问里含型号 → 不反问（交工具循环重查同一型号）
    check("追问含型号 → 不反问（交工具循环）",
          not pv.needs_model_clarify("qwen3.8 flash呢？"))
    check("追问'呢？'含型号仍命中价格意图（反问快路径可用）",
          pv.is_price_question("qwen3.8 flash呢？", hist))
    check("追问'呢？'无历史不触发", not pv.is_price_question("qwen3.8 flash呢？"))
    check("选型对比（无价格历史）不触发", not pv.is_price_question("qwen3.8-max 和 deepseek 哪个强"))


def test_region_fallback_and_usage_cost():
    """默认地域回退、多模态分档价与确定性账单算术回归。"""
    print("[1c] 地域回退 / 多模态价格 / token 成本计算")
    from app import price_verifier as pv, tpm_calc, tools
    import json

    embedding_html = (
        "<h4>Singapore</h4>"
        "<table><tr><th>Model ID</th><th>Input unit price (per million tokens)</th></tr>"
        "<tr><td>tongyi-embedding-vision-plus</td><td>$0.09</td></tr></table>"
        "<h4>China (Beijing)</h4>"
        "<table><tr><th>Model ID</th><th>Input unit price (per million tokens)</th></tr>"
        "<tr><td>qwen3-vl-embedding</td><td>Image/Video: $0.258 Text: $0.1</td></tr></table>"
    )
    rows = pv._parse_pricing_rows(embedding_html)
    block = pv._model_evidence(rows, "qwen3-vl-embedding", "China (Beijing)")[0]
    check("多模态价格: Image/Video 与 Text 拆成两行",
          "China (Beijing) · Image/Video | $0.258" in block
          and "China (Beijing) · Text | $0.1" in block)
    check("多模态价格: Beijing 来源带分表锚点", "#china-beijing-h4" in block)
    detail_text = (
        "original pricing for model API calls. China (Beijing) "
        "Billing Item Price (USD) Unit Image Input 0.258 Per 1M tokens "
        "Text Input 0.1 Per 1M tokens Rate Limits"
    )
    detail = pv._parse_model_pricing(detail_text)
    detail_block = pv._detail_evidence(
        "qwen3-vl-embedding", "https://example.com/model", detail, "China (Beijing)"
    )[0]
    check("多模态详情页: Image/Text 两种输入价都保留",
          "China (Beijing) · image | $0.258" in detail_block
          and "China (Beijing) · text | $0.1" in detail_block
          and "#china-beijing-h4" in detail_block)

    async def fake_pricing_html():
        return embedding_html

    async def fake_detail(*args, **kwargs):
        return ""

    async def fake_search(*args, **kwargs):
        return []

    original = pv._get_pricing_html, pv._cached_fetch, pv.web_search
    pv._get_pricing_html, pv._cached_fetch, pv.web_search = (
        fake_pricing_html, fake_detail, fake_search
    )
    try:
        fallback = asyncio.run(pv.verify_price_for("qwen3-vl-embedding"))
        explicit_sg = asyncio.run(
            pv.verify_price_for("qwen3-vl-embedding", region="Singapore")
        )
    finally:
        pv._get_pricing_html, pv._cached_fetch, pv.web_search = original
    check("默认地域: Singapore 未列出时自动回退 Beijing",
          fallback["status"] == "official" and fallback["region_fallback"]
          and fallback["region"] == "China (Beijing)"
          and "$0.258" in fallback["official_md"] and "$0.1" in fallback["official_md"])
    check("默认地域: 证据明确说明回退且链接到 Beijing 分表",
          "已自动回退 China (Beijing)" in fallback["evidence_md"]
          and any(s["url"].endswith("#china-beijing-h4") for s in fallback["sources"]))
    check("显式 Singapore: 不跨区、不把型号介绍当价格证据",
          explicit_sg["status"] != "official" and "$0.258" not in explicit_sg["official_md"]
          and "China (Beijing) |" not in explicit_sg["evidence_md"])

    # 合成大数：覆盖原始整数减法、百万换算、三个分量、小计与汇率合计。
    item = {
        "model": "qwen4-max",
        "input_tokens": "24,000,000,000",
        "cached_input_tokens": "23,000,000,000",
        "output_tokens": "300,000,000",
        "input_price_per_million": "1.5",
        "cache_input_price_per_million": "0.075",
        "output_price_per_million": "4.5",
    }
    cost_md = tpm_calc.usage_cost_md([item], region="Singapore", fx_rate="7.25")
    check("成本计算: 非缓存输入由原始整数相减", "| 1,000,000,000 | 23,000,000,000 |" in cost_md)
    check("成本计算: 三个费用分量与小计准确",
          "$1,500.00" in cost_md and "$1,725.00" in cost_md
          and "$1,350.00" in cost_md and "$4,575.00" in cost_md)
    check("成本计算: 人民币合计使用指定汇率", "¥33,168.75" in cost_md)
    try:
        tpm_calc.usage_cost_md([{**item, "input_tokens": "1", "cached_input_tokens": "2"}])
        invalid_rejected = False
    except ValueError:
        invalid_rejected = True
    check("成本计算: 缓存量大于输入总量时拒绝猜测", invalid_rejected)

    names = {t["function"]["name"] for t in tools.TOOLS}
    check("成本工具: schema 已注册", "calculate_token_cost" in names)
    tool_result = asyncio.run(tools.execute_tool(
        "calculate_token_cost",
        json.dumps({"region": "Singapore", "items": [item]}, ensure_ascii=False),
    ))
    check("成本工具: 返回独立派生证据", tool_result.get("calculated_md", "").startswith("### Token 成本测算"))
    check("成本工具: 成品表不泄漏提示词指令（硬闸门直接渲染给用户）",
          "逐字输出" not in tool_result.get("calculated_md", "")
          and "逐字输出" in tool_result.get("content", ""))
    official = (
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) |\n"
        "| Singapore | $1.5 | $0.075 | $4.5 |"
    )
    audited = pv.audit_answer_prices(
        cost_md, official + "\n" + tool_result["calculated_md"]
    )
    check("成本审计: 确定性派生费用不再误报 mismatch",
          audited["checked"] and audited["mismatched"] == [], str(audited))


def test_price_parsing_offline():
    """价格页解析：用缓存 HTML 做结构化断言（有网则抓，无网用本地缓存）"""
    print("[2] 定价页结构化解析 + 代码渲染（官方页）")
    from app import price_verifier as pv

    async def run():
        html = await pv._get_pricing_html()
        if not html:
            check("定价页获取", False, "无网且无缓存，跳过")
            return
        check("定价页获取", True)
        rows = pv._parse_pricing_rows(html)
        check(f"解析出行数 > 200（实际 {len(rows)}）", len(rows) > 200)
        regions = {r["region"] for r in rows}
        check("包含 Singapore 分表", "Singapore" in regions)
        check("包含 China (Beijing) 分表", "China (Beijing)" in regions)

        # 代码渲染表格：默认只出 Singapore，显式北京才出 Beijing。
        ds_block = pv._model_evidence(rows, "deepseek-v4.1-flash")
        ds_bj = pv._model_evidence(rows, "deepseek-v4.1-flash", "China (Beijing)")[0]
        check("deepseek-v4.1-flash 证据非空", len(ds_block) > 0)
        tb = ds_block[0] if ds_block else ""
        check("deepseek Singapore 忙时 $0.3（region/scope 归属正确）",
              "| Singapore · International · busy hours | $0.3 |" in tb, tb[:160])
        check("deepseek 默认不带 Beijing", "China (Beijing)" not in tb)
        check("deepseek 指定北京忙时 $0.283 且不带 Singapore",
              "China (Beijing) · Global · busy hours | $0.283" in ds_bj
              and "Singapore" not in ds_bj)
        check("deepseek Cache Input 主表未单列填 —（附官方规则）",
              "官方规则节选" in tb)

        # kimi: 默认 Singapore；指定北京后拆缓存列并合并重复表。
        k_tb = pv._model_evidence(rows, "kimi-k3.1-pro")[0]
        k_bj = pv._model_evidence(rows, "kimi-k3.1-pro", "China (Beijing)")[0]
        check("kimi 北京 Cache Input 拆列 $0.184（Global 档）", "| $1.837 | $0.184 |" in k_bj)
        check("kimi US scope 价不挪用（International = $2）",
              "| Singapore · International | $2 | $0.2 |" in k_tb, k_tb[:160])
        check("kimi 默认不带 Beijing", "China (Beijing)" not in k_tb)
        check("kimi BJ 重复表结构合并且不附带 Singapore",
              sum(1 for l in k_bj.splitlines() if l.startswith("| China (Beijing)")) == 2
              and "Singapore" not in k_bj)

        # qwen3.8-flash: 显式北京时多 scope 分档行保留
        q_tb = pv._model_evidence(rows, "qwen3.8-flash", "China (Beijing)")[0]
        check("qwen3.8-flash BJ 多行分档保留",
              sum(1 for l in q_tb.splitlines() if l.startswith("| China (Beijing)")) >= 2
              and "Singapore" not in q_tb)
        check("qwen3.8-flash batch 折扣行整行忽略", "Batch" not in q_tb, q_tb[:300])

        # 2026-11-09 事故：口语 token 作证据标题 → LLM 照抄并断言"模型 ID 是 kimi-k3.1"。
        # 标题与备注必须落到主表官方 ID 上。
        alias_tb = pv._model_evidence(rows, "kimi-k3.1")[0]
        check("口语型号证据标题用官方 ID（kimi-k3.1 → kimi-k3.1-pro）",
              "kimi-k3.1-pro · 官方定价页" in alias_tb, alias_tb[:120])
        check("口语型号附官方 ID 备注", "官方模型 ID：`kimi-k3.1-pro`" in alias_tb)
        ds_alias = pv._model_evidence(rows, "deepseek-v4.1")[0]
        check("裸版本号落到在售型号（deepseek-v4.1 → -flash）",
              "deepseek-v4.1-flash · 官方定价页" in ds_alias, ds_alias[:120])
        exact_tb = pv._model_evidence(rows, "qwen3.8-max")[0]
        check("精确型号不多余附加 ID 备注", "官方模型 ID" not in exact_tb)

    asyncio.run(run())


def test_knowledge_retrieval():
    """知识库检索：模型名命中 / 主题检索 / 边界容错"""
    print("[3] BM25 知识检索")
    from app import knowledge

    n = knowledge.build_default_index()
    check(f"索引构建（{n} 片段 > 500）", n > 500)

    def top_hit(q):
        hits = knowledge.get_index().search(q, top_k=1)
        return hits[0]["relpath"] if hits else ""

    check("qwen3.8-max 查询命中 maas/qwen.md", "maas/qwen.md" in top_hit("qwen3.8-max 的价格是多少"),
          top_hit("qwen3.8-max 的价格是多少"))
    check("wan3.0 查询命中 maas/wan.md", "maas/wan.md" in top_hit("Wan3.0-Video 支持哪些分辨率"),
          top_hit("Wan3.0-Video 支持哪些分辨率"))
    check("cosyvoice 查询命中 cosyvoice.md", "cosyvoice" in top_hit("cosyvoice 语音合成怎么用"))
    check("中文主题检索（Harness）命中 ai-general-notes",
          "ai-general-notes" in top_hit("什么是 Harness 评估闭环"), top_hit("什么是 Harness 评估闭环"))
    # 边界
    check("空查询不抛异常", isinstance(knowledge.get_index().search("", top_k=3), list))
    check("乱码查询不抛异常", isinstance(knowledge.get_index().search("?!@#$", top_k=3), list))

    # 2026-11-10 事故：对比题整题 BM25 被单一品牌权威文档占满（top8 全是 qwen.md），
    # 另一型号的权威文档挤不进 top-k，模型只能凭记忆写规格（把 1M 上下文答成
    # “官方未明确披露”、CED 串成 V3.2 时代的 DSA）。修复：SPARSE_DIRS 收录 knowledge/
    # 全目录 + search_with_models 按型号补检。
    check("索引含 deepseek 权威文档（knowledge/deepseek/）",
          any("knowledge/deepseek/" in c["relpath"] for c in knowledge.get_index().chunks))
    cmp_q = "qwen3.8-max 和 deepseek-v4.1-flash 哪个更适合长文本 RAG 场景？"
    base = [c["relpath"] for c in knowledge.get_index().search(cmp_q, top_k=6)]
    check("事故复现：整题检索确实被单品牌占满", all("qwen" in r for r in base), str(base[:3]))
    out = knowledge.search_with_models(cmp_q, ["deepseek-v4.1-flash", "qwen3.8-max"], top_k=6)
    check("补检后覆盖两个家族文档",
          any("deepseek" in c["relpath"] for c in out) and any("qwen" in c["relpath"] for c in out))
    check("补检条数受控（≤9）", len(out) <= 9)
    check("单型号题不重复补检（仍 6 条）",
          len(knowledge.search_with_models("qwen3.8-max 多少钱", ["qwen3.8-max"], top_k=6)) == 6)
    check("无型号题不补检",
          len(knowledge.search_with_models("你好", [], top_k=6)) <= 6)
    kimi_q = "kimi-k3.1-pro 和 qwen3.8-max 哪个适合写代码？"
    kimi_out = knowledge.search_with_models(kimi_q, ["kimi-k3.1-pro", "qwen3.8-max"], top_k=6)
    check("kimi 对比题补检命中 kimi-k-series",
          any("kimi-k-series" in c["relpath"] for c in kimi_out))


def test_store():
    """存储层：独立临时库，落库/反馈覆盖/统计/过滤/导出"""
    print("[4] SQLite 交付记录层（临时库）")
    from app import store, config

    with tempfile.TemporaryDirectory() as td:
        # patch store 内已绑定的名字（from .config import 是值绑定，patch config 无效）
        orig = store.get_db_path
        store.get_db_path = lambda: Path(td) / "t.db"
        try:
            store.init_db()
            a1 = store.insert_answer("s1", "Q1价格问题?", "A1回答", [], "official", "m", 100)
            a2 = store.insert_answer("s2", "Q2一般问题?", "A2回答", [], "", "m", 200)
            check("落库返回递增 id", a2 == a1 + 1)

            check("点赞写入", store.add_feedback(a1, "up", ""))
            check("点踩覆盖点赞（可更正）", store.add_feedback(a1, "down", "价格不对/过期"))
            check("非法 rating 拒绝", not store.add_feedback(a2, "bad", ""))

            s = store.stats()
            check("统计 total=2", s["total"] == 2, str(s))
            check("统计 down=1", s["down"] == 1)
            check("统计 official=1", s["price_official_verified"] == 1)

            downs = store.list_answers(rating="down")
            check("过滤点踩记录", len(downs) == 1 and downs[0]["feedback_reason"] == "价格不对/过期")
            ups = store.list_answers(rating="up")
            check("点赞过滤为空（已被覆盖）", len(ups) == 0)
            kw = store.list_answers(q="价格问题")
            check("关键词过滤", len(kw) == 1 and kw[0]["question"].startswith("Q1"))

            csv_text = store.export_csv()
            check("CSV 导出含全部字段", all(k in csv_text for k in ("Q1价格问题", "价格不对/过期", "official")))
        finally:
            store.get_db_path = orig


def test_guide_lookup():
    """售前指南定位：文件名日期会滚动，必须取最新一版而非硬编码。"""
    from app import guide as gd

    hit = gd.latest_guide()
    check("售前指南: 能在知识库中找到指南 HTML", hit is not None, str(gd.guide_dir()))
    if hit:
        check(
            "售前指南: 命中标准命名 ModelStudio-api-sales-guide-<YYYYMMDD>.html",
            hit.name.startswith("ModelStudio-api-sales-guide-") and hit.suffix == ".html",
            hit.name,
        )

    # 用临时目录模拟新旧版本共存 + 非 HTML 干扰项，验证取的是日期最新那个
    tmp = Path(tempfile.mkdtemp())
    d = tmp / gd.GUIDE_DIR
    d.mkdir(parents=True)
    for n in (
        "ModelStudio-api-sales-guide-20260101.html",
        "ModelStudio-api-sales-guide-20261230.html",
        "ModelStudio-api-sales-guide-20261230.png",
    ):
        (d / n).write_text("x", encoding="utf-8")
    orig = gd.knowledge.resolve_source_root
    gd.knowledge.resolve_source_root = lambda: ("local", tmp)
    try:
        pick = gd.latest_guide()
        check(
            "售前指南: 多版本共存时取文件名日期最新的",
            pick is not None and pick.name.endswith("20261230.html"),
            pick.name if pick else "None",
        )
        # 空目录 → 返回 None（路由层会退成友好提示页）
        for p in d.glob("*"):
            p.unlink()
        check("售前指南: 目录为空时返回 None 而不是报错", gd.latest_guide() is None)
    finally:
        gd.knowledge.resolve_source_root = orig


def test_model_clarify():
    """缺型号时必须反问，不能算“无证据”直接拒答（后台点踩 id=210）。"""
    from app import price_verifier as pv, prompts

    check("澄清: 只问价格没给型号 → 需要反问", pv.needs_model_clarify("新加坡节点模型价格是多少"))
    check("澄清: “给我报个价”无型号 → 需要反问", pv.needs_model_clarify("给我报个价"))
    check("澄清: 已给型号 → 不反问", not pv.needs_model_clarify("qwen3.8-max 多少钱"))
    check("澄清: 视频型号 → 不反问", not pv.needs_model_clarify("wan3.0 video 每秒多少钱"))
    check("澄清: 家族词概览 → 不反问", not pv.needs_model_clarify("qwen 多少钱"))
    check("澄清: 产品订阅价 → 不反问（交知识库）", not pv.needs_model_clarify("Qoder 多少钱"))
    check("澄清: 列举式问法 → 不反问", not pv.needs_model_clarify("百炼都有哪些模型，价格多少"))
    check(
        "澄清: 追问沿用历史型号 → 不反问",
        not pv.needs_model_clarify("这个多少钱", [{"role": "user", "content": "qwen3.8-max 多少钱"}]),
    )
    check("澄清: 非价格问题 → 不反问", not pv.needs_model_clarify("百炼支持多 Agent 协作吗"))
    check(
        "澄清话术: 不含拒答话术且给出型号格式示例",
        "暂未能联网核实" not in prompts.MODEL_CLARIFY_TEXT and "多少钱" in prompts.MODEL_CLARIFY_TEXT,
    )


def test_price_audit():
    """输出侧价格审计：回答表格里的 $ 金额必须都来自官方证据（防抄错/臆造）。"""
    print("[5] 输出侧价格审计")
    from app import price_verifier as pv

    official = (
        "#### qwen3.8-max · 模型详情页定价（每 1M tokens USD · 权威）\n"
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
        "|---|---|---|---|---|---|\n"
        "| Singapore | $2 | $0.25 | $6 | $2.5 | — |\n"
        "| China (Beijing) | $1.65 | $0.2 | $4.951 | — | — |\n"
    )

    # 数字归一
    check("金额归一: 0.040→0.04", pv._norm_amount("0.040") == "0.04")
    check("金额归一: 2.00→2", pv._norm_amount("2.00") == "2")
    check("金额归一: 整数 100 不被削尾零", pv._norm_amount("100") == "100")
    check("金额归一: 1.650→1.65", pv._norm_amount("1.650") == "1.65")

    # 逐字照抄官方表 → 通过
    ok = pv.audit_answer_prices("价格如下：\n" + official, official)
    check("审计: 逐字照抄官方表 → checked 且无 mismatch",
          ok["checked"] and ok["mismatched"] == [], str(ok))

    # 抄错一个数字（$6 写成 $82）→ mismatch
    bad = official.replace("| $6 |", "| $82 |")
    r = pv.audit_answer_prices(bad, official)
    check("审计: 抄错的价格被揪出", r["checked"] and "82" in r["mismatched"], str(r))
    check("审计: 合法价格不误报", "2" not in r["mismatched"] and "6" not in r["mismatched"], str(r))

    # 归一后相等不算 mismatch（$2 vs $2.00）
    r2 = pv.audit_answer_prices(official.replace("| $2 |", "| $2.00 |"), official)
    check("审计: 尾零差异不误报", r2["checked"] and r2["mismatched"] == [], str(r2))

    # 没有表格价格 → 无从比对（拒答/纯文字场景）
    r3 = pv.audit_answer_prices("该价格暂未能联网核实，请以官方定价页为准。", official)
    check("审计: 回答无表格价格 → 未审计", not r3["checked"], str(r3))

    # 正文里的成本测算/人民币换算不是表格单价，不应误报
    prose = (
        "按官方单价测算：\n" + official +
        "\n\n若调用 100 万次输入，约 $2 × 100 = $200；折合 ¥1334.24（汇率 6.6712）。"
    )
    r4 = pv.audit_answer_prices(prose, official)
    check("审计: 正文成本测算($200)与人民币(¥)不误报",
          r4["checked"] and r4["mismatched"] == [], str(r4))

    # 多模型成本题：显式加法小计与总计是合法派生值，不是新的官方单价。
    # 总计行允许引用前面已验证的小计；没有算式或算错仍必须报 mismatch。
    cost_official = official + "| kimi-k3.1-pro | China (Beijing) | $1.837 | $0.184 | $9.611 | — | — |\n"
    cost_answer = cost_official + (
        "| qwen3.8-max | $1.65 + $4.951 | **$6.601** |\n"
        "| kimi-k3.1-pro | $1.837 + $9.611 | **$11.448** |\n"
        "| 合计 | $6.601 + $11.448 | **$18.049** |"
    )
    r_sum = pv.audit_answer_prices(cost_answer, cost_official)
    check("审计: 显式加法小计与多模型总计不误报",
          r_sum["checked"] and r_sum["mismatched"] == [], str(r_sum))
    r_sum_bad = pv.audit_answer_prices(cost_answer.replace("$18.049", "$18.06"), cost_official)
    check("审计: 加法算错仍被揪出", "18.06" in r_sum_bad["mismatched"], str(r_sum_bad))
    r_no_formula = pv.audit_answer_prices(official + "| 合计 | **$18.049** |", cost_official)
    check("审计: 无算式的陌生合计仍被揪出",
          "18.049" in r_no_formula["mismatched"], str(r_no_formula))

    # web 旁证价不作数：只喂官方证据，回答里的 web 价应被揪出
    r5 = pv.audit_answer_prices("| Singapore | $9.99 | — | — | — | — |", official)
    check("审计: 官方证据外的价格(疑似 web/臆造)被揪出",
          r5["checked"] and "9.99" in r5["mismatched"], str(r5))

    # 媒体按秒计费表同样受审
    media_off = (
        "| 模型 (Model ID) | Region | 分辨率 | 单价 | 备注 |\n"
        "|---|---|---|---|---|\n"
        "| wan3.0-video | Singapore | 1080P | $0.28/秒 | — |\n"
    )
    rm = pv.audit_answer_prices(media_off, media_off)

    # 2026-11-10 id 72 事故：①多模型问题连调 verify_price 时 official_md 被
    # 覆盖只剩末次证据（修复在 pipeline 累加，这里断审计函数本身对累加后的
    # 多模型证据能一次通过）；②用户要求算 5.5 折时派生值被误判 mismatch。
    check("折扣率抽取: 5.5折/55%/6折", pv._discount_rates("5.5折 55% 6折") == {0.55, 0.6})
    check("折扣率抽取: 120% 越界不收", 1.2 not in pv._discount_rates("120%"))
    multi_off = (
        "| qwen-image-3.0-pro | Singapore | 1K | $0.04/张 | 输入图 $0.003/张 |\n"
        "| qwen-image-3.0-pro | China (Beijing) | 2K | $0.068761/张 | 输入图 $0.00275/张 |\n"
        "| qwen-image-2.1-pro | Singapore | 1K | $0.045/张 | — |\n"
        "| qwen-image-2.1-pro | China (Beijing) | 2K | $0.064242/张 | — |\n"
    )
    q72 = "qwen-image-3.0-pro-北京/新加坡-5.5折 qwen-image-2.1-pro 5.5折"
    a72 = (
        "| qwen-image-3.0-pro | Singapore | 1K | $0.04/张 | 输入图 $0.003/张 |\n"
        "| qwen-image-3.0-pro | Singapore | 1K | 5.5折 $0.024754/张 | — |\n"
        "| qwen-image-3.0-pro | China (Beijing) | 2K | $0.068761/张 | 输入图 $0.00275/张 |\n"
        "| qwen-image-2.1-pro | Beijing | 5.5折 $0.035333/张 | — |\n"
    )
    r72 = pv.audit_answer_prices(a72, multi_off, "", q72)
    check("审计: 多模型证据+折扣派生值不再误报（id 72）",
          r72["checked"] and r72["mismatched"] == [], str(r72))
    r72b = pv.audit_answer_prices(
        a72.replace("5.5折 ", ""), multi_off, "", "qwen-image 价格")
    check("审计: 问答均无折扣标记时派生值仍报 mismatch（保守）",
          r72b["checked"] and "0.024754" in r72b["mismatched"], str(r72b))
    r72c = pv.audit_answer_prices(
        "| m | Singapore | 5.5折 $9.9/张 |", multi_off, "", "算下5.5折")
    check("审计: 折扣场景下真错价仍被揪出",
          r72c["checked"] and "9.9" in r72c["mismatched"], str(r72c))
    check("审计: 视频按秒价照抄 → 通过", rm["checked"] and rm["mismatched"] == [], str(rm))
    rm2 = pv.audit_answer_prices(media_off.replace("$0.28", "$0.82"), media_off)
    check("审计: 视频价抄错被揪出", rm2["checked"] and "0.82" in rm2["mismatched"], str(rm2))

    # 2026-11-20 P0：官方表行级完整性审计（#197 漏 Text 行事故）
    check("用量截图题: 带图问总费用命中",
          pv.is_usage_cost_question("看看多少钱", [], has_images=True))
    check("用量截图题: 无图不命中",
          not pv.is_usage_cost_question("看看多少钱", [], has_images=False))
    check("用量截图题: 追问某一列不命中",
          not pv.is_usage_cost_question("输入价格是多少", [], has_images=True))
    # 2026-11-22 事故：“kimi-k3.1，多少钱”+用量截图被“多少钱”歧义词判成
    # 成本题，硬闸门把模型已写好的单价表替换成澄清话术（答非所问）。
    check("用量截图题: 带型号名只问单价不命中（事故复现）",
          not pv.is_usage_cost_question("kimi-k3.1，多少钱", [], has_images=True))
    check("用量截图题: 带型号名问价格不命中",
          not pv.is_usage_cost_question("kimi-k3.1-pro 价格", [], has_images=True))
    check("用量截图题: 型号名+token 数量仍命中",
          pv.is_usage_cost_question(
              "kimi-k3.1-pro 输入100万tokens、输出100万tokens，一共多少钱？",
              [], has_images=True))
    check("用量截图题: 型号名+裸 token 数量仍命中",
          pv.is_usage_cost_question(
              "kimi-k3.1-pro 100万 tokens 多少钱", [], has_images=True))
    check("用量截图题: 型号名+账单/花了仍命中",
          pv.is_usage_cost_question(
              "kimi-k3.1-pro 这个月账单花了多少钱", [], has_images=True))
    check("用量截图题: 无型号名的成本题仍命中（模型名只在图里）",
          pv.is_usage_cost_question("帮我算下这张账单的总成本", [], has_images=True))
    check("用量截图题: 当前句单价意图不被历史成本题污染",
          not pv.is_usage_cost_question(
              "kimi-k3.1，多少钱",
              [{"role": "user", "content": "帮我算下账单总成本"}], has_images=True))
    official_two = (
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
        "|---|---|---|---|---|---|\n"
        "| China (Beijing) · Image/Video | $0.258 | — | — | — | — |\n"
        "| China (Beijing) · Text | $0.1 | — | — | — | — |\n"
    )
    answer_one = (
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
        "|---|---|---|---|---|---|\n"
        "| China (Beijing) · Image/Video | $0.258 | — | — | — | — |\n"
    )
    missing = pv.audit_price_completeness(
        answer_one, official_two, "qwen3-vl-embedding 北京节点多少钱"
    )
    check("完整性审计: 漏 Text 行被揪出",
          missing["checked"] and any("Text" in row[0] for row in missing["missing_rows"]),
          str(missing))
    complete = pv.audit_price_completeness(
        official_two, official_two, "qwen3-vl-embedding 北京节点多少钱"
    )
    check("完整性审计: 全行覆盖通过",
          complete["checked"] and complete["missing_rows"] == [], str(complete))
    field_q = pv.audit_price_completeness(
        answer_one, official_two, "qwen3-vl-embedding 输入价格是多少"
    )
    check("完整性审计: 字段追问不判漏行", not field_q["checked"], str(field_q))


def test_followup_anchor_and_competitor():
    """工具循环版：竞品证据抽取/打标纯函数回归（is_table_followup/competitor_of
    已随正则路由退役，追问与竞品点名由 LLM 调 verify_price 工具时显式传参）。
    """
    print("[9] 竞品证据抽取与打标（工具循环版）")
    from app import price_verifier as pv

    # verify_price_for 归一：工具入参是模型原话，归一失败时原词直接当 token
    check("工具入参归一: 口语 'kimi k3.1 pro'",
          pv.extract_model_names("kimi k3.1 pro") == ["kimi-k3.1-pro"])
    check("工具入参归一: 非模型词原词入参不炸",
          isinstance(pv.extract_model_names("百炼"), list))

    check(
        "竞品国际站定价页已登记（腾讯云 TokenHub USD 文档）",
        any(
            "tencentcloud.com" in u
            for u in pv._COMPETITOR_OFFICIAL_PAGES.get("腾讯云混元", ())
        ),
        str(pv._COMPETITOR_OFFICIAL_PAGES),
    )
    check(
        "竞品英文检索名映射完整（工具搜索回退用）",
        set(pv._COMPETITOR_EN) == {"腾讯云混元", "火山引擎豆包", "百度智能云文心",
                                    "AWS Bedrock", "OpenAI", "Anthropic Claude",
                                    "Google Gemini", "DeepSeek 官方"},
        str(sorted(pv._COMPETITOR_EN)),
    )

    # 竞品定价表混着「对方自研」与「对方平台上架的第三方模型」，必须分账标清
    html = (
        "<table><tr><td>Model Name</td><td>Input (USD / million tokens)</td></tr>"
        "<tr><td>Hy3</td><td>$0.132</td></tr>"
        "<tr><td>DeepSeek-V4.1-Flash</td><td>$0.14</td></tr>"
        "<tr><td>GLM-5.2</td><td>$1.4</td></tr></table>"
    )
    same, other = pv._tag_and_split_rows(html, "腾讯云混元", ["deepseek-v4.1-flash"])
    check("竞品表格: 同款模型（腾讯也卖 DS）进同款组", len(same) == 1 and "同款" in same[0], str(same))
    check(
        "竞品表格: 同款行仍标明“第三方模型·对方平台价”",
        "[第三方模型·对方平台价]" in same[0],
        str(same),
    )
    check("竞品表格: 对方自研行标 [自研]", any("[自研]" in r for r in other), str(other))
    check(
        "竞品表格: 他人家模型不误标自研",
        any("GLM" in r and "[第三方模型·对方平台价]" in r for r in other),
        str(other),
    )
    same2, _ = pv._tag_and_split_rows(html, "腾讯云混元", ["qwen3.8-max"])
    check("竞品表格: 非同款→不进同款组", same2 == [], str(same2))

    # 竞品价写进回答表格，不应被判为“抄错价”
    official = "| Singapore | $2 | $0.25 | $6 | — | — |"
    competitor = "| 腾讯云混元 | $0.5 | — | $2 | — | — |"
    r_ok = pv.audit_answer_prices(competitor, official, competitor)
    check("审计: 竞品价在白名单内不误报", r_ok["checked"] and r_ok["mismatched"] == [], str(r_ok))
    r_bad = pv.audit_answer_prices(competitor, official)
    check("审计: 不传竞品白名单时竞品价被揪出", "0.5" in r_bad["mismatched"], str(r_bad))

    # 腾讯云风格的纯数字价（单位在表头），回答补 $ 后不应被判 mismatch
    tc_md = "| [第三方模型·对方平台价][同款] | DeepSeek-V4.1-Flash | - | OFF-PEAK | 0.15 | 0.6 | 0.003 | - | - |"
    r_dec = pv.audit_answer_prices("| 腾讯云 | $0.003 |", "", tc_md)
    check("审计: 竞品纯数字价补 $ 后不误报", r_dec["checked"] and r_dec["mismatched"] == [], str(r_dec))


def test_source_visibility():
    """知识库仓库公开可核对：KB 引用也对客户展示，按可信度排序。"""
    print("[6] 来源可见性与排序")
    from app import pipeline

    sources = [
        {"title": "kb", "url": "https://github.com/x/blob/main/maas/qwen.md", "kind": "knowledge"},
        {"title": "off", "url": "https://www.alibabacloud.com/help/en/model-studio/model-pricing", "kind": "official"},
        {"title": "web", "url": "https://example.com/a", "kind": "web"},
    ]
    out = pipeline.order_sources(sources)
    kinds = [s["kind"] for s in out]
    check("来源: 知识库引用不再被过滤（对客户可见）", "knowledge" in kinds, str(kinds))
    check("来源: 排序 官方 > 搜索 > 知识库",
          kinds == ["official", "web", "knowledge"], str(kinds))
    check("来源: 空列表安全", pipeline.order_sources([]) == [])
    check("来源: limit 截断", len(pipeline.order_sources(sources, limit=2)) == 2)
    # 展示上限 3（2026-11-10 用户需求）：多条来源时前端最多显示 3 条，
    # 按可信度官方>搜索>知识取前 3；落库仍是全量不受影响。
    many = [
        {"title": f"w{i}", "url": f"https://e.com/{i}", "kind": "web"} for i in range(6)
    ] + [{"title": "off", "url": "https://off.com", "kind": "official"}]
    out3 = pipeline.order_sources(many)
    check("来源: 展示上限 3 条", len(out3) == 3, str(len(out3)))
    check("来源: 官方优先占位", out3[0]["kind"] == "official", str(out3))
    # 未知 kind 排最后且不丢弃
    out2 = pipeline.order_sources([{"kind": "mystery", "url": "u"}, {"kind": "official", "url": "u2"}])
    check("来源: 未知 kind 兜底排末尾",
          [s["kind"] for s in out2] == ["official", "mystery"], str(out2))


def test_domain_gate():
    """2026-11-10 实测事故：出界题（爱情/股票）BM25 靠高频单字召出 5~6 条无关片段
    并展示为参考来源（"伊斯坦布尔有爱情么"→ 我/的/爱/斯/坦/尔 匹配 Memory-ReAct.md
    score 51，与业务题 45~103 区间重叠，分数阈值无法区分）。修法：域门控。"""
    print("[7] 出界题不检索（域门控）")
    from app import pipeline

    out_of_domain = [
        "我说的是，伊斯坦布尔有爱情么",
        "我喜欢上一个人但不敢表白，怎么办？",
        "现在A股哪些股票值得买？",
        "帮我分析下贵州茅台现在能不能抄底",
        "巴菲特的DCF估值怎么算？",
        "你好",
        "测试",
    ]
    for q in out_of_domain:
        check(f"出界不检索: {q[:16]}", not pipeline.is_domain_question(q))
    in_domain = [
        "qwen3.8-max 的价格是多少",
        "wan3.0-video 支持哪些分辨率",
        "百炼平台上怎么搭建一个多 Agent 协作的应用？",
        "qoder是怎么计费的",
        "帮我算下 100 美元是多少人民币",
        "并发能扛多少",
    ]
    for q in in_domain:
        check(f"业务题仍检索: {q[:16]}", pipeline.is_domain_question(q))
    h_price = [{"role": "user", "content": "qwen3.8-max 的价格是多少"}]
    check("追问无领域词但历史有业务题 → 检索",
          pipeline.is_domain_question("它支持视觉吗", h_price))
    h_love = [{"role": "user", "content": "我喜欢上一个人但不敢表白"}]
    check("爱情历史不误判为业务 → 不检索",
          not pipeline.is_domain_question("那工作呢", h_love))
    # 2026-11-10 追加：股票语境优先于领域关键词——“腾讯和阿里股价”里的“阿里”
    # 是公司不是阿里云，不检索本地 AI 资料，直接交工具循环联网（用户指示）。
    check("股价题含阿里关键词仍不检索", not pipeline.is_domain_question("分析下腾讯和阿里股价"))
    check("投资对比题不检索", not pipeline.is_domain_question("腾讯和阿里的股价对比，哪个更值得投资"))
    check("含型号名的投资题仍检索（AI 话题）",
          pipeline.is_domain_question("qwen3.8-max 值得投资吗"))
    check("混元话题进领域词", pipeline.is_domain_question("混元 Hy4 正式版发布了吗"))


def test_rate_limit_lookup():
    """视频/生图官方限流：HTML 解析、型号归一、类别与地域筛选（离线）。"""
    print("[8] 官方限流查询（视频/生图）")
    from app import rate_limits as rl, tools

    html = """
    <h2>图像与视频生成</h2>
    <h3>千问（Qwen-Image）</h3>
    <div id="panel-新加坡">
      <table>
        <thead>
          <tr><th>模型名称</th><th colspan="2">限流条件</th></tr>
          <tr><th>任务下发接口调用限制</th><th>同时处理中任务数量（并发数）</th></tr>
        </thead>
        <tbody>
          <tr><td>qwen-image-3.0-pro</td><td>5 次/分钟</td><td>同步接口无限制 / 异步接口 10</td></tr>
        </tbody>
      </table>
    </div>
    <div id="panel-华北2-北京">
      <table>
        <thead>
          <tr><th>模型名称</th><th colspan="2">限流条件</th></tr>
          <tr><th>任务下发接口调用限制</th><th>同时处理中任务数量（并发数）</th></tr>
        </thead>
        <tbody>
          <tr><td>qwen-image-3.0</td><td>20 次/分钟</td><td>同步接口无限制 / 异步接口 10</td></tr>
        </tbody>
      </table>
    </div>
    <h3>万相系列</h3>
    <div id="panel-新加坡">
      <table>
        <thead>
          <tr><th>模型名称</th><th colspan="2">限流条件</th></tr>
          <tr><th>每秒钟调用次数（RPS）</th><th>同时处理中任务数量（并发数）</th></tr>
        </thead>
        <tbody>
          <tr><td>wan3.0-video-prime</td><td>5</td><td>5</td></tr>
          <tr><td>wan3.0-video</td><td>5</td><td>5</td></tr>
        </tbody>
      </table>
    </div>
    """

    rows = rl.parse_rate_limit_html(html)
    check("限流解析: 4 条数据行", len(rows) == 4, str(rows))
    check("限流解析: 地域来自 tab panel",
          {r["region"] for r in rows} == {"新加坡", "华北2（北京）"},
          str({r["region"] for r in rows}))

    img = rl.lookup_rate_limits(rows, model="qwen image 3.0 pro")
    check("限流型号归一: qwen image 3.0 pro",
          img["matched_models"] == ["qwen-image-3.0-pro"], str(img["matched_models"]))
    img_md = rl.format_evidence(img, "https://example.com/rate-limit", "2026-11-10 20:00")
    check("限流证据: 生图 RPM 与异步并发原样保留",
          "任务下发接口调用限制 | 5 次/分钟" in img_md
          and "同步接口无限制 / 异步接口 10" in img_md, img_md)

    video = rl.lookup_rate_limits(rows, model="wan3.0 prime")
    check("限流型号归一: wan3.0 prime → wan3.0-video-prime",
          video["matched_models"] == ["wan3.0-video-prime"], str(video["matched_models"]))
    bare = rl.lookup_rate_limits(rows, model="wan3.0")
    check("限流泛型号: 裸 wan3.0 同时返回标准版与 Prime",
          {r["model"] for r in bare["rows"]} == {"wan3.0-video", "wan3.0-video-prime"},
          str(bare["matched_models"]))
    video_md = rl.format_evidence(video, "https://example.com/rate-limit", "2026-11-10 20:00")
    check("限流证据: 视频 RPS 与并发两项都在",
          "每秒钟调用次数（RPS） | 5" in video_md
          and "同时处理中任务数量（并发数） | 5" in video_md, video_md)
    check("限流证据: 不套用 LLM 默认额度",
          "3,000 万 TPM" not in video_md and "20,000 万 RPM" not in video_md, video_md)

    beijing = rl.lookup_rate_limits(rows, model="qwen-image-3.0", region="北京")
    check("限流地域筛选: 北京",
          bool(beijing["rows"]) and {r["region"] for r in beijing["rows"]} == {"华北2（北京）"},
          str(beijing["rows"]))

    generic = rl.lookup_rate_limits(rows, category="video")
    check("限流泛问: 未指定型号时按官方页结果返回",
          {r["model"] for r in generic["rows"]} == {"wan3.0-video", "wan3.0-video-prime"},
          str(generic["matched_models"]))
    check("限流无命中: 不编造数字，返回未找到说明",
          "官方限流页未找到" in rl.lookup_rate_limits(rows, model="not-a-model")["note"])

    names = [t["function"]["name"] for t in tools.TOOLS]
    check("限流工具已注册到 function calling", "get_model_rate_limit" in names, str(names))
    schema = next(t for t in tools.TOOLS if t["function"]["name"] == "get_model_rate_limit")
    check("限流工具: category 枚举 video/image",
          schema["function"]["parameters"]["properties"]["category"]["enum"] == ["video", "image"])


def test_asr():
    """ASR 语音识别（qwen-audio-3.1-asr-flash）：payload 构造与端点推导。"""
    print("[8] ASR payload 与端点推导")
    from app import asr

    check("ASR: 主模型 3.1 优先", asr.ASR_MODELS[0] == "qwen-audio-3.1-asr-flash")
    check("ASR: 兜底 3.0", asr.ASR_MODELS[1] == "qwen-audio-3.0-asr-flash")

    p0 = asr.build_payload("qwen-audio-3.1-asr-flash", "QUJD")
    check("ASR: 无上下文仅一条 user 音频消息", len(p0["input"]["messages"]) == 1)
    check("ASR: 音频 data URI 前缀",
          p0["input"]["messages"][0]["content"][0]["input_audio"]["data"]
          == "data:audio/wav;base64,QUJD")
    check("ASR: format/sample_rate 参数",
          p0["parameters"] == {"format": "wav", "sample_rate": 16000})

    p1 = asr.build_payload("qwen-audio-3.1-asr-flash", "QUJD", context="上一段文本")
    check("ASR: 上下文作为 assistant 消息置首",
          p1["input"]["messages"][0]["role"] == "assistant"
          and p1["input"]["messages"][0]["content"][0]["text"] == "上一段文本")
    check("ASR: 含音频的 user 消息置末",
          p1["input"]["messages"][-1]["content"][0].get("input_audio") is not None)
    # 上下文截断到 400 字符（qwen-audio 上下文增强协议限制）
    p2 = asr.build_payload("m", "QUJD", context="字" * 500)
    check("ASR: 上下文截断 400 字",
          len(p2["input"]["messages"][0]["content"][0]["text"]) == 400)

    import os
    os.environ["DASHSCOPE_BASE_URL"] = "https://llm-xxx.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    check("ASR: workspace 端点推导",
          asr._generation_endpoint().endswith("/api/v1/services/aigc/multimodal-generation/generation")
          and "/compatible-mode" not in asr._generation_endpoint())
    os.environ["DASHSCOPE_BASE_URL"] = "https://dashscope.aliyuncs.com/compatible-mode/v1"
    check("ASR: 标准域名端点推导",
          asr._generation_endpoint().startswith("https://dashscope.aliyuncs.com/api/v1/"))
    del os.environ["DASHSCOPE_BASE_URL"]


def test_pipeline_wiring():
    """端到端（mock LLM/工具/检索）：工具循环两轮接线、审计与落库一致。

    v3：mock stream_chat 第一轮产出 verify_price 工具调用，第二轮产出正文；
    mock tools.execute_tool 返回官方证据。验证：工具被执行、消息正确回填、
    done.price_audit 与落库一致、sources 同时含 knowledge 与 official。
    """
    print("[8] 管线端到端接线（mock 工具循环）")
    import types
    from app import pipeline, tools

    official = (
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
        "|---|---|---|---|---|---|\n"
        "| Singapore | $2 | $0.25 | $6 | $2.5 | — |\n"
    )

    class FakeIdx:
        def search(self, q, top_k=6):
            return [{"text": "x", "title": "qwen", "relpath": "maas/qwen.md"}]

    tool_calls_seen: list[dict] = []

    async def fake_execute_tool(name, arguments):
        tool_calls_seen.append({"name": name, "arguments": arguments})
        return {
            "content": "### 官方定价页证据（权威）\n" + official,
            "sources": [{"title": "off", "url": "https://www.alibabacloud.com/x", "kind": "official"}],
            "price_status": "official",
            "official_md": official,
            "competitor_md": "",
        }

    captured = {}

    def fake_insert(**kw):
        captured.clear()
        captured.update(kw)
        return 1

    async def drive(answer_text):
        """首轮（带工具）产出 tool_calls；拿证据后的轮次产出正文。"""
        call_args_seen: list[list[dict]] = []

        async def fake_stream(messages, tools=None, **kw):
            call_args_seen.append([dict(m) for m in messages])
            if tools and len(call_args_seen) == 1:
                yield ("think", "需要查价")
                yield (
                    "tool_calls",
                    [{"id": "call_0", "name": "verify_price",
                      "arguments": '{"model": "qwen3.8-max"}'}],
                )
            else:
                yield ("text", answer_text)

        pipeline.stream_chat = fake_stream
        evs = []
        async for ev in pipeline.stream_answer("qwen3.8-max 价格", [], "s1"):
            evs.append(ev)
        return evs, call_args_seen

    saved = {k: getattr(pipeline, k) for k in
             ("get_index", "stream_chat", "is_price_question",
              "needs_model_clarify", "store", "fx")}
    saved_tool = tools.execute_tool
    pipeline.get_index = lambda: FakeIdx()
    pipeline.is_price_question = lambda q, h=None: True
    pipeline.needs_model_clarify = lambda q, h=None: False
    pipeline.store = types.SimpleNamespace(insert_answer=fake_insert)
    pipeline.fx = types.SimpleNamespace(
        is_fx_question=lambda q: False, is_pure_rate_query=lambda q: False
    )
    tools.execute_tool = fake_execute_tool
    try:
        # 照抄官方表 → 工具被调、审计 ok、落库一致
        evs, call_args = asyncio.run(drive("价格如下：\n" + official))
        done = next(e for e in evs if e["type"] == "done")
        srcs = [e for e in evs if e["type"] == "sources"]
        check("接线: verify_price 工具被调用",
              tool_calls_seen and tool_calls_seen[0]["name"] == "verify_price",
              str(tool_calls_seen))
        check("接线: 共两轮 LLM 调用（工具轮+收尾轮）", len(call_args) == 2, str(len(call_args)))
        check("接线: 第二轮消息含 assistant(tool_calls) 与 role:tool 回填",
              any(m.get("role") == "tool" for m in call_args[1])
              and any(m.get("tool_calls") for m in call_args[1]),
              str([m.get("role") for m in call_args[1]]))
        check("接线: 最后一轮不带 tools（强制收尾，tools=None）",
              len(call_args) == 2, "fake_stream 靠 tools 分流，若第三轮仍带工具会再发起调用")
        check("接线: 照抄 → done.price_audit=ok", done.get("price_audit") == "ok", str(done))
        check("接线: done.price_status=official", done.get("price_status") == "official", str(done))
        check("接线: 落库 price_audit 与 done 一致", captured.get("price_audit") == "ok")
        all_src = [s for e in srcs for s in e["sources"]]
        check("接线: sources 事件含知识库引用",
              any(s["kind"] == "knowledge" for s in all_src))
        check("接线: 工具来源随第二次 sources 事件下发",
              any(s["kind"] == "official" for s in all_src))
        tool_status = [e for e in evs if e.get("stage") == "tool"]
        check("接线: 工具执行推送 status 事件", len(tool_status) == 1, str(tool_status))

        # 抄错价格 → done.price_audit=mismatch:82
        tool_calls_seen.clear()
        evs2, _ = asyncio.run(drive(official.replace("| $6 |", "| $82 |")))
        done2 = next(e for e in evs2 if e["type"] == "done")
        check("接线: 抄错 → done.price_audit=mismatch",
              done2.get("price_audit") == "mismatch:82", str(done2))
        check("接线: mismatch 落库一致", captured.get("price_audit") == "mismatch:82")
    finally:
        for k, v in saved.items():
            setattr(pipeline, k, v)
        tools.execute_tool = saved_tool


def test_pipeline_usage_cost_gate():
    """用量截图成本题：只开放核价/计算/汇率，必须走到 calculate_token_cost。

    mock 第一轮 verify_price、第二轮 calculate_token_cost；拿到 calculated_md 后
    应提前收尾，不再进入自由文本生成轮，最终答案由代码直接输出成品表。
    """
    print("[8b] 用量截图成本题硬闸门（mock 工具循环）")
    import types
    from app import pipeline, tools

    official = (
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) | 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |\n"
        "|---|---|---|---|---|---|\n"
        "| Singapore | $1.5 | $0.075 | $4.5 | $1.875 (5m) / $3 (1h) | — |"
    )
    calculated = (
        "### Token 成本测算（Singapore · 确定性计算）\n\n"
        "| 模型 | 非缓存输入 tokens | 缓存输入 tokens | 输出 tokens | 非缓存输入费用 (USD) |"
        " 缓存输入费用 (USD) | 输出费用 (USD) | 小计 (USD) |\n"
        "|---|---:|---:|---:|---:|---:|---:|---:|\n"
        "| qwen4-max | 465,468,500 | 23,953,611,124 | 344,621,570 |"
        " $698.20 | $1,796.52 | $1,550.80 | $4,045.52 |"
    )

    class FakeIdx:
        def search(self, q, top_k=6):
            return [{"text": "x", "title": "qwen", "relpath": "maas/qwen.md"}]

    stream_calls: list[dict] = []
    captured: dict = {}

    async def fake_stream(messages, tools=None, **kw):
        stream_calls.append({"messages": [dict(m) for m in messages], "tools": tools})
        if len(stream_calls) == 1:
            yield ("think", "先核价")
            yield (
                "tool_calls",
                [{"id": "call_0", "name": "verify_price",
                  "arguments": '{"model": "qwen4-max"}'}],
            )
        elif len(stream_calls) == 2:
            yield ("think", "再计算")
            yield (
                "tool_calls",
                [{"id": "call_1", "name": "calculate_token_cost",
                  "arguments": '{"region": "Singapore", "items": []}'}],
            )
        else:
            yield ("text", "不应到达的自由文本")

    async def fake_execute_tool(name, arguments):
        if name == "verify_price":
            return {
                "content": "### 官方定价页证据（权威）\n" + official,
                "sources": [{"title": "off", "url": "https://x", "kind": "official"}],
                "price_status": "official",
                "official_md": official,
                "competitor_md": "",
            }
        if name == "calculate_token_cost":
            return {"content": calculated, "calculated_md": calculated}
        return {"content": ""}

    def fake_insert(**kw):
        captured.clear()
        captured.update(kw)
        return 1

    saved = {k: getattr(pipeline, k) for k in ("get_index", "stream_chat", "store")}
    saved_tool = tools.execute_tool
    pipeline.get_index = lambda: FakeIdx()
    pipeline.stream_chat = fake_stream
    pipeline.store = types.SimpleNamespace(insert_answer=fake_insert)
    tools.execute_tool = fake_execute_tool
    async def drive():
        evs = []
        async for ev in pipeline.stream_answer(
            "看看多少钱", [], "cost-session",
            images=["data:image/png;base64,xxx"],
        ):
            evs.append(ev)
        return evs

    try:
        evs = asyncio.run(drive())
    finally:
        for k, v in saved.items():
            setattr(pipeline, k, v)
        tools.execute_tool = saved_tool

    deltas = "".join(e["text"] for e in evs if e["type"] == "delta")
    done = next(e for e in evs if e["type"] == "done")
    tool_names = {
        t["function"]["name"]
        for t in (stream_calls[0]["tools"] or [])
    }
    trace_names = [t["name"] for t in captured.get("tool_trace", [])]

    check("成本闸门: system prompt 附加硬约束",
          "用量截图测算" in stream_calls[0]["messages"][0]["content"],
          stream_calls[0]["messages"][0]["content"][:200])
    check("成本闸门: 只开放核价/计算/汇率工具",
          tool_names == {"verify_price", "calculate_token_cost", "get_fx_rate"},
          str(tool_names))
    check("成本闸门: 必须走到 calculate_token_cost",
          trace_names == ["verify_price", "calculate_token_cost"], str(trace_names))
    check("成本闸门: 拿到成品表后提前收尾（不进自由文本轮）",
          len(stream_calls) == 2, str(len(stream_calls)))
    check("成本闸门: 最终答案由代码直接渲染成品表",
          "按官方单价与原始整数 tokens 计算" in deltas and "$4,045.52" in deltas,
          deltas[:300])
    check("成本闸门: 不输出自由文本成本",
          "不应到达的自由文本" not in deltas and "不应到达的自由文本" not in captured.get("answer", ""),
          captured.get("answer", "")[:300])
    check("成本闸门: image_count 落库", captured.get("image_count") == 1)
    check("成本闸门: done 仍携带审计状态", done.get("price_status") == "official", str(done))


def test_store_price_audit():
    """price_audit 列：新库写入、老库自动迁移、统计/导出。"""
    print("[7] price_audit 存储与迁移")
    import sqlite3
    from app import store

    with tempfile.TemporaryDirectory() as td:
        orig = store.get_db_path
        store.get_db_path = lambda: Path(td) / "t.db"
        try:
            store.init_db()
            a1 = store.insert_answer("s1", "Q1", "A1", [], "official", "m", 100,
                                     price_audit="mismatch:0.82")
            store.insert_answer("s2", "Q2", "A2", [], "official", "m", 100,
                                price_audit="ok")
            store.insert_answer("s3", "Q3", "A3", [], "", "m", 100)
            trace = [{"name": "calculate_token_cost", "arguments": "{}",
                      "status": "ok", "latency_ms": 12}]
            hist = [{"role": "user", "content": "看看多少钱"}]
            a4 = store.insert_answer("s4", "Q4", "A4", [], "official", "m", 100,
                                     tool_trace=trace, history=hist, image_count=1)
            s = store.stats()
            check("price_audit: 统计 mismatch 计数=1", s.get("price_audit_mismatch") == 1, str(s))
            items = {it["id"]: it for it in store.list_answers()}
            check("price_audit: 落库值可回读", items[a1]["price_audit"] == "mismatch:0.82")
            check("price_audit: 未审计默认空串", items[a1 + 2]["price_audit"] == "")
            check("审计列: tool_trace_json 可回读",
                  json.loads(items[a4]["tool_trace_json"])[0]["name"] == "calculate_token_cost",
                  str(items[a4].get("tool_trace_json")))
            check("审计列: history_json 可回读",
                  json.loads(items[a4]["history_json"])[0]["content"] == "看看多少钱",
                  str(items[a4].get("history_json")))
            check("审计列: image_count 可回读", items[a4]["image_count"] == 1)
            csv_text = store.export_csv()
            check("price_audit: CSV 含表头与值",
                  "price_audit" in csv_text and "mismatch:0.82" in csv_text)
            check("审计列: CSV 含工具轨迹与图片数",
                  "tool_trace" in csv_text and "image_count" in csv_text
                  and "calculate_token_cost" in csv_text)
        finally:
            store.get_db_path = orig

    # 老库（无 price_audit 列）→ init_db 自动 ALTER TABLE 补列
    with tempfile.TemporaryDirectory() as td:
        dbp = Path(td) / "old.db"
        conn = sqlite3.connect(dbp)
        conn.execute(
            "CREATE TABLE answers (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " session_id TEXT, question TEXT, answer TEXT, sources_json TEXT,"
            " price_status TEXT, llm_model TEXT, latency_ms INTEGER, created_at TEXT,"
            " feedback TEXT, feedback_reason TEXT, feedback_at TEXT)"
        )
        conn.commit()
        conn.close()
        orig = store.get_db_path
        store.get_db_path = lambda: dbp
        try:
            store.init_db()  # 应补 price_audit / thinking / client_ip / 审计列等
            aid = store.insert_answer("s", "Q", "A", [], "official", "m", 1,
                                      price_audit="mismatch:1.23")
            row = store.list_answers()[0]
            check("price_audit: 老库迁移后可写可读",
                  row["id"] == aid and row["price_audit"] == "mismatch:1.23", str(row))
            check("审计列: 老库迁移后默认值",
                  row["tool_trace_json"] == "[]" and row["history_json"] == "[]"
                  and row["image_count"] == 0, str(row))
        finally:
            store.get_db_path = orig


def test_fx():
    """实时汇率：解析、意图识别、用户自报优先（踩记录 id=225~230）。"""
    from app import fx

    sina = 'var hq_str_USDCNY="17:49:00,6.6711,6.6713,6.6722,40,6.6700,6.6720,6.6680,6.6713,人民币,2026-11-06";'
    fxrate = 'var hq_str_fx_susdcny="17:49:00,6.6711,6.6713,6.6680,40.0,6.6700,6.6720";'
    check("汇率解析: 新浪 USDCNY 取买卖中间价", abs((fx.parse_sina(sina) or 0) - 6.6712) < 1e-6, str(fx.parse_sina(sina)))
    check("汇率解析: 新浪 fx_susdcny 同格式", abs((fx.parse_sina(fxrate) or 0) - 6.6712) < 1e-6)
    check("汇率解析: 非报价响应返回 None", fx.parse_sina('v_pv_none_match="1";') is None)
    qq = 'v_whUSDCNY="310~人民币~USDCNY~6.6710~0~20261106210926~6.6680~6.6700";'
    check("汇率解析: 腾讯 whUSDCNY 取当前价", abs((fx.parse_qq(qq) or 0) - 6.671) < 1e-6, str(fx.parse_qq(qq)))
    check("汇率解析: 腾讯非报价响应返回 None", fx.parse_qq('v_pv_none_match="1";') is None)
    check(
        "汇率解析: CFETS 中间价取 records[0]",
        abs((fx.parse_chinamoney({"records": [{"date": "2026-11-06", "values": ["6.7168"]}]}) or 0) - 6.7168) < 1e-6,
    )
    check("汇率解析: 超区间值被丢弃", fx.parse_sina('var hq_str_USDCNY="1,240,240,1";') is None)
    check(
        "汇率兜底源: exchangerate-api JSON",
        abs((fx.parse_exchangerate_api({"rates": {"CNY": 7.0712}}) or 0) - 7.0712) < 1e-6,
    )
    check("汇率意图: 查询实时汇率命中", fx.is_fx_question("查询下实时汇率"))
    check("汇率意图: 兑人民币命中", fx.is_fx_question("1.65 美金兑人民币多少"))
    check("汇率意图: 普通价格题不误触", not fx.is_fx_question("qwen3.8-max 多少钱"))
    check(
        "汇率意图: 币种共现但无“汇率”字样也要触发",
        fx.is_fx_question("北京的1.65美金相当于12RMB*0.45的几折？"),
    )
    check("汇率意图: 只提美元不算汇率题", not fx.is_fx_question("qwen3.8-max 的美元价格"))
    check("纯查汇率: 能走直接回答", fx.is_pure_rate_query("查询下实时汇率"))
    check("纯查汇率: 带计算不定为纯查询", not fx.is_pure_rate_query("1.65 美金按汇率是多少人民币 12 元打几折"))
    # v3：用户自报汇率交工具循环处理（模型按 prompt 规则以用户为准），
    # user_given_rate 已删；这里验证快路径不会把带计算的问法当成纯查询直答
    check("纯查汇率: 自报汇率+计算不走快路径",
          not fx.is_pure_rate_query("实时汇率是6.6704，1.65美元是多少人民币"))
    ev = fx.evidence_md({"rate": 6.6712, "source": "新浪财经", "at": "2026-11-06T17:49:00+08:00"})
    check("汇率证据: 含汇率与换算规则", "6.6712" in ev and "换算规则" in ev)
    check("汇率直接回答: 给出汇率与来源", "6.6712" in fx.direct_answer({"rate": 6.6712, "source": "新浪财经", "at": "2026-11-06T17:49:00+08:00"}))


def test_vendor_report():
    """供应商报告解析器：阻塞判定/证据提取/非阻塞排除/消息组装（离线合成 fixture）"""
    from app import vendor_report as vr

    fixture = (
        '<div class="overview-item"><span class="overview-label">模型 ID</span>'
        '<span class="overview-value">test-model</span></div>'
        '<div class="overview-item"><span class="overview-label">平台 / 供应商</span>'
        '<span class="overview-value">Aliyun(hk)</span></div>'
        '<summary class="template-group-heading"><strong>标准模版</strong>'
        '<span class="status bad">阻塞性 · 必须全部通过</span><span>通过 1 / 2</span></summary>'
        '<div class="case-group-heading"><strong>缓存检测</strong><span>2 个用例</span></div>'
        '<details class="case"><span class="name">用例A缓存</span>'
        '<span class="status bad">未通过 · 通过率 0%</span>'
        '<h5>请求体</h5><pre>{&quot;model&quot;:&quot;test-model&quot;,'
        '&quot;prompt_cache_options&quot;:{&quot;ttl&quot;:&quot;1H&quot;}}</pre>'
        '<h5>响应体</h5><pre>{&quot;usage&quot;:{&quot;prompt_tokens_details&quot;:{&quot;cached_tokens&quot;:0}}}</pre>'
        '<h5>断言</h5><ul class="asserts"><li class="bad">[失败] cache_write_tokens 缺失</li></ul>'
        '</details>'
        '<details class="case"><span class="name">用例B通过</span>'
        '<span class="status ok">通过 · 通过率 100%</span>'
        '<h5>断言</h5><ul class="asserts"><li class="ok">[通过] http_status 200</li></ul>'
        '</details>'
        '<summary class="template-group-heading"><strong>思考开关</strong>'
        '<span class="status ok">拓展能力 · 仅统计</span><span>通过 0 / 1</span></summary>'
        '<details class="case"><span class="name">非阻塞思考</span>'
        '<span class="status bad">未通过</span>'
        '<h5>断言</h5><ul class="asserts"><li class="bad">[失败] reasoning_content 意外存在</li></ul>'
        '</details>'
    )
    p = vr.parse_report(fixture)
    check("报告解析: meta 模型ID", p["meta"].get("模型 ID") == "test-model")
    check("报告解析: meta 平台", p["meta"].get("平台 / 供应商") == "Aliyun(hk)")
    check("报告解析: 阻塞组计数 1/2", p["stats"]["blocking_passed"] == 1 and p["stats"]["blocking_total"] == 2)
    check("报告解析: 仅阻塞组失败计入", p["stats"]["failure_count"] == 1)
    check("报告解析: 失败用例名", p["blocking_failures"][0]["name"] == "用例A缓存")
    check("报告解析: 非阻塞失败被排除", all(f["name"] != "非阻塞思考" for f in p["blocking_failures"]))
    check("报告解析: 失败断言原文", "cache_write_tokens" in p["blocking_failures"][0]["failed_assertions"][0])
    check("报告解析: 请求保留关键参数", "1H" in p["blocking_failures"][0]["request"] and "prompt_cache_options" in p["blocking_failures"][0]["request"])
    check("报告解析: 响应保留 usage", "cached_tokens" in p["blocking_failures"][0]["response"])
    bg = {g["name"]: g["blocking"] for g in p["groups"]}
    check("报告解析: 阻塞标志正确", bg.get("标准模版") is True and bg.get("思考开关") is False)
    check("报告解析: 概览含模型与计数", "test-model" in vr.summary_text(p) and "1/2" in vr.summary_text(p))
    msgs = vr.build_messages(p)
    check("报告解析: 消息组装 system+user", len(msgs) == 2 and msgs[0]["role"] == "system" and msgs[1]["role"] == "user")
    check("报告解析: 方法论入 system", "三层核对" in msgs[0]["content"])
    check("报告解析: 证据入 user", "用例A缓存" in msgs[1]["content"])
    check("报告解析: 空报告零失败", vr.parse_report("")["stats"]["failure_count"] == 0)
    only_nb = fixture.split('<summary class="template-group-heading"><strong>思考开关')[1]
    only_nb = '<summary class="template-group-heading"><strong>思考开关' + only_nb
    check("报告解析: 纯非阻塞报告零失败", vr.parse_report(only_nb)["stats"]["failure_count"] == 0)


def test_vendor_report_generality():
    """通用性加固：请求保留所有顶层参数(新模型 novel 参数不丢)+知识卡分厂商覆盖+格式守卫"""
    from app import vendor_report as vr
    # 含旧白名单外的新模型参数（Qwen enable_search / GLM do_sample / top_p / 自定义）
    req = ('{"model":"qwen4.0","enable_search":true,"do_sample":false,"top_p":0.8,'
           '"custom_flag":"x","messages":[{"role":"user","content":"hi"}],'
           '"tools":[{"function":{"name":"f1"}},{"function":{"name":"f2"}}]}')
    comp = vr._compact_request(req)
    check("通用: 保留 enable_search", "enable_search" in comp)
    check("通用: 保留 do_sample", "do_sample" in comp)
    check("通用: 保留 top_p", "top_p" in comp)
    check("通用: 保留 novel custom_flag", "custom_flag" in comp)
    check("通用: tools 收敛计数+名称", "tools_count" in comp and "f1" in comp)
    check("通用: messages 仍预览", "user" in comp)
    # 超长字符串值截断（避免单个大参数挤占上下文）
    lc = vr._compact_request('{"model":"m","big":"' + ("A" * 500) + '"}')
    check("通用: 超长字符串截断", len(lc) < 400 and "…" in lc)
    # 知识卡分厂商覆盖 + 通用方法论声明
    sp = vr.REPORT_SYSTEM_PROMPT
    check("知识卡: 含 Qwen 段", "Qwen" in sp and "enable_search" in sp)
    check("知识卡: 含 GLM 段", "GLM" in sp and "finish_reason" in sp)
    check("知识卡: 含 DeepSeek 段", "DeepSeek" in sp)
    check("知识卡: 非穷举+厂商识别声明", "非穷举" in sp and "厂商识别" in sp)
    # 格式守卫：含标记但无有效分组 → groups 空（server 据此提示格式不识别）
    check("格式守卫: 残缺报告 groups 空", vr.parse_report('<summary class="template-group-heading">残缺</summary>')["groups"] == [])
    # focus：用户随报告上传的补充关注点注入 user 消息
    pmin = {"meta": {"模型 ID": "m"}, "stats": {"blocking_passed": 0, "blocking_total": 1, "failure_count": 1},
            "blocking_failures": [{"name": "c", "top_group": "g", "sub_group": "s",
                                   "failed_assertions": [], "request": "", "response": ""}], "groups": []}
    mf = vr.build_messages(pmin, "重点看缓存命中")
    check("focus: 注入用户关注点", "重点看缓存命中" in mf[1]["content"] and "用户补充关注点" in mf[1]["content"])
    check("focus: 空 focus 不注入", "用户补充关注点" not in vr.build_messages(pmin)[1]["content"])


def test_ecs_price():
    """ECS 服务器询价：归一/请求结构/证据渲染/快路径排除（不联网）"""
    print("[19] ECS 服务器询价")
    from app import ecs_price as ep
    from app import price_verifier as pv
    from app import tools

    # 型号/地域归一
    check("ECS 型号归一: 补 ecs. 前缀", ep.normalize_instance("g9i.large") == "ecs.g9i.large")
    check("ECS 型号归一: 大写/裸金属", ep.normalize_instance("ECS.EBMG9AE.48XLARGE") == "ecs.ebmg9ae.48xlarge")
    check("ECS 型号归一: 缺规格段拒绝", ep.normalize_instance("g9i") is None)
    check("ECS 地域归一: 乌兰察布", ep.normalize_region("乌兰察布") == ("cn-wulanchabu", "华北6（乌兰察布）"))
    check("ECS 地域归一: 香港/HK/id", ep.normalize_region("HK")[0] == "cn-hongkong" and ep.normalize_region("cn-hongkong")[0] == "cn-hongkong")
    check("ECS 地域归一: 未知拒绝", ep.normalize_region("火星") is None)

    # 地域动态兜底：纯函数匹配 + mock 拉取（不联网）
    entries = [("ap-southeast-8", "马来西亚（柔佛州）"),
               ("ap-southeast-3", "马来西亚（吉隆坡）"),
               ("ap-southeast-7", "泰国（曼谷）")]
    check("ECS 动态地域: id 精确命中", ep._match_region("ap-southeast-7", entries) == ("ap-southeast-7", "泰国（曼谷）"))
    check("ECS 动态地域: 包含匹配 曼谷", ep._match_region("曼谷", entries) == ("ap-southeast-7", "泰国（曼谷）"))
    check("ECS 动态地域: 多命中返候选不猜", ep._match_region("马来西亚", entries) == entries[:2])
    check("ECS 动态地域: 未命中返 None", ep._match_region("火星", entries) is None)

    # getCommodity 地域表解析：POC/单测地域过滤
    sample = {"data": {"components": {"vm_region_no": {"vm_region_no": [
        {"value": "ap-southeast-8", "text": "马来西亚（柔佛州）"},
        {"value": "cn-wulanchabu-acdr-ut-1", "text": "China (Ulanqab) POC"},
        {"value": "ap-southeast-7-oxs", "text": "Thailand (Bangkok) OXS"},
        {"value": "", "text": "脏数据"},
    ]}}}}
    check("ECS 地域解析: 正常抽取+POC/OXS/脏数据过滤",
          ep._parse_region_entries(sample) == [("ap-southeast-8", "马来西亚（柔佛州）")])
    check("ECS 地域解析: 空响应不炸", ep._parse_region_entries({}) == [])

    fetch_calls = []

    async def fake_fetch(client):
        fetch_calls.append(1)
        return entries
    orig_fetch = ep._fetch_region_entries
    ep._fetch_region_entries = fake_fetch
    ep._region_entries, ep._region_cache_ts = [], 0.0
    try:
        async def resolve(raw):
            return await ep._resolve_region_dynamic(raw, None)
        check("ECS 动态兜底: 静态未命中→拉取匹配", asyncio.run(resolve("曼谷")) == ("ap-southeast-7", "泰国（曼谷）"))
        check("ECS 动态兜底: 缓存生效不重拉", asyncio.run(resolve("柔佛州"))[0] == "ap-southeast-8" and len(fetch_calls) == 1)
        try:
            asyncio.run(resolve("马来西亚"))
            check("ECS 动态兜底: 多命中招 LookupError", False)
        except LookupError as e:
            check("ECS 动态兜底: 多命中招 LookupError", "吉隆坡" in str(e) and "柔佛" in str(e))
        try:
            asyncio.run(resolve("火星"))
            check("ECS 动态兜底: 真不存在招 LookupError", False)
        except LookupError as e:
            check("ECS 动态兜底: 真不存在招 LookupError", "未找到" in str(e))
    finally:
        ep._fetch_region_entries = orig_fetch
        ep._region_entries, ep._region_cache_ts = [], 0.0

    # 请求结构两个必踩坑：family 属性 + vm_os 组件
    body = ep._build_body("ecs.g9i.large", "cn-wulanchabu", 1, 0)
    comps = {c["componentCode"]: c for c in body["configurations"][0]["components"]}
    it_props = {p["code"]: p["value"] for p in comps["instance_type"]["instanceProperty"]}
    check("ECS 请求: instance_type_family 必带", it_props.get("instance_type_family") == "ecs.g9i")
    check("ECS 请求: vm_os 组件必带", "vm_os" in comps)
    check("ECS 请求: 默认无盘", "systemdisk" not in comps)
    check("ECS 请求: 含盘时带 systemdisk",
          "systemdisk" in {c["componentCode"] for c in ep._build_body("ecs.g9i.large", "cn-wulanchabu", 1, 40)["configurations"][0]["components"]})

    # 证据渲染（mock 询价与规格目录，不联网）：数字与审计白名单闭环
    async def fake_query(client, instance, region_id, duration, disk_gib):
        base = {"instance_type": 32.29 if duration == 1 else 271.25}
        if disk_gib:
            base["systemdisk"] = 6.69 if duration == 1 else 74.28
        return base

    async def fake_catalog(client):
        return {"ecs.g9i.large": {"cpuCoreCount": 2, "memorySize": "8",
                                   "physicalProcessorModel": "Intel(R) Xeon(R) 6982P-C"}}
    orig, orig_cat = ep._query_one, ep._fetch_spec_catalog
    ep._query_one, ep._fetch_spec_catalog = fake_query, fake_catalog
    try:
        r = asyncio.run(ep.query_ecs_price("g9i.large", "乌兰察布"))
        md = r.get("evidence_md", "")
        check("ECS 证据: 月度刊例价 $32.29 两位小数", "$32.29" in md and "$32.290" not in md)
        check("ECS 证据: 年度成本×12 代码预算", "$387.48" in md)
        check("ECS 证据: 配置列换行 vCPU/内存+CPU型号", "2 vCPU / 8 GiB<br>Intel Xeon 6982P-C" in md)
        check("ECS 证据: 规格与地域换行", "ecs.g9i.large<br>华北6（乌兰察布）" in md)
        check("ECS 证据: 四列表头", "| 规格 · 地域 | 配置 | 月度刊例价 | 年度成本（×12） |" in md)
        check("ECS 证据: 包年实付与折合月价入说明", "$271.25" in md and "$22.60" in md)
        check("ECS 证据: 附计算器链接", ep.CALCULATOR_URL in md)
        check("ECS 证据: sources 为 official", r["sources"][0]["kind"] == "official")
        audit = pv.audit_answer_prices(md, md)
        check("ECS 审计: 逐字搬运无 mismatch", audit["checked"] and not audit["mismatched"])
        r_disk = asyncio.run(ep.query_ecs_price("ecs.g9i.large", "乌兰察布", 40))
        check("ECS 证据: 含盘合计代码预算", "$38.98" in r_disk["evidence_md"])
    finally:
        ep._query_one, ep._fetch_spec_catalog = orig, orig_cat
    # 配置列：目录优先，缺失时后缀降级，判不出不猜
    amd = {"cpuCoreCount": 8, "memorySize": "16", "physicalProcessorModel": "AMD EPYC 9T95 192-Core"}
    check("ECS 配置列: 目录含 AMD 型号换行", ep._spec_cell("ecs.c9ae.2xlarge", amd) == "8 vCPU / 16 GiB<br>AMD EPYC 9T95 192-Core")
    check("ECS 配置列: 小数内存去尾零", ep._spec_cell("ecs.t1.xsmall", {"cpuCoreCount": 1, "memorySize": "0.5"}).startswith("1 vCPU / 0.5 GiB"))
    check("ECS 配置列: 目录缺失降级倚天", "倚天" in ep._spec_cell("ecs.c8y.4xlarge", None))
    check("ECS 配置列: 未知后缀不猜厂商", ep._spec_cell("ecs.sn1ne.large", None) == "—")
    err = asyncio.run(ep.query_ecs_price("bad-spec", "乌兰察布"))
    check("ECS 错误路径: 非法型号不联网直接引导", "error" in err)

    # 快路径排除守卫（正负例成对：ECS 题不被缺型号反问劫持，本职反问不受影响）
    check("ECS 守卫: 入口 chip 问法不反问", not pv.needs_model_clarify("乌兰察布 ecs.g9i.large 服务器包月多少钱？"))
    check("ECS 守卫: 裸规格口语不反问", not pv.needs_model_clarify("g9i.large 乌兰察布多少钱"))
    check("ECS 守卫: 泛问服务器不反问", not pv.needs_model_clarify("阿里云服务器多少钱"))
    check("分享守卫: 报价出链接不反问", not pv.needs_model_clarify("把刚才两个报价生成一个可转发的链接，方便我发给客户"))
    check("ECS 守卫: 模型缺型号仍反问", pv.needs_model_clarify("新加坡节点模型价格是多少"))
    check("ECS 守卫: 百炼计费仍反问", pv.needs_model_clarify("百炼怎么收费"))

    # 检索门控：纯 ECS 询价不检索 maas（无关引用噪声），混合题/新话题仍检索
    from app import pipeline as pl
    h_ecs = [{"role": "user", "content": "乌兰察布 ecs.g9i.large 服务器包月多少钱？"},
             {"role": "assistant", "content": "$32.29/月"}]
    check("ECS 门控: 裸规格询价不检索", pl.is_ecs_price_only("g9i.4xlarge 新加坡多少钱"))
    check("ECS 门控: chip 问法不检索", pl.is_ecs_price_only("乌兰察布 ecs.g9i.large 服务器包月多少钱？"))
    check("ECS 门控: 省略追问不检索", pl.is_ecs_price_only("那香港的 ebmg9ae.48xlarge 呢？", h_ecs))
    check("ECS 门控: 报价出链接不检索", pl.is_ecs_price_only("把刚才两个报价生成一个可转发的链接", h_ecs))
    check("ECS 门控: 模型价格仍检索", not pl.is_ecs_price_only("qwen3.8-max 多少钱", h_ecs))
    check("ECS 门控: 模型话题仍检索", not pl.is_ecs_price_only("视频模型多少钱", h_ecs))
    check("ECS 门控: 混合题仍检索", not pl.is_ecs_price_only("ECS 上部署大模型怎么选，多少钱"))
    check("ECS 门控: 非价格 ECS 题仍检索", not pl.is_ecs_price_only("ecs.g9i 支持哪些地域"))

    # 工具注册
    names = {t["function"]["name"] for t in tools.TOOLS}
    check("ECS 工具: schema 已注册", "get_ecs_price" in names)
    schema = next(t["function"] for t in tools.TOOLS if t["function"]["name"] == "get_ecs_price")
    check("ECS 工具: 必填 instance_type+region", set(schema["parameters"]["required"]) == {"instance_type", "region"})
    check("ECS 工具: 状态提示已配", "ECS" in tools.status_of("get_ecs_price"))

    # ECS 分享卡片：汇总计算/换行渲染/全链路 mock（不联网不传 OSS）
    from app import share_card as sc
    mk = lambda inst, label, c1, c12, qty: {
        "ok": True, "instance": inst, "region_label": label,
        "spec": "2 vCPU / 8 GiB<br>Intel", "compute1": c1, "compute12": c12,
        "avg12": round(c12 / 12, 2), "disk1": 0.0, "disk_gib": 0, "quantity": qty}
    quote = sc.build_ecs_quote_md([mk("ecs.a.large", "柔佛", 100.0, 800.0, 17),
                                   mk("ecs.b.large", "乌兰察布", 50.0, 400.0, 12)])
    check("ECS 卡片: 月度总计代码计算", "$2,300.00" in quote)
    check("ECS 卡片: 年度总计×12", "$27,600.00" in quote)
    check("ECS 卡片: 台数总计", "**29**" in quote)
    check("ECS 卡片: 包年实付汇总入说明", "$18,400.00" in quote)
    card = sc.render_ecs_card(quote, "2026-11-18 12:00")
    check("ECS 卡片: <br> 还原为真换行", "<br>Intel" in card and "&lt;br&gt;" not in card)
    check("ECS 卡片: 不附模型限流备注", "TPM" not in card)

    async def fake_struct(it, reg, disk=0):
        if it == "bad":
            return {"ok": False, "error": "规格无法识别"}
        return mk(it, "柔佛", 100.0, 800.0, 1)
    orig_struct = ep.query_ecs_price_struct
    orig_cfg, orig_put = sc.get_oss_config, sc._put_and_sign
    ep.query_ecs_price_struct = fake_struct
    sc.get_oss_config = lambda: {"key_id": "x", "key_secret": "y", "prefix": "t/",
                                 "bucket": "b", "endpoint": "e"}
    sc._put_and_sign = lambda cfg, key, h: ("https://example.com/card", "2026-11-19 12:00")
    try:
        r = asyncio.run(sc.make_ecs_share_link([
            {"instance_type": "ecs.a.large", "region": "柔佛", "quantity": 17}]))
        check("ECS 卡片链路: 返回 url 与条目", r.get("url") == "https://example.com/card"
              and "×17" in r["items"][0])
        r2 = asyncio.run(sc.make_ecs_share_link([
            {"instance_type": "ecs.a.large", "region": "柔佛"},
            {"instance_type": "bad", "region": "柔佛"}]))
        check("ECS 卡片链路: 任一条失败整体不出卡", "error" in r2 and "未生成卡片" in r2["error"])
    finally:
        ep.query_ecs_price_struct = orig_struct
        sc.get_oss_config, sc._put_and_sign = orig_cfg, orig_put
    share_schema = next(t["function"] for t in tools.TOOLS
                        if t["function"]["name"] == "make_price_share_link")
    check("ECS 卡片工具: ecs_items 已注册且不强制 model",
          "ecs_items" in share_schema["parameters"]["properties"]
          and "required" not in share_schema["parameters"])

    # git 超时降级守卫：TimeoutExpired 不得穿透 ensure_knowledge 跳过索引构建
    # （线上 kb_chunks=0 事故回归）
    from app import knowledge as kn
    import subprocess as sp
    orig_run = kn.subprocess.run
    def raise_timeout(*a, **kw):
        raise sp.TimeoutExpired(cmd="git pull", timeout=180)
    kn.subprocess.run = raise_timeout
    try:
        r = kn._run_git(["pull", "--ff-only"])
        check("git 守卫: 超时转普通失败不抛异常", r.returncode == 124 and "超时" in r.stderr)
    finally:
        kn.subprocess.run = orig_run
    def raise_oserr(*a, **kw):
        raise OSError("git not found")
    kn.subprocess.run = raise_oserr
    try:
        check("git 守卫: OSError 转普通失败", kn._run_git(["status"]).returncode == 127)
    finally:
        kn.subprocess.run = orig_run


def main():
    print("=" * 56)
    print("阿里小可爱AI问答助手 — 离线自测套件")
    print("=" * 56)
    test_price_verifier_units()
    test_table_render_and_followup()
    test_region_fallback_and_usage_cost()
    test_price_parsing_offline()
    test_knowledge_retrieval()
    test_store()
    test_guide_lookup()
    test_model_clarify()
    test_price_audit()
    test_followup_anchor_and_competitor()
    test_source_visibility()
    test_domain_gate()
    test_rate_limit_lookup()
    test_asr()
    test_pipeline_wiring()
    test_pipeline_usage_cost_gate()
    test_store_price_audit()
    test_fx()
    test_vendor_report()
    test_vendor_report_generality()
    test_ecs_price()
    print("-" * 56)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
