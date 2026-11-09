"""
价格联网校验 — 官方定价页结构化抽取（权威）+ 搜索引擎旁证
================================================
口径：阿里云国际站（新加坡节点）USD 列表价。
alibabacloud.com 为静态渲染页，可直接 httpx 抓取（区别于 JS 渲染站点）。

核心原则（与 LLM 解耦）：本模块产出的「证据块」是回答中唯一合法的
价格数字来源；LLM 严禁凭记忆报价，证据缺失时必须拒答并引导官方页。

v3 工具循环（2026-11-09）：主入口改为 verify_price_for(model, competitor)——
型号与竞品由 LLM 调用 verify_price 工具时显式传入，不再从问题文本做
正则提取（旧 verify_prices/competitor_of/is_table_followup 均已删）。
提取/解析/渲染的数值层护栏全部原样保留。

v2 结构化抽取：按 <table> 行 + region 标题解析，每行携带地域归属。
（v1 纯文本窗口提取的教训：定价页按 Singapore/Beijing/Frankfurt 等 6 个
region 分表，窗口提取会混淆地域归属；且 DeepSeek 的缓存折扣是 Model ID
单元格里的 "context caching discount" 标记而非独立 Cached input 列，
文本化后语义全丢。）
"""

import asyncio
import bisect
import json
import logging
import re
import time
from datetime import datetime

import httpx

from .config import PRICE_PAGE_TTL_HOURS, PRICE_PAGE_URL, get_cache_dir
from .searcher import web_search

log = logging.getLogger("price")

# 档位后缀：口语里跟在版本号后面，可多段（"wan3.0 video prime" → wan3.0-video-prime）。
# max/plus/flash/pro/turbo/thinking 为通用 LLM 档位；video/prime/t2v/i2v 等为 wan 视频线档位。
_TIER_ALT = (
    "max|plus|flash|pro|turbo|thinking|preview|video|prime"
    "|t2v|i2v|r2v|s2v|kf2v|t2i|animate|videoedit|vace"
)

# 模型名识别（价格校验的检索目标）
# wan 线要带档位后缀：wan3.0-prime / wan3.0-video-prime / wan2.2-t2v-plus。
# 只写 wan[\d.]+ 会把 "wan3.0 prime" 削成 wan3.0，于是详情页去抓 wan3-0
# （一个空壳页），拿不到分辨率分档价，模型只能在主表残缺证据上反复权衡。
MODEL_NAME_RE = re.compile(
    r"(qwen[\d.]*-(?:max|plus|flash|turbo)(?:-preview)?"
    r"|qwen[\d.]+"
    # 生图线：qwen-image-3.0-pro / qwen-image-2.1-turbo / qwen-mt-image-2.0，
    # 漏了就提取不到型号 → 落到泛化 token "qwen"，把一整片 qwen 模型都扒进证据
    r"|qwen-(?:mt-)?image(?:-[\d.]+)?(?:-(?:pro|turbo|max|flash|preview))*"
    rf"|wan[\d.]+(?:-(?:{_TIER_ALT}))*"
    r"|happyhorse[\d.]*"
    r"|deepseek-v[\d.]+(?:-pro|-flash)?"
    r"|claude-(?:opus|sonnet|haiku)-?[\d.]*"
    r"|gpt-[\d.]+(?:-mini|-nano)?"
    r"|gemini-[\d.]+"
    r"|kimi-k[\d.]+(?:-pro|-thinking)?"
    rf"|glm-[\d.]+(?:-(?:{_TIER_ALT}))*"
    r"|doubao-[\w-]+"
    r"|minimax-[\w-]+"
    r"|cosyvoice[\w-]*"
    r"|funasr|fun-music|qwen-audio[\w-]*)",
    re.IGNORECASE,
)

# 触发价格校验的问题特征
PRICE_KEYWORDS_RE = re.compile(
    r"价格|定价|多少钱|多钱|报价|报个价|计费|收费|费率|费用|成本|单价|免费额度|额度|优惠|折扣|一亿|百万"
    r"|pricing|price|cost|quota|discount|usd|美元|\$",
    re.IGNORECASE,
)

# 口语中会出现的模型家族词。当前句提到家族词却抽不出具体型号时（如
# "kimi 最新款价格"），禁止回退挪用历史里的其他模型——否则会拿着
# deepseek 的证据去回答 kimi 的问题，前端还显示"已联网核实"误导客户。
# 边界用 (?<![a-z])…(?![a-z]) 而非 \b：汉字在 Python 正则中也算 \w，
# "那kimi呢"/"kimi的" 在 \b 下不命中，追问场景会漏拦截。
_FAMILY_HINT_RE = re.compile(
    r"(?<![a-z])(qwen|wan|deepseek|glm|kimi|claude|gpt|gemini|doubao|minimax"
    r"|cosyvoice|funasr|fun-music|happyhorse)(?![a-z])",
    re.IGNORECASE,
)

# 非百炼模型的阿里云产品（订阅/席位制，不在百炼 model-pricing 页上）。
# 问它们的价格时若走了百炼模型校验，models 提取为空 → 注入"未能核实，
# 请引导 model-studio/model-pricing"的兜底证据 → LLM 把百炼定价页链接
# 安到 Qoder 头上（事故实测）。产品定价题应交给知识库检索回答。
# 边界同上：(?<![a-z])…(?![a-z])，防 "qoder的" /"那qoder呢" 漏匹配。
_PRODUCT_NAME_RE = re.compile(
    r"(?<![a-z])(qoder(?:wake|work)?|qwen-?work|百小可爱)(?![a-z])",
    re.IGNORECASE,
)

# ── 跨云比价 ──
# v3 工具循环（2026-11-09）：竞品不再从问题文本正则识别（competitor_of 已删），
# 由 LLM 调 verify_price 工具时显式传 competitor 参数（enum 白名单约束）。
# 下面的官方页/英文名/自研型号映射供 verify_price_for 使用。

# 竞品的「国际站（海外站）官方定价页」：静态 HTML、以 USD / 每百万 tokens 计价，
# 与阿里云国际站口径完全一致，可直接抓取并结构化抽取，优先于搜索摘要。
# 用户明确要求：跨云比价必须用美金版本定价对比（腾讯云国际站 = tencentcloud.com，
# 其 TokenHub 模型定价文档即 USD 口径；pricing/hunyuan 那个页是混元生 3D，不是 LLM）。
_COMPETITOR_OFFICIAL_PAGES: dict[str, tuple[str, ...]] = {
    "腾讯云混元": ("https://www.tencentcloud.com/document/product/1300/78937",),
}

# 搜索回退时用的英文检索名（英文 query 更容易命中国际站 USD 定价页）
_COMPETITOR_EN = {
    "腾讯云混元": "Tencent Cloud Hunyuan",
    "火山引擎豆包": "Volcano Engine Doubao",
    "百度智能云文心": "Baidu ERNIE API",
    "AWS Bedrock": "AWS Bedrock pricing",
    "OpenAI": "OpenAI API",
    "Anthropic Claude": "Anthropic Claude API",
    "Google Gemini": "Google Gemini API",
    "DeepSeek 官方": "DeepSeek API",
}

# 竞品“自研型号”识别：同一张国际站定价表里往往混着对方自研型号与对方平台上架的
# 第三方模型（如腾讯云 TokenHub 既卖混元 Hy3/Hy4，也卖 DeepSeek/GLM/Kimi）。
# 后者是转售或自部署托管，价格由该平台决定，**不等于模型厂商官方价**；不分账
# 就会拿“腾讯云上的 DeepSeek 价”去解释“腾讯自研模型价格”，结论必错。
_COMPETITOR_SELF_RE = {
    "腾讯云混元": re.compile(r"(?i)hunyuan|hy\d|混元"),
    "火山引擎豆包": re.compile(r"(?i)doubao|豆包|seedance|seedream"),
    "百度智能云文心": re.compile(r"(?i)ernie|文心"),
    "OpenAI": re.compile(r"(?i)gpt|o\d-(?:mini|preview)"),
    "Anthropic Claude": re.compile(r"(?i)claude"),
    "Google Gemini": re.compile(r"(?i)gemini|imagen|veo"),
    "DeepSeek 官方": re.compile(r"(?i)deepseek"),
}


