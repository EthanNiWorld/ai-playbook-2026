"""
自测套件 — 离线单测（不调 LLM、不打外部搜索）
运行: .venv/bin/python tests/test_self.py
"""

import asyncio
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
    check(
        "表头列序固定（Cache Write 在 Output 右侧）",
        "| Region | 输入价格 (Input) | 缓存输入价格 (Cache Input) "
        "| 输出价格 (Output) | 显式缓存创建 (Cache Write) | 备注 |" in tb,
    )
    check("SG 行 Cache Input/Write 就位，显式读取进备注",
          "| Singapore | $2 | $0.25 | $6 | $2.5 | 显式缓存读取 $0.17 |" in tb)
    check("Batch 批次价不进备注（口径：一律忽略）", "Batch" not in tb)
    check("busy/idle 按 qualifier 拆行",
          "| China (Beijing) · idle hours | $1.6 | $0.2 | $4.8 | — | — |" in tb
          and "| China (Beijing) · busy hours | $1.65 | $0.206 | $4.951 | — | — |" in tb)

    hist = [
        {"role": "user", "content": "deepseek-v4.1-flash 的价格是多少？"},
        {"role": "assistant", "content": "价格如下..."},
    ]
    check("追问'呢？'触发（历史有价格话题）", pv.is_price_question("qwen3.8 flash呢？", hist))
    check("追问'呢？'无历史不触发", not pv.is_price_question("qwen3.8 flash呢？"))
    check("'价格。'回退历史模型名", pv._models_with_history("价格。", hist) == ["deepseek-v4.1-flash"])
    check("当前句模型名优先于历史", pv._models_with_history("kimi-k3.1-pro呢？", hist) == ["kimi-k3.1-pro"])
    # 当前句提了家族却抽不出型号时，不得挪用历史模型（防拿错模型证据误导回答）
    check("含家族词无型号不挪用历史模型",
          pv._models_with_history("kimi 最新款价格", hist) == [])
    check("口语 'kimi k3.1 pro' 不再回退历史 deepseek",
          pv._models_with_history("kimi k3.1 pro的价格呢？", hist) == ["kimi-k3.1-pro"])
    check("选型对比（无价格历史）不触发", not pv.is_price_question("qwen3.8-max 和 deepseek 哪个强"))


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

        # 代码渲染表格：deepseek 双节点忙闲分档（价格与 region/scope 严格对齐）
        ds_block = pv._model_evidence(rows, "deepseek-v4.1-flash")
        check("deepseek-v4.1-flash 证据非空", len(ds_block) > 0)
        tb = ds_block[0] if ds_block else ""
        check("deepseek Singapore 忙时 $0.3（region/scope 归属正确）",
              "| Singapore · International · busy hours | $0.3 |" in tb, tb[:160])
        check("deepseek Beijing 忙时 $0.283",
              "China (Beijing) · Global · busy hours | $0.283" in tb)
        check("deepseek Cache Input 主表未单列填 —（附官方规则）",
              "官方规则节选" in tb)

        # kimi: Cached input 拆列 + 跨 scope 不挪用 + BJ 重复表合并
        k_tb = pv._model_evidence(rows, "kimi-k3.1-pro")[0]
        check("kimi Cache Input 拆列 $0.184（Global 档）", "| $1.837 | $0.184 |" in k_tb)
        check("kimi US scope 价不挪用（International = $2）",
              "| Singapore · International | $2 | $0.2 |" in k_tb, k_tb[:160])
        check("kimi BJ 重复表结构合并",
              sum(1 for l in k_tb.splitlines() if l.startswith("| China (Beijing)")) == 2)

        # qwen3.8-flash: Beijing 多 scope 分档行保留
        q_tb = pv._model_evidence(rows, "qwen3.8-flash")[0]
        check("qwen3.8-flash BJ 多行分档保留",
              sum(1 for l in q_tb.splitlines() if l.startswith("| China (Beijing)")) >= 2)
        check("qwen3.8-flash batch 折扣行整行忽略", "Batch" not in q_tb, q_tb[:300])

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


def test_fx():
    """实时汇率：解析、意图识别、用户自报优先（踩记录 id=225~230）。"""
    from app import fx

    sina = 'var hq_str_USDCNY="17:49:00,6.6711,6.6713,6.6722,40,6.6700,6.6720,6.6680,6.6713,人民币,2026-11-06";'
    fxrate = 'var hq_str_fx_susdcny="17:49:00,6.6711,6.6713,6.6680,40.0,6.6700,6.6720";'
    check("汇率解析: 新浪 USDCNY 取买卖中间价", abs((fx.parse_sina(sina) or 0) - 6.6712) < 1e-6, str(fx.parse_sina(sina)))
    check("汇率解析: 新浪 fx_susdcny 同格式", abs((fx.parse_sina(fxrate) or 0) - 6.6712) < 1e-6)
    check("汇率解析: 非报价响应返回 None", fx.parse_sina('v_pv_none_match="1";') is None)
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
    check("用户自报汇率: 识别 6.6704", abs((fx.user_given_rate("实时汇率是6.6704") or 0) - 6.6704) < 1e-6)
    check("用户自报汇率: 型号价格题不误抽", fx.user_given_rate("qwen3.8-max 多少钱") is None)
    ev = fx.evidence_md({"rate": 6.6712, "source": "新浪财经", "at": "2026-11-06T17:49:00+08:00"})
    check("汇率证据: 含汇率与换算规则", "6.6712" in ev and "换算规则" in ev)
    check("汇率直接回答: 给出汇率与来源", "6.6712" in fx.direct_answer({"rate": 6.6712, "source": "新浪财经", "at": "2026-11-06T17:49:00+08:00"}))


def main():
    print("=" * 56)
    print("阿里小可爱AI问答助手 — 离线自测套件")
    print("=" * 56)
    test_price_verifier_units()
    test_table_render_and_followup()
    test_price_parsing_offline()
    test_knowledge_retrieval()
    test_store()
    test_guide_lookup()
    test_model_clarify()
    test_fx()
    print("-" * 56)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
