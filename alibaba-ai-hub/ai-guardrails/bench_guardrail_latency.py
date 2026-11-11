"""AI 安全护栏对 LLM 服务指标影响实测 — TTFT / 输出速度 / 总耗时

问题（2026-11-11）：自建网关接入护栏后，大模型 TTFT、输出 token/s 等指标
受影响多少？费用按什么计？

实测设计（glm-5.3 百炼北京，流式）：
  micro  护栏 API 自身延迟：standard vs hp 高性能版 × 短文本/长文本
  A      基线：直连流式，无护栏
  B      输入侧同步检测（query_security_check）+ 流式直出
  C      输入检测 + 输出全量缓冲检测（攒完再检再放行，最保守网关）
  D      输入检测 + 流式切片检测（response_security_check_hp，
         每 100 可见字符一切片，chatId+done 关联，检过才透出）

指标：TTFT（首个可见 content token）、总耗时、可见输出速度（字符/s）、
      模型生成速度（completion tokens/s，含强制推理）、护栏附加延迟。
费用：API 按次计费（15 元/万次/维度），流式每切片 = 1 次独立调用。
成本硬上限：80 次检测 + 20 次 LLM，预估 < 0.5 元。
"""
import json
import statistics
import sys
import time
import uuid

sys.path.insert(0, __file__.rsplit("/", 1)[0])
import test_guardrail_custom_keyword as t  # 复用 .env 加载与双客户端
from alibabacloud_green20220302 import models as guard_models
from openai import OpenAI

MAX_GUARD = 80
MAX_LLM = 20
guard_n = 0
llm_n = 0
llm_tokens = {"prompt": 0, "completion": 0}
guard_latencies = []  # (service, 文本长度, ms)

PROMPT = "写一段200字左右的杭州介绍，涵盖西湖、美食与数字经济。"
SHORT_TEXT = "我是画地为牢啊，PPIO"
LONG_TEXT = ("杭州是浙江省省会，西湖闻名遐迩，龙井虾仁与片儿川令人回味，"
             "数字经济蓬勃发展，是一座历史与现代交融的城市。") * 30  # ~1900 字符
SLICE_CHARS = 100
RUNS = 4


def guard_check(service, content, chat_id=None, done=None):
    global guard_n
    if guard_n >= MAX_GUARD:
        raise SystemExit("❌ 达到检测硬上限，终止")
    guard_n += 1
    params = {"content": content, "dataId": uuid.uuid4().hex}
    if chat_id:
        params["chatId"] = chat_id
        params["sessionId"] = chat_id
    if done is not None:
        params["done"] = done
    req = guard_models.MultiModalGuardRequest(service=service,
                                              service_parameters=json.dumps(params))
    t0 = time.perf_counter()
    resp = t.guard.multi_modal_guard_with_options(req, t.RUNTIME)
    ms = (time.perf_counter() - t0) * 1000
    body = resp.body.to_map()
    if body.get("Code") != 200:
        print(f"  ⚠️ 护栏调用异常 Code={body.get('Code')} Msg={body.get('Message')}")
    guard_latencies.append((service, len(content), ms))
    return (body.get("Data") or {}).get("Suggestion", "?"), ms


def micro_bench():
    print("=" * 25, "micro: 护栏 API 自身延迟", "=" * 25)
    for svc in ("response_security_check", "response_security_check_hp"):
        for tag, text in (("短文本13字", SHORT_TEXT), ("长文本1900字", LONG_TEXT[:1900])):
            lats = []
            for _ in range(6):
                _, ms = guard_check(svc, text)
                lats.append(ms)
            print(f"  {svc:32s} {tag}: avg={statistics.mean(lats):.0f}ms "
                  f"p50={statistics.median(lats):.0f}ms max={max(lats):.0f}ms")