def _norm_model_key(s: str) -> str:
    """型号宽松归一：去连字符/点/空格并小写，便于跨厂商写法对齐。"""
    return re.sub(r"[^a-z0-9]", "", s.lower())


def _peak_tag(line: str) -> str:
    """区分忙时/闲时分档：返回 offpeak / peak / 空串。

    腾讯 TokenHub 文档把同一型号拆成 PEAK 与 OFF-PEAK 两张表，行内模型名重复，
    如果只按型号去重会把高峰价丢掉，因此去重键必须带上时段标签。
    """
    if re.search(r"(?i)off[\s-]?peak|idle", line):
        return "offpeak"
    if re.search(r"(?i)peak|busy", line):
        return "peak"
    return ""


# 定价页分表的地域标题（口径优先级：Singapore > China (Beijing) > 其他）
_REGIONS = (
    "Singapore",
    "China (Beijing)",
)
_REGION_RE = re.compile("|".join(re.escape(r) for r in _REGIONS))

# 首格像模型 ID 的行才入库（排除表头/说明行）
_ROW_MODEL_RE = re.compile(r"^[a-z][a-z0-9._-]{2,40}", re.IGNORECASE)
_ROW_SKIP_KW = ("model", "note", "region", "deployment", "scope", "quota", "item")


def is_price_question(question: str, history: list | None = None) -> bool:
    """价格问题识别（仅服务于 pipeline 的缺型号反问快路径）。

    v3 工具循环后，“是否联网查价”已交由 LLM 调 verify_price 工具自主决策，
    本函数只保留一个窄场景：价格意图明确但没说型号时，确定性反问比让模型
    反问更稳（不猜型号、不联网、不报价，秒回）。
    """
    if question and PRICE_KEYWORDS_RE.search(question):
        if extract_model_names(question) or not _PRODUCT_NAME_RE.search(question):
            return True
    if history and question and len(question) <= 30 and extract_model_names(question):
        for h in history[-8:]:
            if h.get("role") == "user" and PRICE_KEYWORDS_RE.search(
                str(h.get("content", ""))[:200]
            ):
                return True
    return False


# 列举式问法（"都有哪些模型，价格多少"）要的是清单，反问型号只会变相刁难
_CLARIFY_LISTING_RE = re.compile(
    r"哪些|哪几|都有|全部|所有|清单|列表|对比|比较|区别|推荐|哪个好|哪个便宜|多少种|一览"
)


def needs_model_clarify(question: str, history: list | None = None) -> bool:
    """价格意图明确、但根本没说问哪个型号时，应该反问而不是直接拒答。

    背景（后台点踩案例）：用户问「新加坡节点模型价格是多少」，旧逻辑把它当成
    「无 official 证据 → 输出固定拒答话术」，思考 1000+ 字、耗时 44 秒，最后只
    回一句"暂未能联网核实"——信息量为零。真实诉求是让助手反问一句型号。

    只有下面五类"能自己答"的情况才跳过反问：
      1) 句中已含型号（含追问里的型号）；2) 家族词（qwen 多少钱 → 厂商级概览）；
      3) 产品订阅价（Qoder 等，交知识库）；4) 列举式问法；5) 历史里问过型号（追问）。
    """
    if not question or not PRICE_KEYWORDS_RE.search(question):
        return False
    if extract_model_names(question):
        return False
    if _FAMILY_HINT_RE.search(question) or _PRODUCT_NAME_RE.search(question):
        return False
    if _CLARIFY_LISTING_RE.search(question):
        return False
    # 追问：「它/这个多少钱」应沿用上一轮型号，反问反而打断
    for h in (history or [])[-6:]:
        if h.get("role") == "user" and extract_model_names(str(h.get("content", ""))):
            return False
    return True


