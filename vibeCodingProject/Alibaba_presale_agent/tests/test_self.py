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
    # v3 工具循环：“是否查价/追问锚定”由 LLM 决策，is_price_question 仅服务
    # 缺型号反问快路径；追问里含型号 → 不反问（交工具循环重查同一型号）
    check("追问含型号 → 不反问（交工具循环）",
          not pv.needs_model_clarify("qwen3.8 flash呢？"))
    check("追问'呢？'含型号仍命中价格意图（反问快路径可用）",
          pv.is_price_question("qwen3.8 flash呢？", hist))
    check("追问'呢？'无历史不触发", not pv.is_price_question("qwen3.8 flash呢？"))
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
    # 未知 kind 排最后且不丢弃
    out2 = pipeline.order_sources([{"kind": "mystery", "url": "u"}, {"kind": "official", "url": "u2"}])
    check("来源: 未知 kind 兜底排末尾",
          [s["kind"] for s in out2] == ["official", "mystery"], str(out2))


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
            s = store.stats()
            check("price_audit: 统计 mismatch 计数=1", s.get("price_audit_mismatch") == 1, str(s))
            items = {it["id"]: it for it in store.list_answers()}
            check("price_audit: 落库值可回读", items[a1]["price_audit"] == "mismatch:0.82")
            check("price_audit: 未审计默认空串", items[a1 + 2]["price_audit"] == "")
            csv_text = store.export_csv()
            check("price_audit: CSV 含表头与值",
                  "price_audit" in csv_text and "mismatch:0.82" in csv_text)
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
            store.init_db()  # 应补 price_audit / thinking / client_ip 等列
            aid = store.insert_answer("s", "Q", "A", [], "official", "m", 1,
                                      price_audit="mismatch:1.23")
            row = store.list_answers()[0]
            check("price_audit: 老库迁移后可写可读",
                  row["id"] == aid and row["price_audit"] == "mismatch:1.23", str(row))
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
    test_price_audit()
    test_followup_anchor_and_competitor()
    test_source_visibility()
    test_pipeline_wiring()
    test_store_price_audit()
    test_fx()
    print("-" * 56)
    print(f"结果: {PASS} 通过 / {FAIL} 失败")
    sys.exit(1 if FAIL else 0)


if __name__ == "__main__":
    main()