def stream_llm(mode):
    """按模式跑一次流式请求，返回指标 dict。mode ∈ A/B/C/D"""
    global llm_n
    if llm_n >= MAX_LLM:
        raise SystemExit("❌ 达到 LLM 硬上限，终止")
    llm_n += 1
    client = OpenAI(api_key=t.LLM_KEY, base_url=t.LLM_URL, timeout=180)
    input_guard_ms = 0.0
    out_guard_ms = 0.0
    slice_n = 0
    chat_id = uuid.uuid4().hex

    t0 = time.perf_counter()
    if mode in ("B", "C", "D"):
        _, input_guard_ms = guard_check("query_security_check", PROMPT)

    resp = client.chat.completions.create(
        model="glm-5.3", max_tokens=2048, temperature=0, stream=True,
        stream_options={"include_usage": True},
        messages=[{"role": "user", "content": PROMPT}])

    first_any = first_content = last_content = None
    visible = []
    pending = ""
    usage = None

    def release(text):
        nonlocal first_content, last_content
        now = time.perf_counter()
        if first_content is None:
            first_content = now
        last_content = now
        visible.append(text)

    for chunk in resp:
        now = time.perf_counter()
        if chunk.usage:
            usage = chunk.usage
        if not chunk.choices:
            continue
        delta = chunk.choices[0].delta
        piece = getattr(delta, "content", None)
        if not piece:
            if first_any is None and getattr(delta, "reasoning_content", None):
                first_any = now
            continue
        if first_any is None:
            first_any = now
        if mode in ("A", "B"):
            release(piece)
        elif mode == "C":
            pending += piece  # 全量缓冲，最后统一检测
        elif mode == "D":
            pending += piece
            while len(pending) >= SLICE_CHARS:
                slice_text, pending = pending[:SLICE_CHARS], pending[SLICE_CHARS:]
                sug, ms = guard_check("response_security_check_hp", slice_text,
                                      chat_id=chat_id, done=False)
                out_guard_ms += ms
                slice_n += 1
                if sug == "block":
                    pending = ""
                    break
                release(slice_text)
    t_gen_end = time.perf_counter()

    if mode == "C":
        full = pending
        sug, ms = guard_check("response_security_check", full)
        out_guard_ms += ms
        slice_n = 1
        if sug != "block":
            release(full)
    elif mode == "D" and pending:
        sug, ms = guard_check("response_security_check_hp", pending,
                              chat_id=chat_id, done=True)
        out_guard_ms += ms
        slice_n += 1
        if sug != "block":
            release(pending)
    t_end = time.perf_counter()

    if usage:
        llm_tokens["prompt"] += usage.prompt_tokens
        llm_tokens["completion"] += usage.completion_tokens
    vis_chars = sum(len(x) for x in visible)
    ttft = (first_content - t0) if first_content else None
    total = t_end - t0
    gen_span = (last_content - first_content) if (first_content and last_content and last_content > first_content) else None
    return {
        "mode": mode,
        "ttft_s": ttft,
        "first_any_s": (first_any - t0) if first_any else None,
        "total_s": total,
        "vis_chars": vis_chars,
        "vis_chars_per_s": (vis_chars / gen_span) if gen_span else None,
        "completion_tokens": usage.completion_tokens if usage else None,
        "gen_tokens_per_s": (usage.completion_tokens / (t_gen_end - t0)) if usage else None,
        "input_guard_ms": input_guard_ms,
        "out_guard_ms": out_guard_ms,
        "slices": slice_n,
    }


def fmt(v, unit=""):
    return f"{v:.2f}{unit}" if isinstance(v, (int, float)) else "N/A"


def main():
    micro_bench()
    results = {m: [] for m in "ABCD"}
    for mode in "ABCD":
        print(f"\n{'=' * 25} 模式 {mode} × {RUNS} 次 {'=' * 25}")
        for i in range(RUNS):
            r = stream_llm(mode)
            results[mode].append(r)
            print(f"  #{i+1} TTFT={fmt(r['ttft_s'],'s')} 总耗时={fmt(r['total_s'],'s')} "
                  f"可见={r['vis_chars']}字 可见速度={fmt(r['vis_chars_per_s'],'字/s')} "
                  f"生成={fmt(r['gen_tokens_per_s'],'tok/s')} "
                  f"护栏入={r['input_guard_ms']:.0f}ms 出={r['out_guard_ms']:.0f}ms 切片={r['slices']}")

    print("\n" + "=" * 25, "汇总（4 次平均）", "=" * 25)
    base = results["A"]
    base_ttft = statistics.mean(r["ttft_s"] for r in base)
    base_total = statistics.mean(r["total_s"] for r in base)
    base_speed = statistics.mean(r["vis_chars_per_s"] for r in base if r["vis_chars_per_s"])
    for mode in "ABCD":
        rs = results[mode]
        ttft = statistics.mean(r["ttft_s"] for r in rs)
        total = statistics.mean(r["total_s"] for r in rs)
        speeds = [r["vis_chars_per_s"] for r in rs if r["vis_chars_per_s"]]
        speed = statistics.mean(speeds) if speeds else 0
        print(f"  模式{mode}: TTFT={ttft:.2f}s (Δ{ttft-base_ttft:+.2f}s) "
              f"总耗时={total:.2f}s (Δ{total-base_total:+.2f}s) "
              f"可见速度={speed:.1f}字/s ({(speed/base_speed-1)*100:+.0f}%)")

    print("\n" + "=" * 25, "成本估算", "=" * 25)
    print(f"  护栏检测 {guard_n} 次（标准+hp，按 15 元/万次/维度，双维度开启）≈ {guard_n*0.003:.3f} 元")
    print(f"  glm-5.3 {llm_n} 次 tokens={llm_tokens} ≈ <0.2 元")
    with open(__file__.rsplit("/", 1)[0] + "/bench_guardrail_latency_raw.json", "w") as f:
        json.dump({"results": results, "guard_latencies": guard_latencies,
                   "llm_tokens": llm_tokens}, f, ensure_ascii=False, indent=2)
    print("  原始数据已存 bench_guardrail_latency_raw.json")


if __name__ == "__main__":
    main()