def _tag_and_split_rows(
    html: str, competitor: str, models: list[str] | None = None
) -> tuple[list[str], list[str]]:
    """把竞品定价页表格行拆成「同款」与「其它」两组，并打上归属标记。

    纯函数（不联网），便于离线单测。打标规则：
      [自研]            对方自研型号（匹配 _COMPETITOR_SELF_RE）
      [第三方模型·对方平台价]  其余：对方平台上架的他人模型（转售或自部署托管）
      [同款]            与本次所问模型同一型号（优先在前，可逐项对比）
    """
    want = {
        _norm_model_key(m)
        for m in (models or [])
        if m and m != "qwen" and len(_norm_model_key(m)) >= 5
    }
    self_re = _COMPETITOR_SELF_RE.get(competitor)
    same_rows: list[str] = []
    other_rows: list[str] = []
    seen: set[str] = set()
    dup_seen: set[str] = set()
    for table in re.findall(r"<table[\s\S]*?</table>", html, re.I):
        # 价格单元格常见两种写法：带 $ 的（阿里云风格）与纯数字 + 表头注明
        # “(USD / million tokens)”的（腾讯云文档风格，全页只有 1 个 $）。
        # 只认 $ 会把后者整个表丢光（实测 15 张表全部被过滤）。
        head = re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", table))[:600]
        usd_table = bool(re.search(r"(?i)usd|us\$", head))
        last_model = ""  # 分表/跨行的模型名继承（PEAK 段常见首格留空）
        for tr in re.findall(r"<tr[\s\S]*?</tr>", table, re.I):
            cells = re.findall(r"<t[dh][\s\S]*?</t[dh]>", tr, re.I)
            if not cells:
                continue
            vals = [re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", c)).strip() for c in cells]
            # 首格必须是真实型号名；为空时沿用上一行模型名（PEAK 分表结构），
            # 否则会把“高峰价”整行丢掉，只拿闲时价去比。
            main_name = re.split(r"[\s(（]", vals[0] if vals else "")[0]
            if not main_name or not re.search(r"\w", main_name):
                if vals and last_model:
                    vals[0] = last_model
                    main_name = re.split(r"[\s(（]", last_model)[0]
                else:
                    continue
            else:
                last_model = vals[0]
            line = "| " + " | ".join(vals) + " |"
            # 行内必须有“像价格”的数字：带小数，或 ≥3 位整数（避开型号里的 3、4）
            has_price = bool(re.search(r"\d+\.\d+|\d{3,}", line))
            if not has_price:
                continue
            if "$" not in line and not usd_table:
                continue
            if line in seen:
                continue
            seen.add(line)
            key = _norm_model_key(line)
            same = bool(want) and any(w in key for w in want)
            if self_re and self_re.search(line):
                tag = "[自研]"
            else:
                tag = "[第三方模型·对方平台价]"
            if same:
                tag += "[同款]"
            # 同一型号常因“(Vendor Direct)”“-1017”等写法重复出现，按 型号+时段 去重
            matched = next((w for w in want if w in key), "")
            dedup = f"{matched or _norm_model_key(main_name)}|{_peak_tag(line)}"
            if dedup in dup_seen:
                continue
            dup_seen.add(dedup)
            (same_rows if same else other_rows).append(f"{tag} {line}")
    return same_rows, other_rows


async def _competitor_official_blocks(
    competitor: str, models: list[str] | None = None
) -> tuple[list[str], list[dict]]:
    """抓竞品国际站官方定价页，抽出含 $ 的表格行并标注型号归属（USD / 百万 tokens）。

    为什么优先于搜索：搜索摘要常把人民币价或二手博客价当成官方价（实测出现
    “$15/百万 tokens”这类离谱数字），而国际站文档页是静态 HTML 可比对。

    打标规则（关键）：
      [自研]            对方自研型号（混元 Hy3/Hy4、豆包、文心等）
      [第三方模型·对方平台价]  对方平台上架的他人模型（DeepSeek/GLM/Kimi/Qwen），
                          可能是转售或自部署托管，价格由该平台决定，不代表模型厂商官方价
      [同款]            与本次所问模型同一型号，可逐项对比（优先排在前面）
    """
    blocks: list[str] = []
    srcs: list[dict] = []
    for url in _COMPETITOR_OFFICIAL_PAGES.get(competitor, ()):  # type: ignore[arg-type]
        try:
            html = await _cached_fetch(f"competitor_{competitor}", url)
        except Exception as e:
            log.warning("竞品定价页抓取失败 %s: %s", url, e)
            continue
        if not html:
            continue
        same_rows, other_rows = _tag_and_split_rows(html, competitor, models)
        if not same_rows and not other_rows:
            continue
        blocks.append(
            f"国际站官方定价页（{competitor} · USD / 百万 tokens）：{url}\n"
            "行首标记含义：[自研] = 对方自研型号；[第三方模型·对方平台价] = 对方平台上架的"
            "第三方模型（转售或自部署托管，价格由该平台定价，**不代表模型厂商官方价**）；"
            "[同款] = 与本次所问型号相同，可直接逐项对比。"
        )
        # 同款最多 4 行（通常就 2 行：忙/闲），其余型号最多凑到 8 行。
        # 行数过多会让模型在两份价格表之间反复权衡，实测耗时从 55s 涨到 158s。
        blocks.extend(same_rows[:4])
        blocks.extend(other_rows[: max(0, 8 - len(same_rows[:4]))])
        srcs.append(
            {
                "title": f"{competitor} 国际站官方定价（USD / 百万 tokens）",
                "url": url,
                "kind": "web",
            }
        )
        break
    return blocks, srcs


def _slug_candidates(model: str) -> list[str]:
    """口语模型名 → 官方详情页 slug 候选（按顺序尝试）。

    wan 视频线的官方 ID 里往往带 video：口语说 "wan3.0 prime"，页面却是
    wan3-0-video-prime；裸版本号 wan3.0 则同时对应 video 与 video-prime。
    早期只用 model.replace('.','-') 直拼，结果去抓了 wan3-0（空壳页），
    分辨率分档价全部拿不到。
    """
    base = model.replace(".", "-")
    # 注意不能直接 base.split("-")：wan3.0 转成 wan3-0 后会被误拆为 head=wan3/rest=0
    m = re.fullmatch(r"(wan[\d.]+)(?:-(.+))?", model, re.IGNORECASE)
    if not m:
        return [base]
    head, rest = m.group(1).replace(".", "-"), m.group(2)
    base = f"{head}-{rest}" if rest else head
    cands = [base]
    if rest and not re.search(
        r"(video|t2v|i2v|r2v|s2v|kf2v|t2i|animate|videoedit|vace)", rest
    ):
        cands.append(f"{head}-video-{rest}")
    elif not rest:
        cands += [f"{base}-video", f"{base}-video-prime"]
    out: list[str] = []
    for c in cands:
        if c not in out:
            out.append(c)
    return out


def extract_model_names(question: str) -> list[str]:
    """从问题中提取去重后的模型名（小写），并把口语写法归一为官方 model ID：
    'qwen3.8 max' → 'qwen3.8-max'、'kimi k3.1 pro' → 'kimi-k3.1-pro'、
    'deepseek v4.1 flash' → 'deepseek-v4.1-flash'。
    """
    q = question
    # ⓪ 省略版本前缀/连字符的口语写法先补齐：
    #    "deepseek4.1呢" / "deepseek 4.1" / "deepseekv4.1" → deepseek-v4.1，
    #    "glm4.6" → glm-4.6。漏掉这一层会抽不出型号，叠加家族词守卫后
    #    既不能挪用历史模型、又没有证据，只能甩"暂未能联网核实"（2026-11-09 实测）。
    q = re.sub(r"(?<![a-z])deepseek[\s-]*v?([\d.]+)", r"deepseek-v\1", q, flags=re.IGNORECASE)
    q = re.sub(r"(?<![a-z])glm[\s-]*([\d.]+)", r"glm-\1", q, flags=re.IGNORECASE)
    # ① 家族名与版本号之间的口语空格先归并（注意家族差异：
    #    kimi/deepseek/glm 官方 ID 带连字符，qwen/wan 不带）。
    #    边界用 (?<![a-z]) 而非 \b：汉字也算 \w，"和deepseek v4.1" 在 \b 下不命中
    q = re.sub(r"(?<![a-z])(kimi|deepseek|glm)[\s-]+([a-z]?[\d.]+)", r"\1-\2", q, flags=re.IGNORECASE)
    q = re.sub(r"(?<![a-z])(qwen|wan)\s+([a-z]?[\d.]+)", r"\1\2", q, flags=re.IGNORECASE)
    # ①-b 生图线："qwen image 2.1 pro" → qwen-image-2.1-pro（三类前缀都要归）
    q = re.sub(
        r"(?<![a-z])qwen[\s_\-]*(mt[\s_\-]+)?image",
        lambda m: "qwen-mt-image" if m.group(1) else "qwen-image",
        q,
        flags=re.IGNORECASE,
    )
    q = re.sub(r"(qwen-(?:mt-)?image)[\s_\-]+([\d.]+)", r"\1-\2", q, flags=re.IGNORECASE)
    # ② 版本号与档位后缀之间的空格归并为连字符（保留 ① 拼出的 k/v 前缀）。
    #    后缀边界用 (?![a-z]) 而非 \b：CJK 汉字在 Python 正则中也算 \w，
    #    "pro的价格" 在 "pro" 后没有 \b，会漏归一（"kimi-k3.1 pro的价格" 实测踩坑）
    #    循环替换以支持多段后缀（"wan3.0 video prime" → "wan3.0-video-prime"）。
    suffix_re = re.compile(
        rf"(?<![a-z])(qwen|wan|kimi|deepseek|glm)(-?[a-z]?[\d.]+(?:-(?:{_TIER_ALT}))*)"
        rf"\s+({_TIER_ALT})(?![a-z])",
        re.IGNORECASE,
    )
    while True:
        q2 = suffix_re.sub(r"\1\2-\3", q)
        if q2 == q:
            break
        q = q2
    # 生图线的档位后缀（"qwen image 2.1 pro" → qwen-image-2.1-pro）
    q = re.sub(
        rf"(qwen-(?:mt-)?image-[\d.]+)\s+({_TIER_ALT})(?![a-z])", r"\1-\2", q, flags=re.IGNORECASE
    )
    return sorted({m.group(0).lower() for m in MODEL_NAME_RE.finditer(q)})


# ──────────────────── 抓取与缓存 ────────────────────


async def _fetch_raw(url: str) -> str:
    try:
        async with httpx.AsyncClient(timeout=20, follow_redirects=True) as client:
            r = await client.get(url, headers={"User-Agent": "Mozilla/5.0"})
            r.raise_for_status()
            return r.text
    except Exception as e:
        log.warning("抓取 %s 失败: %s", url, e)
        return ""


def _strip_tags(html: str) -> str:
    text = re.sub(r"<script[\s\S]*?</script>", " ", html, flags=re.I)
    text = re.sub(r"<style[\s\S]*?</style>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    return re.sub(r"\s+", " ", text)


async def _get_pricing_html() -> str:
    """官方定价页原始 HTML，TTL 内读缓存；抓取失败时降级用过期缓存"""
    return await _cached_fetch("pricing_page", PRICE_PAGE_URL)


async def _cached_fetch(key: str, url: str) -> str:
    """通用抓取缓存：{key}.html + {key}.json 元数据，TTL 同定价页；失败降级过期缓存"""
    cache_dir = get_cache_dir()
    page_file = cache_dir / f"{key}.html"
    meta_file = cache_dir / f"{key}.json"
    now = time.time()
    if page_file.exists() and meta_file.exists():
        try:
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            if now - meta.get("fetched_at", 0) < PRICE_PAGE_TTL_HOURS * 3600:
                return page_file.read_text(encoding="utf-8")
        except Exception:
            pass
    html = await _fetch_raw(url)
    if html:
        page_file.write_text(html, encoding="utf-8")
        meta_file.write_text(
            json.dumps({"fetched_at": now, "url": url}), encoding="utf-8"
        )
        return html
    if page_file.exists():
        log.warning("%s 本次抓取失败，沿用过期缓存", key)
        return page_file.read_text(encoding="utf-8")
    return ""


# ────────────── 模型详情页（含缓存/细项价格，优先于主定价页） ──────────────

# 详情页 Billing Item 行（长项优先；可选括号修饰词支持忙/闲时段写法，如 "Input (Idle hours) 0.141"）
_BILLING_ITEM_RE = re.compile(
    r"(Explicit Cache Creation|Explicit Cache Read|Input\(Implicit Cache[^)]*\)|"
    r"Input\(Batch File\)|Input\(Batch Chat\)|Output\(Batch File\)|Output\(Batch Chat\)"
    r"|Input|Output)\s*(\([^)]*\))?\s+\$?([\d.]+)",
    re.IGNORECASE,
)


def _parse_model_pricing(text: str) -> dict:
    """从模型详情页纯文本中提取 Pricing 节的 Singapore / Beijing 计费项。

    返回 {region: {billing_item_lower: "$price"}}，region 为 Singapore / China (Beijing)。
    """
    out: dict = {}
    pi = text.find("original pricing")
    if pi < 0:
        pi = text.lower().find("pricing")
    if pi < 0:
        return out
    # 窗口：Pricing 节起点 → 之后的 Rate Limits 节（详情页该节标题固定）
    ri = text.find("Rate Limits", pi)
    window = text[pi : ri if ri > 0 else pi + 20000]
    for region in ("Singapore", "China (Beijing)"):
        rpos = window.find(region)
        if rpos < 0:
            continue
        # 切到下一个 region 标题或窗口尾
        nexts = [window.find(r2, rpos + len(region)) for r2 in _REGIONS if r2 != region]
        end = min([n for n in nexts if n > 0], default=len(window))
        seg = window[rpos + len(region) : end]
        items: dict = {}
        for m in _BILLING_ITEM_RE.finditer(seg):
            base = m.group(1).lower()
            qual = (m.group(2) or "").strip("() ").strip()  # 如 "Idle hours"
            # 归一化：Input(Implicit Cache, Busy hours) → base=input(implicit cache), qual=busy hours
            m_ic = re.match(r"input\(implicit cache\s*,?\s*([^)]*)\)$", base)
            if m_ic:
                extra = m_ic.group(1).strip(" ,")
                base = "input(implicit cache)"
                qual = (extra + ", " + qual).strip(" ,") if qual and extra else (extra or qual)
            # kimi 详情页写法 "Input (cache hit) 0.184" → 缓存命中价，归入 Cache Input 列
            if base == "input" and "cache hit" in qual.lower():
                base, qual = "input(implicit cache)", ""
            key = base + (f"|{qual.lower()}" if qual else "")
            if key not in items:  # 同名取首个（区域段内不会重复）
                items[key] = "$" + m.group(3)
        if items:
            out[region] = items
    return out


# ────────────── 标准价格表渲染（代码生成，杜绝 LLM 排版漂移） ──────────────
# 列序为产品约定：Region | Input | Cache Input | Output | Cache Write | 备注
_TABLE_HEADER = (
    "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) "
    "| 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |"
)
_TABLE_SEP = "|---|---|---|---|---|---|"


def _render_price_table(title: str, rows: list[tuple]) -> str:
    """rows 元素: (region_label, input, cache_input, output, cache_write, note)"""
    lines = [f"**{title}**", "", _TABLE_HEADER, _TABLE_SEP]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} | {r[5]} |" for r in rows]
    return "\n".join(lines)


def _detail_evidence(model_id: str, page_url: str, pricing: dict) -> list[str]:
    """模型详情页 → 标准价格表（代码渲染）。

    按 qualifier（idle/busy hours）拆行；显式缓存读取与 Batch 档价进备注列；
    详情页未提供的计费项（如 DeepSeek 系无 Explicit Cache Creation）填 “—”。
    """
    rows: list[tuple] = []
    for region, items in pricing.items():
        # 按时段 qualifier 分组：input|idle hours 与 output|idle hours 同行
        groups: dict[str, dict] = {}
        order: list[str] = []
        for key, price in items.items():
            base, _, qual = key.partition("|")
            if qual not in groups:
                groups[qual] = {}
                order.append(qual)
            groups[qual][base] = price
        for qual in order:
            g = groups[qual]
            notes = []
            if g.get("explicit cache read"):
                notes.append(f"显式缓存读取 {g['explicit cache read']}")
            # 口径：Batch 折扣/批次价一律忽略，不进备注
            rows.append(
                (
                    f"{region} · {qual}" if qual else region,
                    g.get("input", "—"),
                    g.get("input(implicit cache)", "—"),
                    g.get("output", "—"),
                    g.get("explicit cache creation", "—"),
                    "；".join(notes) or "—",
                )
            )
    return [
        _render_price_table(
            f"{model_id} · 模型详情页定价（每 1M tokens USD · 权威）", rows
        )
    ]


# ────────────── 视频/图像模型：按秒/按张计费（分辨率分档） ──────────────
# 详情页写法："Video generation (480P) 0.068 Per second"，与 LLM 的
# "Input/Output ... Per million tokens" 完全不同。早期只认 token 计费，
# 视频页解析结果为空 → 退回主表 → 模型拿到"标题写每 1M tokens、值却是每秒、
# 丢分辨率与单位"的残缺证据，只能长篇权衡（实测思考 5818 字 / 正文 445 字）。
# 详情页计费项写法不统一，不能靠固定模板匹配。实测三种：
#   Video generation (480P) 0.068 Per second
#   Image Generation 0.04 Per image            （qwen-image-2.1-pro，无括号）
#   1K Image Output 0.04 / 2KImage Generation 0.068761 / 1KImageInput 0.00275
# 因此只锤“价格 + Per 单位”锚点，向前取 60 字当计费项文本，再从中抽分辨率与类别。
_MEDIA_PRICE_RE = re.compile(
    r"\$?(\d+(?:\.\d+)?)\s+Per\s+(second|image|video|generation|item)", re.IGNORECASE
)
# 分辨率： 1K / 2K / 480P / 1080P / 1024x1024。
# 不能用 \b 收尾：详情页有 "1KImage Generation"（无空格）写法，K 后直接接字母。
_RES_RE = re.compile(
    r"(\d{1,2}\s*[Kk])|(\d{3,4}\s*[Pp])|(\d{3,4}\s*[x×*]\s*\d{3,4})"
)
_UNIT_ZH = {"second": "秒", "image": "张", "video": "条", "generation": "次", "item": "项"}


def _media_label(seg: str, pos: int) -> str:
    """取价格之前的计费项文字，砍掉上一项尾巴与表头噪声（Billing Item / Price (USD) Unit）"""
    tail = seg[max(0, pos - 60) : pos]
    tail = re.split(r"Per\s+(?:second|image|video|generation|item)", tail, flags=re.I)[-1]
    tail = re.split(r"\bUnit\b", tail, flags=re.I)[-1]
    tail = re.split(r"\bBilling [Ii]tem\b", tail)[-1]
    return re.sub(r"\s+", " ", tail).strip(" ,")


def _media_kind(label: str) -> str:
    """计费项 → 输出图 / 输入图 / 视频 / 未知（去空格后判，容忍 1KImageInput 写法）"""
    low = label.lower().replace(" ", "")
    if "imageinput" in low:
        return "输入图"
    if "imageoutput" in low or "imagegeneration" in low:
        return "输出图"
    if "videogeneration" in low or "videooutput" in low:
        return "视频"
    return ""


def _media_res(label: str) -> str:
    m = _RES_RE.search(label)
    if not m:
        return ""
    return re.sub(r"\s+", "", m.group(0)).upper().replace("*", "×")

# 详情页全部地域标题（仅用于切段，输出仍只取 Singapore + China (Beijing)）
_ALL_REGION_HEADS = (
    "Singapore",
    "China (Beijing)",
    "Japan (Tokyo)",
    "Germany (Frankfurt)",
    "US (Virginia)",
    "China (Hong Kong)",
)

_MEDIA_HEADER = "| 模型 (Model ID) | Region | 分辨率 | 单价 | 备注 |"
_MEDIA_SEP = "|---|---|---|---|---|"


def _pricing_window(text: str) -> str:
    """从详情页纯文本切出 Pricing 节（到 Rate limits 为止）"""
    pi = text.find("original price")
    if pi < 0:
        pi = text.lower().find("pricing")
    if pi < 0:
        return ""
    ri = min(
        [p for p in (text.find("Rate limits", pi), text.find("Rate Limits", pi)) if p > 0],
        default=-1,
    )
    return text[pi : ri if ri > 0 else pi + 20000]


def _seg_by_region(window: str) -> dict:
    """按地域标题切段。必须扫全部地域：只扫 Singapore/Beijing 会让 Singapore 段
    吞下 Tokyo/Frankfurt 等分表的价格（同一模型不同地域价不同，串了就错）。"""
    heads = sorted(
        (window.find(n), n) for n in _ALL_REGION_HEADS if window.find(n) >= 0
    )
    out: dict = {}
    for i, (p, name) in enumerate(heads):
        end = heads[i + 1][0] if i + 1 < len(heads) else len(window)
        out.setdefault(name, window[p + len(name) : end])
    return out


def _parse_media_pricing(text: str) -> dict:
    """从模型详情页提取「分辨率 × 单价」的按秒/按张计费。

    返回 {region: [(分辨率, 计费项类别, "$0.04/张")]}，类别为 输出图/输入图/视频。
    空 dict 表示该页不是按秒/按张计费（即按 token 计费的常规模型）。
    """
    window = _pricing_window(text)
    if not window:
        return {}
    segs = _seg_by_region(window)
    out: dict = {}
    for region in _REGIONS:  # Singapore 主口径 + China (Beijing) 第二参考
        seg = segs.get(region)
        if not seg:
            continue
        items = []
        for m in _MEDIA_PRICE_RE.finditer(seg):
            label = _media_label(seg, m.start())
            unit = _UNIT_ZH.get(m.group(2).lower(), m.group(2))
            items.append((_media_res(label), _media_kind(label), f"${m.group(1)}/{unit}"))
        if items:
            out[region] = items
    return out


def _id_from_slug(slug: str) -> str:
    """详情页 slug → 官方 Model ID（wan3-0-video-prime → wan3.0-video-prime；
    qwen-image-2-1-pro → qwen-image-2.1-pro）。表格里的模型名要给客户看的官方 ID。
    """
    out = re.sub(r"^(wan|qwen|happyhorse)(\d+)-(\d+)", r"\1\2.\3", slug, flags=re.I)
    if out == slug:
        out = re.sub(r"(image)-(\d+)-(\d+)", r"\1-\2.\3", slug, flags=re.I)
    return out


def _render_media_table(title: str, rows: list[tuple]) -> str:
    """rows 元素: (model_id, region, resolution, price, note)"""
    lines = [f"**{title}**", "", _MEDIA_HEADER, _MEDIA_SEP]
    lines += [f"| {r[0]} | {r[1]} | {r[2]} | {r[3]} | {r[4]} |" for r in rows]
    return "\n".join(lines)


def _media_evidence(model_id: str, media: dict) -> list[str]:
    """详情页分辨率分档价 → 按秒/按张计费表。

    图片模型有输入图/输出图两个价：**单价列取输出图价**（用户问“每张多少钱”），
    输入图价放备注，不能混为一谈（qwen-image-3.0 输入 $0.003 vs 输出 $0.04）。
    """
    rows: list[tuple] = []
    for region in _REGIONS:
        items = media.get(region, [])
        input_by_res = {res: p for res, kind, p in items if kind == "输入图"}
        outputs = [it for it in items if it[1] in ("输出图", "视频")]
        if not outputs:  # 只有输入价等异常情况：原样给出，不吞数据
            outputs = [it for it in items if it[1] != "输入图"] or items
        for res, kind, price in outputs:
            note = "—"
            if kind == "输出图" and res in input_by_res:
                note = f"输入图 {input_by_res[res]}"
            rows.append((model_id, region, res or "—", price, note))
    if not rows:
        return []
    return [_render_media_table(f"{model_id} · 模型详情页定价（按秒/按张计费）", rows)]


def _official_id(raw: str) -> str:
    """主表首格 → 纯官方模型 ID（剥掉折扣/缓存标记后缀）。

    主表 model_id 形如 "qwen3.8-max 50% batch inference discount context caching
    discount"，直接拿来当标题会把营销标记写进模型名。
    """
    return re.split(
        r"\s+(?:\d+%\s*batch|batch inference discount|context caching discount)",
        (raw or "").strip(),
    )[0].strip()


def _row_matches(model_id: str, token: str) -> bool:
    """主表行与问题里的模型 token 匹配。

    先试子串（wan3.0 → wan3.0-video 系列），再试分段全含：
    "wan3.0-prime" 的 [wan3.0, prime] 必须都在 model_id 里，
    这样只命中 wan3.0-video-prime，不会把普通版 wan3.0-video 混进来。
    """
    mid = model_id.lower()
    if token in mid:
        return True
    parts = [p for p in token.lower().split("-") if p]
    return len(parts) > 1 and all(p in mid for p in parts)


def _media_rows_from_main(rows: list[dict], token: str) -> list[tuple]:
    """主定价页里的按秒/按张行 → 媒体计费表行（带模型列，避免多个型号混行）。

    图片模型表头同时有 Input unit price 与 Output unit price：**单价列取输出价**
    （问“每张多少钱”指的是生成价），否则会把 $0.003 的输入图价当报价报出去。
    """
    out: list[tuple] = []
    seen: set = set()
    for r in [x for x in rows if _row_matches(x["model_id"], token)][:16]:
        cells = r["cells"]
        hc = r.get("header_cells") or []

        def _idx(*kws: str) -> int | None:
            """表头同时含所有这些关键词的列（先精确，后宽松）"""
            for i, c in enumerate(hc):
                cl = c.lower()
                if all(k in cl for k in kws):
                    return i
            return None

        def _price_at(i: int | None) -> str:
            if i is None or i >= len(cells):
                return ""
            m = re.search(r"\$([\d.]+)\s*/\s*(second|image)", cells[i], re.I)
            return f"${m.group(1)}/{_UNIT_ZH[m.group(2).lower()]}" if m else ""

        res_i = _idx("resolution")
        scope_i = _idx("scope")
        # 优先输出价，其次任意价格列
        price = _price_at(_idx("output", "price"))
        if not price:
            price = _price_at(_idx("price"))
        if not price:
            continue
        input_price = _price_at(_idx("input", "price"))
        scope = cells[scope_i] if scope_i is not None and scope_i < len(cells) else ""
        region = f"{r['region']} · {scope}" if scope.strip() else r["region"]
        res = cells[res_i] if res_i is not None and res_i < len(cells) else "—"
        res = _media_res(res) or res  # 统一成 1K/2K/480P 写法（页面里有 1k 小写）
        # 官方页同一型号会按 scope 重复多行（Global/无 scope 同价），按型号+地域+分辨率+价去重
        key = (r["model_id"], r["region"], res, price)
        if key in seen:
            continue
        seen.add(key)
        raw = cells[_idx("price")] if _idx("price") is not None else ""
        note = "列表价，限时折扣以官方页为准" if "limited" in raw.lower() else "—"
        if input_price and input_price != price:
            note = f"输入图 {input_price}" if note == "—" else f"输入图 {input_price}；{note}"
        out.append((r["model_id"], region, res, price, note))
    return out


# ──────────────────── 结构化解析 ────────────────────


def _cells(tr_html: str) -> list[str]:
    cells = []
    for td in re.finditer(r"<t[dh][^>]*>([\s\S]*?)</t[dh]>", tr_html):
        txt = re.sub(r"&nbsp;?", " ", td.group(1))
        txt = re.sub(r"<[^>]+>", " ", txt)
        cells.append(re.sub(r"\s+", " ", txt).strip())
    return cells


def _parse_pricing_rows(html: str) -> list[dict]:
    """把定价页全部 <table> 解析为行记录。

    每行 {region, model_id, cells, header}：
      region  = 行所属地域（由该表之前最近的 region 标题决定，bisect 定位）
      header  = 该表表头（用于证据中说明列含义）
    """
    # 提取页首官方缓存计费规则（explicit cache / implicit cache 说明段），
    # 供无独立命中价的模型附注引用
    text = _strip_tags(html)
    m = re.search(r"cache\s*creation|Cache-hit input tokens", text, re.I)
    _CACHE_RULE_POS["page"] = text
    _CACHE_RULE_POS["rule"] = m.start() - 120 if m else None
    # 预扫描全部地域标题位置
    heads = []
    for h in re.finditer(r"<h[1-4][^>]*>([\s\S]*?)</h[1-4]>", html):
        m = _REGION_RE.search(_strip_tags(h.group(1)))
        if m:
            heads.append((h.start(), m.group(0)))
    positions = [p for p, _ in heads]

    rows: list[dict] = []
    for tbl in re.finditer(r"<table[\s\S]*?</table>", html):
        idx = bisect.bisect_right(positions, tbl.start()) - 1
        region = heads[idx][1] if idx >= 0 else ""
        trs = list(re.finditer(r"<tr[\s\S]*?</tr>", tbl.group(0)))
        if not trs:
            continue
        # 首行若含 "model" 视为表头
        first_cells = _cells(trs[0].group(0))
        header = (
            " ｜ ".join(c for c in first_cells if c)[:220]
            if any("model" in c.lower() for c in first_cells)
            else ""
        )
        for tr in trs:
            cells = _cells(tr.group(0))
            if not cells:
                continue
            first = cells[0]
            lowered = first.lower()
            if (
                not _ROW_MODEL_RE.match(first)
                or any(k in lowered for k in _ROW_SKIP_KW)
                or not first.replace("context caching discount", "").strip()
            ):
                continue  # 表头/说明行
            rows.append(
                {
                    "region": region,
                    "model_id": first,
                    "cells": cells,
                    "header": header,
                    "header_cells": first_cells,  # 表头单元格序列（代码渲染表格的列映射依据）
                }
            )
    log.info("定价页结构化解析: %d 行（含地域归属）", len(rows))
    return rows


# 命中缓存但无独立命中价时，附官方页首的显式/隐式缓存计费规则（解析时填充）
_CACHE_RULE_POS: dict = {}


def _col_roles(header_cells: list[str]) -> dict:
    """表头单元格 → 列角色索引（主定价页表头存在多种变体：有无 scope 列、free quota 列等）"""
    roles: dict = {}
    for i, c in enumerate(header_cells):
        cl = c.lower()
        if "deployment scope" in cl or cl.strip() in ("scope", "region"):
            roles.setdefault("scope", i)
        elif "input price" in cl:
            roles.setdefault("input", i)
        elif "output price" in cl:
            roles.setdefault("output", i)
        elif "cached input" in cl or "cache hit" in cl:
            roles.setdefault("cache_input", i)
        elif "cache creation" in cl or "cache write" in cl:
            roles.setdefault("cache_write", i)
    return roles


def _first_price(cell: str) -> str:
    m = re.search(r"\$[\d.]+", cell)
    return m.group(0) if m else ""


def _model_evidence(rows: list[dict], token: str) -> list[str]:
    """某模型 → 标准价格表（代码渲染；Singapore 主口径 + China (Beijing) 第二参考，均给）。

    按表头列映射取数，杜绝 LLM 渲染时的跨 scope 挪用（此前 US scope 的 $2
    曾被当成 Singapore·International 价）。busy/idle 双价同格的行拆为两行，
    同 region 同 scope 同价的重复行合并。
    """
    hits = [r for r in rows if _row_matches(r["model_id"], token)]
    if not hits:
        return []

    # 标题必须用主表里的官方 model_id，而不是用户口语 token：
    # "kimi-k3.1呢" 命中的是 kimi-k3.1-pro 行，若标题沿用口语名，
    # 模型会照抄并断言"百炼模型 ID 是 kimi-k3.1"（2026-11-09 实测事故）。
    official_ids = sorted({_official_id(r["model_id"]) for r in hits if _official_id(r["model_id"])})
    display = token
    if official_ids:
        display = token if token in official_ids else min(official_ids, key=len)
    id_note = ""
    if display != token:
        others = [i for i in official_ids if i != display]
        id_note = (
            f"\n\n官方模型 ID：`{display}`（问题里的 `{token}` 对应此型号；"
            "回答模型名/模型 ID 时以此为准，不得简写或另造）"
            + ("；同族另有：" + "、".join(f"`{i}`" for i in others[:3]) if others else "")
        )
    # 视频/图像模型按秒/按张计费：直接出「分辨率 × 单价」表，不套用 LLM 列。
    # 强拉进输入/输出/缓存六列会让标题（每 1M tokens）与数值（每秒）互相矛盾，
    # 丢失分辨率与单位，模型只能靠推理猜哪行属于哪个型号。
    media = _media_rows_from_main(hits, token)
    if media:
        return [
            _render_media_table(
                f"{display} · 官方定价页（按秒/按张计费 USD）", media
            )
            + id_note
        ]
    sg = [r for r in hits if r["region"] == "Singapore"]
    bj = [r for r in hits if r["region"] == "China (Beijing)"]
    selected = sg + bj or hits[:4]

    table_rows: list[tuple] = []
    all_rows: list[tuple[tuple, bool]] = []  # (六元组行, 是否带 scope 标注)
    seen: set = set()
    has_cc = False
    for r in selected[:8]:
        cells = r["cells"]
        first = cells[0].lower()
        # 口径：Batch 折扣/批次价一律忽略——带折扣标记的行整行剔除（避免把折扣后价格当常规价）
        if re.search(r"\d+%\s*batch|batch inference discount", first):
            continue
        cc = "context caching discount" in first
        has_cc = has_cc or cc
        roles = _col_roles(r.get("header_cells") or [])

        def _cell(role: str) -> str:
            i = roles.get(role)
            return cells[i] if i is not None and i < len(cells) else ""

        scope = _cell("scope").strip()
        input_cell, output_cell = _cell("input"), _cell("output")
        cache_w_cell = _cell("cache_write")

        # kimi 系：Cached input 数值内嵌在输入价单元格
        cache_in = ""
        mi = re.search(r"Cached input:\s*\$([\d.]+)", input_cell, re.I)
        if mi:
            cache_in = f"${mi.group(1)}"
        if not cache_in and roles.get("cache_input") is not None:
            cache_in = _first_price(_cell("cache_input"))
        cache_w = _first_price(cache_w_cell) if cache_w_cell else ""

        notes = []

        # busy/idle 双价在同一格（DeepSeek 系）→ 拆两行
        busy_i = re.search(r"Busy hours:\s*\$([\d.]+)", input_cell, re.I)
        idle_i = re.search(r"Idle hours:\s*\$([\d.]+)", input_cell, re.I)
        variants: list[tuple[str, str, str]] = []
        if busy_i and idle_i:
            busy_o = re.search(r"Busy hours:\s*\$([\d.]+)", output_cell, re.I)
            idle_o = re.search(r"Idle hours:\s*\$([\d.]+)", output_cell, re.I)
            variants = [
                ("busy hours", f"${busy_i.group(1)}", f"${busy_o.group(1)}" if busy_o else ""),
                ("idle hours", f"${idle_i.group(1)}", f"${idle_o.group(1)}" if idle_o else ""),
            ]
        else:
            variants = [("", _first_price(input_cell), _first_price(output_cell))]

        for qual, ip, op in variants:
            if not ip and not op:
                continue
            label = f"{r['region']} · {scope}" if scope else r["region"]
            if qual:
                label = f"{label} · {qual}" if label else qual
            key = (label, ip, op, cache_in, cache_w)
            if key in seen:
                continue
            seen.add(key)
            all_rows.append(
                (
                    (
                        label,
                        ip or "—",
                        cache_in or "—",
                        op or "—",
                        cache_w or "—",
                        "；".join(notes) or "—",
                    ),
                    bool(scope),
                )
            )

    # 同 region 同价且同备注的无 scope 行若已被带 scope 行覆盖 → 丢弃；
    # 备注不同（如 batch 折扣档）则保留，避免吞掉分档信息
    scoped_prices = {
        (r[0].split(" · ")[0], r[1], r[2], r[3], r[4], r[5]) for r, sc in all_rows if sc
    }
    table_rows = [
        r
        for r, sc in all_rows
        if sc
        or (r[0].split(" · ")[0], r[1], r[2], r[3], r[4], r[5]) not in scoped_prices
    ]

    if not table_rows:
        return []
    block = _render_price_table(
        f"{display} · 官方定价页（每 1M tokens USD）", table_rows
    ) + id_note
    # 支持缓存折扣但主表未给命中单价（DeepSeek/Qwen 系常态）→ 附官方规则，防 LLM 臆造
    if has_cc and not any(r[2] != "—" for r in table_rows):
        i = _CACHE_RULE_POS.get("rule")
        if i:
            rule = re.sub(r"\s+", " ", _CACHE_RULE_POS["page"])[i : i + 500]
            m1 = (
                re.search(r"[^.;]*cache[^.;]*%[^.;]*[.;]", rule, re.I)
                or re.search(r"[^.;]*cache[^.;]*[.;]", rule, re.I)
            )
            snippet = m1.group(0).strip() if m1 else rule[:180].strip()
            block += (
                "\n\n注：该模型 intl 主表未单列缓存命中/显式创建单价"
                f"（仅 context caching discount 标记）。官方规则节选：{snippet} "
                "具体单价以官方页为准，禁止估算。"
            )
    return [block]


def _find_windows(page_text: str, token: str, width: int = 300, max_windows: int = 2) -> list[str]:
    """（兜底用）在纯文本中定位模型 token 附近的上下文窗口"""
    windows: list[str] = []
    last_end = -1
    for m in re.finditer(re.escape(token), page_text, re.IGNORECASE):
        if m.start() <= last_end:
            continue
        s = max(0, m.start() - width // 3)
        e = min(len(page_text), m.end() + width)
        windows.append(page_text[s:e].strip())
        last_end = e
        if len(windows) >= max_windows:
            break
    return windows


# ──────────────────── 校验主入口 ────────────────────


async def verify_price_for(model: str, competitor: str = "") -> dict:
    """工具入口：给定型号（口语写法可）与可选竞品厂商，产出价格证据块。

    与旧 verify_prices（已删）的区别：型号与竞品由调用方（LLM 工具调用）
    显式给出，不再从问题文本做正则提取——意图理解交给模型，证据链留在
    代码。型号归一复用 extract_model_names，归一失败时用原词当 token
    直接匹配主表（不猜、不吞）。

    返回:
        {
          "status":     "official" | "web" | "none",
          "models":     [归一后的模型名],
          "evidence_md": 证据块 markdown（回填给 role:tool 消息），
          "official_md": 官方证据（输出侧价格审计的白名单），
          "competitor_md": 竞品证据（审计白名单，非阿里云口径），
          "competitor":  竞品名或空串,
          "sources":    [{title, url, kind}],
          "checked_at":  核实时间 ISO
        }
    """
    models = extract_model_names(model)
    if not models:
        token = (model or "").strip().lower()
        models = [token] if token else []

    checked_at = datetime.now().astimezone().isoformat(timespec="seconds")
    sources: list[dict] = []
    official_blocks: list[str] = []
    web_blocks: list[str] = []
    need_main_page_models: list[str] = []  # 详情页未命中、回退主定价页的模型

    # 〇级证据：模型详情页（含分辨率分档/缓存等细项价，优先）
    for m in models:
        if m == "qwen":  # 泛化 token，无详情页
            need_main_page_models.append(m)
            continue
        # 口语型号与官方 slug 不完全一致：wan3.0-prime 的实际页面是
        # wan3-0-video-prime；裸版本号（wan3.0）则同时对应 video 与 video-prime。
        bare_version = bool(re.fullmatch(r"wan[\d.]+", m))
        got = False
        for slug in _slug_candidates(m):
            url = f"https://www.alibabacloud.com/help/en/model-studio/{slug}"
            try:
                html = await _cached_fetch(f"model_{slug}", url)
            except Exception as e:
                log.warning("模型详情页抓取失败 %s: %s", url, e)
                html = ""
            if not html:
                continue
            text = _strip_tags(html)
            # 视频/图像：按秒/按张计费（分辨率分档），与 token 计费分开渲染
            media = _parse_media_pricing(text)
            if media:
                model_id = _id_from_slug(slug)
                official_blocks.append(
                    f"#### {model_id} · 模型详情页定价（按秒/按张计费 · 权威）\n"
                    f"来源链接（回答时**直接引用此 URL**，不要自己拼接）：{url}"
                )
                official_blocks.extend(_media_evidence(model_id, media))
                sources.append(
                    {
                        "title": f"{model_id} 模型详情页（分辨率分档价 · 权威）",
                        "url": url,
                        "kind": "official",
                    }
                )
                got = True
                if not bare_version:
                    break
                continue
            pricing = _parse_model_pricing(text)
            if pricing:
                official_blocks.append(
                    f"#### {m} · 模型详情页定价（权威，优先于主定价页）"
                )
                official_blocks.extend(_detail_evidence(m, url, pricing))
                sources.append(
                    {
                        "title": f"{m} 模型详情页（含缓存价 · 权威）",
                        "url": url,
                        "kind": "official",
                    }
                )
                got = True
                break
        if not got:
            need_main_page_models.append(m)

    # 一级证据：官方定价页主表（详情页未命中时）
    html = await _get_pricing_html()
    if html and need_main_page_models:
        rows = _parse_pricing_rows(html)
        for m in need_main_page_models:
            official_blocks.extend(_model_evidence(rows, m))
        text = _strip_tags(html)
        if not any("模型详情页定价" in b for b in official_blocks):
            # 详情页全未命中时才回退 v1 文本窗口
            if not official_blocks:
                for m in need_main_page_models:
                    for w in _find_windows(text, m):
                        official_blocks.append(f"- 【{m}】…{w}…")
        # 命中忙/闲分时价格时，附带官方的忙时时间段定义（不然回答有价无时段）
        if any("busy" in b.lower() for b in official_blocks):
            i = text.lower().find("busy hours are")
            if i >= 0:
                official_blocks.append(
                    "- 【忙/闲时段官方定义】" + text[max(0, i - 60) : i + 260].strip()
                )
        if official_blocks and need_main_page_models:
            sources.append(
                {
                    "title": "Model Studio 官方定价页（国际站 · 权威）",
                    "url": PRICE_PAGE_URL,
                    "kind": "official",
                }
            )

    # 二级证据：搜索旁证。官方证据已就绪时跳过（官方页更权威，且 web_search 单次 12-14s，
    # 跳过可把价格题核实耗时从 ~25s 降到秒级）；仅官方证据缺失时用作兜底
    web_results = []
    if not official_blocks:
        queries = [f"{m} alibabacloud model studio pricing" for m in models]
        if not queries:
            queries = ["阿里云百炼 模型 定价 pricing"]
        web_results = await asyncio.gather(
            *[web_search(q, max_results=3) for q in queries[:3]]
        )
    for results in web_results:
        for r in results:
            snippet = (r.get("snippet") or "").strip()
            if not snippet:
                continue
            web_blocks.append(
                f"- [{r.get('title', '')}]({r.get('url', '')}): {snippet[:300]}"
            )
            sources.append(
                {
                    "title": (r.get("title") or "搜索结果")[:60],
                    "url": r.get("url", ""),
                    "kind": "web",
                }
            )

    # 竞品比价（腾讯云/火山/百度/AWS 等）：对比对象不在自家定价页上，因此即使
    # official 证据已就绪也必须额外比对；结果只作对比参考，绝不充当阿里云报价依据。
    # 口径要求（用户明确）：必须用对方国际站的美金定价来比，而不是中国站人民币价。
    # v3：competitor 由工具调用方显式传入（enum 白名单），不再从问题正则识别。
    competitor_blocks: list[str] = []
    if competitor:
        # ① 优先直抓国际站官方定价页（静态 HTML + USD / 百万 tokens，与阿里云同口径）
        competitor_blocks, c_srcs = await _competitor_official_blocks(competitor, models)
        sources.extend(c_srcs)
        # ② 无官方页可抓时才回退搜索（英文 + USD 路；中文路只给人民币价无法对比）
        if not competitor_blocks:
            en = _COMPETITOR_EN.get(competitor, competitor)
            c_results = await web_search(
                f"{en} pricing USD per million tokens",
                max_results=3,
                thinking_budget=1024,
            )
            seen_c: set[str] = set()
            for r in c_results:
                snippet = (r.get("snippet") or "").strip()
                url = r.get("url", "")
                if not snippet or not url or url in seen_c:
                    continue
                seen_c.add(url)
                competitor_blocks.append(
                    f"- [{r.get('title', '')}]({url}): {snippet[:240]}"
                )
                sources.append(
                    {
                        "title": f"{competitor} · {(r.get('title') or '搜索结果')[:50]}",
                        "url": url,
                        "kind": "web",
                    }
                )

    # 去重 sources
    seen: set[str] = set()
    deduped: list[dict] = []
    for s in sources:
        if s["url"] and s["url"] not in seen:
            seen.add(s["url"])
            deduped.append(s)
    sources = deduped

    status = "official" if official_blocks else ("web" if web_blocks else "none")

    evidence_md = ""
    if official_blocks:
        evidence_md += (
            "### 官方定价页证据（权威 — 具体价格数字仅可引用此处）\n"
            "输出规则：证据块里的「表格部分」（表头行 + 数据行）必须逐字原样输出，"
            "不得改写列名/行序/“—”占位，不得增删行列或自行重组表格；\n"
            "证据块的 `####` 标题行仅供你定位，**不要复制到回答里**；但题目下方的来源 URL 请直接引用，不要自己拼接或改动；\n"
            "若下方资料片段里出现与证据不一致的旧价/折扣价，直接忽略，不要说明、不要比对。\n"
            + "\n".join(official_blocks)
            + "\n\n"
        )
    if web_blocks:
        evidence_md += (
            "### 搜索旁证（仅供交叉参考与时效提示，不得作为报价依据）\n"
            + "\n".join(web_blocks[:8])
            + "\n"
        )
    if competitor_blocks:
        evidence_md += (
            f"### 竞品价格（{competitor} · 国际站 USD / 百万 tokens 口径，第三方信源）\n"
            "优先使用**对方国际站官方定价页**的数字（与阿里云同为 USD / 百万 tokens，可直接对比）；"
            "若这里是搜索摘要，则属于二手转述、可能过期。**任何情况下都不得作为阿里云报价依据**，"
            "引用时必须写明“第三方信源，以对方官网为准，价格可能已过期”，并与阿里云官方价分表对照。\n"
            + "\n".join(competitor_blocks[:14])
            + "\n"
        )
    elif competitor:
        evidence_md += (
            f"### 竞品价格（{competitor}）\n"
            "本次未检索到该国厂商国际站的 USD 公开报价。回答时请说明“未检索到对方国际站近期公开报价”，"
            "并引导以对方国际站官网为准；**不要用人民币价与阿里云 USD 价直接并列比较**，"
            "也不得因竞品价缺失而拒答阿里云自家价格。\n"
        )

    return {
        "status": status,
        "models": models,
        "evidence_md": evidence_md,
        # 仅官方证据（不含 web 旁证）：输出侧价格审计的合法数字白名单。
        # web 旁证按口径不得作报价依据，故不进白名单。
        "official_md": "\n".join(official_blocks),
        # 竞品证据：不是阿里云口径，但出现在回答表格里不应被判为“抄错价”，
        "competitor_md": "\n".join(competitor_blocks),
        "competitor": competitor,
        "sources": sources,
        "checked_at": checked_at,
    }


# ──────────────────── 输出侧价格审计 ────────────────────
# 输入侧再严，模型仍可能把证据表里的 $0.28 抄成 $0.82。前端「已联网核实」徽章
# 只看 price_status=official，会给抄错的答案背书。这里在落库前做确定性比对：
# 回答「表格内」的每个 $ 金额都必须能在官方证据里找到，否则标记 mismatch。
#
# 只审计表格行（以 | 开头）里的 $ 金额，原因：
#   1) prompt 硬约束「价格表逐字原样输出」，表格是 unit price 的唯一合法载体；
#   2) 避开正文里的成本测算（$1.65×100=$165）与人民币换算（¥11.01）——那些是
#      合法计算产物，不是 hallucinated 单价，不应误报。
# 仅比对 $（USD）金额：官方证据统一以 $ 渲染，人民币是计算值不在证据内。
_ANSWER_PRICE_RE = re.compile(r"\$\s*([\d]+(?:\.\d+)?)")


def _norm_amount(s: str) -> str:
    """归一价格数字用于比对：'0.040'→'0.04'、'2.00'→'2'、'100'→'100'。
    只有含小数点时才削尾零，避免把整数 100 误削成 1。"""
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s


def _table_usd_amounts(md: str) -> set[str]:
    """抽取 markdown 表格行（以 | 开头）里的全部 $ 金额，归一后去重。"""
    out: set[str] = set()
    for line in md.splitlines():
        if not line.lstrip().startswith("|"):
            continue
        for m in _ANSWER_PRICE_RE.finditer(line):
            out.add(_norm_amount(m.group(1)))
    return out


# 竞品定价页的价格常写成纯数字（单位“USD / million tokens”放在表头），
# 回答里模型会补上 $，因此 extra 白名单需额外收录这些纯数字单元格。
# 只认“被两个竖线夹住的纯数字格”（如 | 0.003 |），避免把型号里的 4.1、1017 当价。
_EXTRA_DECIMAL_RE = re.compile(r"\|\s*(\d+(?:\.\d+)?)\s*(?=\|)")


def _extra_decimal_amounts(md: str) -> set[str]:
    """从竞品证据里抽纯数字金额（如 0.003），供审计白名单使用。

    注意：竞品证据行带 [自研]/[同款] 标签前缀，不以 | 开头，不能按行首过滤。
    """
    out: set[str] = set()
    for line in md.splitlines():
        if line.count("|") < 3:
            continue
        for m in _EXTRA_DECIMAL_RE.finditer(line):
            out.add(_norm_amount(m.group(1)))
    return out


def audit_answer_prices(answer: str, official_md: str, extra_md: str = "") -> dict:
    """比对回答表格里的 USD 价格是否都来自官方证据（+ 可选额外白名单）。

    extra_md 用于竞品对比场景：竞品价来自第三方搜索，不在 official_md 里，
    但写进表格是允许的，不能因此判为“抄错价/臆造”。

    返回 {"checked": bool, "mismatched": [金额...]}：
      checked=False 表示回答表格里没有 $ 金额（无从比对，不算通过也不算失败）；
      mismatched 非空表示回答里出现了官方证据中不存在的价格（疑似抄错/臆造）。
    """
    answer_prices = _table_usd_amounts(answer)
    if not answer_prices:
        return {"checked": False, "mismatched": []}
    allowed = (
        _table_usd_amounts(official_md)
        | _table_usd_amounts(extra_md)
        | _extra_decimal_amounts(extra_md)
    )
    mismatched = sorted(answer_prices - allowed)
    return {"checked": True, "mismatched": mismatched}
