"""测试百炼 decision-model-preview（决策模型，System One 协议）— 实测适用场景

背景（2026-10-09，官方文档 https://help.aliyun.com/zh/model-studio/decision-model-preview）：
  面向高频业务判断的结构化决策模型，一次前向并行完成分类(choice)/是非(noul)/评分(score)，
  返回概率分布与置信度，不生成文本，延迟与成本与输出长度无关。限时免费。

本脚本实测维度：
  Case 1  工单分流组合决策（choice + noul + score 一次请求，官方主场景）
  Case 2  内容审核（一条评论并行跑多条审核规则，全 noul）
  Case 3  智能体路由（choice 含 other 兜底 + 嵌套结构化 state）
  Case 4  评分场景（客服对话质检 score，验证概率加权期望的非整数输出）
  Case 5  概率校准（模糊/边界输入，看 probabilities 分布是否合理）
  Case 6  延迟基准（20 次采样 P50/P95/P99，与同端点 qwen3.7-plus chat 对照）
  Case 7  边界行为（错误问题类型 / 超长选项描述等容错性）

端点实测结论（先期 curl 验证）：
  - workspace 专属域名 ✅（北京 llm-7ufq8xadyf99jlbp / 新加坡 llm-ablnum2bgfvl34hs 均通）
  - 标准 DashScope 端点 dashscope.aliyuncs.com/compatible-mode/v1/systemone ❌ 404
    —— 与通用 LLM 相反：通用 LLM 需标准端点（workspace 域名不支持），
       决策模型只支持 workspace 域名（标准端点 404）。

端点与凭证：DASHSCOPE_API_KEY_CN_TEST + DASHSCOPE_API_KEY_CN_URL（.env，sk-ws- 前缀）
"""
import json
import os
import time
import urllib.request

# ---------- 环境加载（.env 已被 .gitignore 忽略，密钥不会进 Git） ----------
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("DASHSCOPE_API_KEY_CN_TEST", "").strip()
BASE = os.getenv("DASHSCOPE_API_KEY_CN_URL", "").strip().rstrip("/") \
    or "https://llm-7ufq8xadyf99jlbp.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"
SYSTEMONE_URL = f"{BASE}/systemone"
CHAT_URL = f"{BASE}/chat/completions"
MODEL = "decision-model-preview"


def http_post(url, payload, timeout=60):
    """裸 HTTP POST，返回 (status, body_dict_or_text)"""
    req = urllib.request.Request(
        url,
        data=json.dumps(payload).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {API_KEY}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            body = json.loads(resp.read().decode("utf-8"))
            return resp.status, body, (time.time() - t0) * 1000
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode("utf-8", "replace"), (time.time() - t0) * 1000


def systemone(state, questions, label=""):
    """调用 System One 协议并打印结果摘要"""
    status, body, client_ms = http_post(SYSTEMONE_URL, {
        "model": MODEL, "state": state, "questions": questions,
    })
    print(f"\n{'=' * 16} {label} {'=' * 16}")
    if status != 200:
        print(f"[HTTP {status}] {str(body)[:300]}")
        return None
    for qid, ans in body.get("answers", {}).items():
        t = ans.get("type")
        if t == "choice":
            probs = ans.get("probabilities", {})
            top2 = sorted(probs.items(), key=lambda x: -x[1])[:3]
            print(f"  {qid:14s} choice={ans['choice']:12s} conf={ans.get('confidence')} "
                  f"probs={ {k: round(v, 3) for k, v in top2} }")
        elif t == "noul":
            print(f"  {qid:14s} noul P(yes)={ans['noul']}")
        elif t == "score":
            probs = ans.get("probabilities", {})
            print(f"  {qid:14s} score={ans['score']} (期望值) conf={ans.get('confidence')} "
                  f"probs={ {k: round(v, 2) for k, v in probs.items()} }")
    print(f"  [usage] input_tokens={body.get('usage', {}).get('input_tokens')} "
          f"server_latency={body.get('latency_ms')}ms client={client_ms:.0f}ms")
    return body


# ---------------- Case 1: 工单分流（官方主场景复刻） ----------------
def case1_ticket_triage():
    return systemone(
        state={"ticket_id": "T-1001",
               "content": "订单支付后超过 24 小时仍未到账，用户无法继续使用核心服务，要求立即处理。"},
        questions={
            "department": {"type": "choice", "instructions": "应该由哪个团队处理？",
                           "criteria": {"billing": "支付、退款和账单问题",
                                        "technical": "产品故障和集成问题",
                                        "other": "以上都不是"}},
            "escalate": {"type": "noul", "instructions": "是否需要立即通知值班人员？"},
            "severity": {"type": "score", "instructions": "这个问题有多严重？",
                         "criteria": ["轻微问题，不影响功能", "部分功能受影响，但存在替代方案",
                                      "核心功能不可用，没有替代方案", "造成严重业务或安全影响"]},
        },
        label="Case 1 工单分流: choice+noul+score 一次前向",
    )


# ---------------- Case 1b: 对照验证 — 去掉 other 兜底选项 ----------------
def case1b_no_other():
    # Case 1 实测 other 兜底选项以 0.79 概率"吸走"了本应归 billing 的工单
    # （官方示例无 other 时 billing=0.94）。去掉 other 验证该干扰效应。
    return systemone(
        state={"ticket_id": "T-1001",
               "content": "订单支付后超过 24 小时仍未到账，用户无法继续使用核心服务，要求立即处理。"},
        questions={
            "department": {"type": "choice", "instructions": "应该由哪个团队处理？",
                           "criteria": {"billing": "支付、退款和账单问题",
                                        "technical": "产品故障和集成问题"}},
        },
        label="Case 1b 对照: 同工单去掉 other 兜底",
    )


# ---------------- Case 2: 内容审核（并行多条 noul 规则） ----------------
def case2_content_moderation():
    comment = "你们这个产品就是垃圾，我花了 399 买了个废物！客服只会踢皮球，"
    "再不解决问题我就去 12315 投诉，把聊天记录全发到网上去！"
    return systemone(
        state={"platform": "电商评论区", "comment": comment},
        questions={
            "toxic":       {"type": "noul", "instructions": "是否包含辱骂或人身攻击？"},
            "refund":      {"type": "noul", "instructions": "是否在索要退款？"},
            "legal_risk":  {"type": "noul", "instructions": "是否存在投诉/曝光等升级风险？"},
            "off_topic":   {"type": "noul", "instructions": "是否与平台商品或服务无关？"},
            "spam":        {"type": "noul", "instructions": "是否是广告或水军刷评？"},
        },
        label="Case 2 内容审核: 一条评论并行 5 条规则",
    )


# ---------------- Case 3: 智能体路由（choice + 嵌套结构化 state） ----------------
def case3_agent_routing():
    return systemone(
        state={"session": {"user_id": "u-8823", "vip_level": 3},
               "history_summary": "用户先问了发票抬头修改，未解决；现在追问上月的账单异常扣费。",
               "latest_message": "那笔多扣的 29 块钱到底什么时候退给我？",
               "available_agents": {"billing_agent": "账单/扣费/退款", "invoice_agent": "发票相关",
                                    "tech_agent": "产品故障", "human_agent": "转人工"}},
        questions={
            "route_to": {"type": "choice",
                         "instructions": "下一条消息应该路由给哪个 agent？",
                         "criteria": {"billing_agent": "账单、扣费、退款问题",
                                      "invoice_agent": "发票相关",
                                      "tech_agent": "产品故障",
                                      "human_agent": "情绪激动或多次未解决，转人工"}},
            "is_angry": {"type": "noul", "instructions": "用户当前情绪是否激动/不满？"},
        },
        label="Case 3 智能体路由: 嵌套state + choice(5选项)",
    )


# ---------------- Case 4: 评分场景（客服质检） ----------------
def case4_quality_scoring():
    return systemone(
        state={"dialog": [
            {"agent": "您好，请问有什么可以帮您？"},
            {"user": "我的会员积分没有到账，三天了。"},
            {"agent": "您别着急，我这边看到您的积分因为系统延迟还没入账，"
                      "我已经帮您加急登记了，预计 24 小时内到账，到账后短信通知您。"},
        ]},
        questions={
            "resolution": {"type": "score", "instructions": "客服是否有效解决了用户问题？",
                           "criteria": ["完全没有解决", "敷衍推诿", "给了临时方案但未根治",
                                        "基本解决", "彻底解决并有主动跟进"]},
            "empathy": {"type": "score", "instructions": "共情与态度得分？",
                        "criteria": ["态度冷漠", "态度一般", "态度良好", "非常贴心"]},
        },
        label="Case 4 客服质检: 双维度 score 量表",
    )


# ---------------- Case 5: 概率校准（模糊输入） ----------------
def case5_calibration():
    # 边界模糊案例：介于两选项之间、似是而非的是非题
    return systemone(
        state="用户说：'这个东西还行吧，就是有点贵，我再考虑考虑。'",
        questions={
            "sentiment": {"type": "choice", "instructions": "用户情感倾向？",
                          "criteria": {"positive": "明确满意", "neutral": "中立观望",
                                       "negative": "明确不满"}},
            "will_buy": {"type": "noul", "instructions": "用户是否表达了购买意愿？"},
            "price_objection": {"type": "noul", "instructions": "是否因价格产生犹豫？"},
        },
        label="Case 5 概率校准: 模糊输入的分布行为",
    )


# ---------------- Case 5b: 边界模糊输入校准（对立证据并存） ----------------
def case5b_ambiguous():
    # 正负证据并存的句子：贵（负）+ 质量好（正）。理想校准应给出
    # 接近 50/50 或至少平滑的分布，而非极端值。
    return systemone(
        state="用户评价：'这东西确实不便宜，但质量是真的好，用了一年没出过毛病。'",
        questions={
            "sentiment": {"type": "choice", "instructions": "评价的情感倾向？",
                          "criteria": {"positive": "总体满意", "negative": "总体不满"}},
            "would_recommend": {"type": "noul", "instructions": "用户是否可能推荐该商品？"},
        },
        label="Case 5b 校准: 正负证据并存的句子",
    )


# ---------------- Case 6: 延迟基准（决策模型 vs 通用 LLM chat） ----------------
def case6_latency():
    print(f"\n{'=' * 16} Case 6 延迟基准 {'=' * 16}")
    state = {"content": "客户来电反映 App 登录后闪退，重装无效，会员账号无法使用。"}
    questions = {
        "department": {"type": "choice", "instructions": "应该由哪个团队处理？",
                       "criteria": {"billing": "支付、退款和账单问题",
                                    "technical": "产品故障和集成问题"}},
        "escalate": {"type": "noul", "instructions": "是否需要立即通知值班人员？"},
        "severity": {"type": "score", "instructions": "严重程度？",
                     "criteria": ["轻微", "中等", "严重", "危急"]},
    }
    # 6.1 决策模型 20 次采样
    latencies = []
    for i in range(20):
        status, body, client_ms = http_post(SYSTEMONE_URL,
                                            {"model": MODEL, "state": state, "questions": questions})
        if status == 200:
            latencies.append(body.get("latency_ms", client_ms))
        time.sleep(0.05)
    latencies.sort()
    p50 = latencies[len(latencies) // 2]
    p95 = latencies[int(len(latencies) * 0.95)]
    print(f"  decision-model-preview ×20: server_latency P50={p50:.0f}ms P95={p95:.0f}ms "
          f"min={latencies[0]:.0f} max={latencies[-1]:.0f}")

    # 6.2 对照组：同端点 qwen3.7-plus 用 chat completions 完成同样三问（要求 JSON 输出）
    prompt = (
        "你是工单分诊器。根据工单内容输出 JSON："
        '{"department": "billing|technical", "escalate": true|false, '
        '"severity": 0-3}。工单：客户来电反映 App 登录后闪退，重装无效，会员账号无法使用。'
        "只输出 JSON。"
    )
    chat_latencies = []
    for i in range(5):
        status, body, client_ms = http_post(CHAT_URL, {
            "model": "qwen3.7-plus",
            "messages": [{"role": "user", "content": prompt}],
            "max_tokens": 200,
            "enable_thinking": False,  # 关思考保证与决策模型公平对比
        })
        if status == 200:
            # chat 耗时用客户端口径（首包-末包不可细分，urllib 非流式）
            chat_latencies.append(client_ms)
        else:
            print(f"  [chat 对照组 HTTP {status}] {str(body)[:200]}")
        time.sleep(0.2)
    if chat_latencies:
        chat_latencies.sort()
        print(f"  qwen3.7-plus(chat)     ×5: client_latency P50={chat_latencies[len(chat_latencies)//2]:.0f}ms "
              f"max={chat_latencies[-1]:.0f}ms (含文本生成，输出解析需自行处理)")
    return latencies, chat_latencies


# ---------------- Case 7: 边界行为容错 ----------------
def case7_edge_cases():
    print(f"\n{'=' * 16} Case 7 边界行为 {'=' * 16}")
    # 7.1 非法问题类型
    status, body, ms = http_post(SYSTEMONE_URL, {
        "model": MODEL,
        "state": "测试",
        "questions": {"bad": {"type": "unknown_type", "instructions": "?"}},
    })
    print(f"  非法type:    HTTP {status} → {str(body)[:150]}")
    # 7.2 空 state
    status, body, ms = http_post(SYSTEMONE_URL, {
        "model": MODEL, "state": "", "questions": {"x": {"type": "noul", "instructions": "是吗"}},
    })
    print(f"  空 state:    HTTP {status} → {str(body)[:150]}")
    # 7.3 16 个问题并行（官方建议上限）
    questions = {f"q{i}": {"type": "noul", "instructions": f"该内容是否与主题{i % 4}相关？"}
                 for i in range(16)}
    status, body, ms = http_post(SYSTEMONE_URL, {
        "model": MODEL, "state": "用户询问了如何开发票以及会员退款政策。", "questions": questions,
    })
    if status == 200:
        print(f"  16问题并行:  HTTP {status} latency={body.get('latency_ms')}ms "
              f"tokens={body.get('usage', {}).get('input_tokens')}")
    else:
        print(f"  16问题并行:  HTTP {status} → {str(body)[:150]}")
    # 7.4 冒充通用对话（验证"不生成文本"边界）
    status, body, ms = http_post(SYSTEMONE_URL, {
        "model": MODEL, "state": "写一首关于秋天的诗",
        "questions": {"reply": {"type": "noul", "instructions": "请直接写诗"}},
    })
    print(f"  当对话模型用: HTTP {status} → {str(body)[:150]}")


def main():
    print(f"endpoint: {SYSTEMONE_URL}")
    print(f"model:    {MODEL}")
    case1_ticket_triage()
    case1b_no_other()
    case2_content_moderation()
    case3_agent_routing()
    case4_quality_scoring()
    case5_calibration()
    case5b_ambiguous()
    case6_latency()
    case7_edge_cases()
    print("\n全部用例执行完成。")


if __name__ == "__main__":
    main()
