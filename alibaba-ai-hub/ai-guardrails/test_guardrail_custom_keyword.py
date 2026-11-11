"""AI 安全护栏自定义词库拦截测试 — 客户自建 AI 网关场景

背景（2026-11-11）：
  客户自建 AI 网关，需纳入阿里云 AI 安全护栏对 LLM 输入/输出做合规检测。
  验证目标：网关能否拦截模型输出「我是画地为牢啊，PPIO」。
  该短语本身不违规，默认策略不会拦截 → 需通过自定义关键词库实现。

测试链路：
  status   检查服务开通状态 / RAM 权限 / 现有 service 配置
  baseline 默认策略下检测目标短语（预期 pass）
  setup    AddKeywordLib 建词库（关键词：画地为牢）→ 绑定 response_security_check
  verify   复测目标短语（预期 block，Label=customized）
  e2e      glm-5.3（百炼北京）原样输出该短语 → 网关式送检 → 拦截替换代答
  cleanup  恢复 service 原配置并删除测试词库

凭证（均从工作区根 .env 读取，禁止硬编码）：
  Aliyun-AccessKey-ID / Aliyun-AccessKey-Secret   RAM key（需 AliyunYundunGreenWebFullAccess）
  DASHSCOPE_API_KEY_INTL_BJ_TEST / _URL           百炼北京 workspace（glm-5.3）

成本护栏：文本检测 15 元/万次（0.0015 元/次），脚本硬上限 30 次检测 + 6 次 LLM
  调用（max_tokens=100），理论成本 << 1 元，远低于 20 元预算。
"""
import json
import os
import sys
import time
import uuid

from alibabacloud_green20220302.client import Client as GuardClient
from alibabacloud_green20220302 import models as guard_models
from alibabacloud_green20220926.client import Client as ConfigClient
from alibabacloud_green20220926 import models as config_models
from alibabacloud_tea_openapi.models import Config
from alibabacloud_tea_util.models import RuntimeOptions

# ---- .env 加载（向上两级到工作区根） ----
ENV_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), ".env")
if os.path.exists(ENV_PATH):
    with open(ENV_PATH) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

AK = os.getenv("Aliyun-AccessKey-ID", "").strip()
SK = os.getenv("Aliyun-AccessKey-Secret", "").strip()
LLM_KEY = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", "").strip()
LLM_URL = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "").strip()

REGION = os.getenv("GUARDRAIL_REGION", "cn-beijing")
ENDPOINT = os.getenv("GUARDRAIL_ENDPOINT", f"green-cip.{REGION}.aliyuncs.com")
# 配置管理面（2022-09-26 版本 API）仅上海接入点可用，检测面（2022-03-02）走北京
CFG_ENDPOINT = os.getenv("GUARDRAIL_CFG_ENDPOINT", "green-cip.cn-shanghai.aliyuncs.com")
SERVICE = "response_security_check"          # AI 生成内容安全检测（输出侧）
QUERY_SERVICE = "query_security_check"       # AI 输入内容安全检测（输入侧）
TARGET_PHRASE = "我是画地为牢啊，PPIO"
KEYWORD = "画地为牢"                          # 命中即 block 的最小关键词
LIB_NAME = "guardrail-test-ppio"
STATE_FILE = os.path.join(os.path.dirname(__file__), "guardrail_test_state.json")

# ---- 成本硬护栏 ----
MAX_GUARD_CALLS = 30
MAX_LLM_CALLS = 6
guard_calls = 0
llm_calls = 0
llm_tokens = {"prompt": 0, "completion": 0}

RUNTIME = RuntimeOptions(read_timeout=15000, connect_timeout=5000)


def make_client(cls):
    return cls(Config(access_key_id=AK, access_key_secret=SK,
                      region_id=REGION, endpoint=ENDPOINT,
                      read_timeout=15000, connect_timeout=5000))


guard = make_client(GuardClient)
cfg = ConfigClient(Config(access_key_id=AK, access_key_secret=SK,
                          region_id=REGION, endpoint=CFG_ENDPOINT,
                          read_timeout=15000, connect_timeout=5000))


def load_state():
    if os.path.exists(STATE_FILE):
        with open(STATE_FILE) as f:
            return json.load(f)
    return {}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)


def brief(obj, limit=1500):
    s = json.dumps(obj, ensure_ascii=False, default=str)
    return s if len(s) <= limit else s[:limit] + f"...(truncated, total {len(s)})"


def detect(service, content, tag):
    """调用 MultiModalGuard 文本检测，返回 (suggestion, detail_dict)"""
    global guard_calls
    if guard_calls >= MAX_GUARD_CALLS:
        raise SystemExit(f"❌ 达到检测调用硬上限 {MAX_GUARD_CALLS}，终止以控制成本")
    guard_calls += 1
    req = guard_models.MultiModalGuardRequest(
        service=service,
        service_parameters=json.dumps({"content": content, "dataId": uuid.uuid4().hex}),
    )
    t0 = time.time()
    resp = guard.multi_modal_guard_with_options(req, RUNTIME)
    body = resp.body.to_map()
    latency = (time.time() - t0) * 1000
    data = body.get("Data") or {}
    suggestion = data.get("Suggestion", "?")
    print(f"\n[{tag}] service={service} 耗时={latency:.0f}ms Code={body.get('Code')} "
          f"Suggestion={suggestion} (第{guard_calls}次检测)")
    if body.get("Code") != 200:
        print(f"  ⚠️ Message={body.get('Message')} RequestId={body.get('RequestId')}")
    print(f"  内容: {content[:80]!r}")
    print(f"  Detail: {brief(data.get('Detail'), 800)}")
    return suggestion, body


def phase_status():
    print("=" * 30, "status: 开通状态 / 权限 / 现有配置", "=" * 30)
    try:
        r = cfg.get_user_buy_status_with_options(
            config_models.GetUserBuyStatusRequest(region_id=REGION), RUNTIME)
        print("GetUserBuyStatus:", brief(r.body.to_map()))
    except Exception as e:
        print("GetUserBuyStatus 失败:", type(e).__name__, str(e)[:300])
    try:
        r = cfg.list_service_configs_with_options(
            config_models.ListServiceConfigsRequest(region_id=REGION), RUNTIME)
        print("ListServiceConfigs:", brief(r.body.to_map(), 3000))
    except Exception as e:
        print("ListServiceConfigs 失败:", type(e).__name__, str(e)[:300])
    try:
        r = cfg.list_keyword_libs_with_options(
            config_models.ListKeywordLibsRequest(region_id=REGION), RUNTIME)
        print("ListKeywordLibs:", brief(r.body.to_map(), 2000))
    except Exception as e:
        print("ListKeywordLibs 失败:", type(e).__name__, str(e)[:300])


def phase_baseline():
    print("=" * 30, "baseline: 默认策略检测目标短语", "=" * 30)
    detect(SERVICE, TARGET_PHRASE, "基线-输出侧")
    detect(SERVICE, "今天天气不错，适合出门散步。", "基线-正常对照")


def phase_setup():
    print("=" * 30, "setup: 建自定义词库并绑定 service", "=" * 30)
    state = load_state()
    # 1) 记录原配置（用于 cleanup 恢复）
    r = cfg.get_service_config_with_options(
        config_models.GetServiceConfigRequest(
            region_id=REGION, resource_type="text", service_code=SERVICE), RUNTIME)
    orig = r.body.to_map()
    print("GetServiceConfig(原配置):", brief(orig, 3000))
    state["orig_service_config"] = orig
    # 2) 创建关键词库
    r = cfg.add_keyword_lib_with_options(
        config_models.AddKeywordLibRequest(
            region_id=REGION, lib_name=LIB_NAME, keywords=KEYWORD), RUNTIME)
    body = r.body.to_map()
    print("AddKeywordLib:", brief(body))
    lib_id = (body.get("Data") or {}).get("LibId")
    if not lib_id:
        raise SystemExit("❌ 建库失败，终止")
    state["lib_id"] = lib_id
    save_state(state)
    print(f"✅ 词库已创建: {lib_id}（关键词: {KEYWORD}）")
    # 3) 绑定到 response_security_check 的命中词库
    orig_hit = ((orig.get("Data") or {}).get("KeywordHitLibs")) or "[]"
    if isinstance(orig_hit, str):
        hit_libs = json.loads(orig_hit) if orig_hit.strip() else []
    else:
        hit_libs = list(orig_hit)
    state["orig_keyword_hit_libs"] = hit_libs
    new_hit = hit_libs + [lib_id]
    r = cfg.update_service_config_with_options(
        config_models.UpdateServiceConfigRequest(
            region_id=REGION, resource_type="text", service_code=SERVICE,
            keyword_hit_libs=json.dumps(new_hit)), RUNTIME)
    print("UpdateServiceConfig:", brief(r.body.to_map()))
    save_state(state)
    print("✅ 已绑定命中词库，等待约 1 分钟生效后再跑 verify")


def phase_verify():
    print("=" * 30, "verify: 自定义词库生效复测", "=" * 30)
    s1, _ = detect(SERVICE, TARGET_PHRASE, "复测-目标短语")
    s2, _ = detect(SERVICE, "今天天气不错，适合出门散步。", "复测-正常对照")
    s3, _ = detect(SERVICE, "他这种画地为牢的做法，限制了团队的发展。", "复测-关键词变体")
    print(f"\n判定: 目标短语={s1}（预期 block）| 正常文本={s2}（预期 pass）| 变体={s3}（预期 block）")


def llm_chat(prompt):
    global llm_calls
    if llm_calls >= MAX_LLM_CALLS:
        raise SystemExit(f"❌ 达到 LLM 调用硬上限 {MAX_LLM_CALLS}，终止以控制成本")
    llm_calls += 1
    from openai import OpenAI
    client = OpenAI(api_key=LLM_KEY, base_url=LLM_URL, timeout=120)
    resp = client.chat.completions.create(
        model="glm-5.3", max_tokens=100, temperature=0,
        messages=[{"role": "user", "content": prompt}])
    u = resp.usage
    llm_tokens["prompt"] += u.prompt_tokens
    llm_tokens["completion"] += u.completion_tokens
    return resp.choices[0].message.content or ""


def phase_e2e():
    print("=" * 30, "e2e: glm-5.3 北京 → 网关送检 → 拦截", "=" * 30)
    # 场景 1：用户诱导模型输出目标短语
    prompt = f"请原样复述这句话，不要添加任何解释：{TARGET_PHRASE}"
    print(f"\n[场景1] 用户输入: {prompt!r}")
    detect(QUERY_SERVICE, prompt, "e2e-输入侧检测")
    out = llm_chat(prompt)
    print(f"  glm-5.3 原始输出: {out!r}")
    suggestion, _ = detect(SERVICE, out, "e2e-输出侧检测")
    if suggestion == "block":
        print("  🚫 网关动作: 拦截原始输出，替换为代答话术 →「抱歉，该内容无法提供。」")
    else:
        print(f"  ⚠️ 网关动作: 放行（Suggestion={suggestion}，未达预期）")
    # 场景 2：正常请求对照
    prompt2 = "用一句话介绍杭州。"
    print(f"\n[场景2] 用户输入: {prompt2!r}")
    out2 = llm_chat(prompt2)
    print(f"  glm-5.3 原始输出: {out2!r}")
    s2, _ = detect(SERVICE, out2, "e2e-正常输出对照")
    print(f"  网关动作: {'放行 ✅' if s2 == 'pass' else f'意外拦截 ⚠️ ({s2})'}")


def phase_cleanup():
    print("=" * 30, "cleanup: 恢复配置并删除测试词库", "=" * 30)
    state = load_state()
    lib_id = state.get("lib_id")
    if not lib_id:
        print("无测试词库记录，跳过")
        return
    orig_hit = state.get("orig_keyword_hit_libs", [])
    r = cfg.update_service_config_with_options(
        config_models.UpdateServiceConfigRequest(
            region_id=REGION, resource_type="text", service_code=SERVICE,
            keyword_hit_libs=json.dumps(orig_hit)), RUNTIME)
    print("恢复 KeywordHitLibs:", brief(r.body.to_map()))
    r = cfg.delete_keyword_lib_with_options(
        config_models.DeleteKeywordLibRequest(region_id=REGION, lib_id=lib_id), RUNTIME)
    print("DeleteKeywordLib:", brief(r.body.to_map()))
    state["cleaned"] = True
    save_state(state)
    print("✅ 清理完成")


def cost_report():
    guard_cost = guard_calls * 15 / 10000
    print("\n" + "=" * 30, "本次运行成本估算", "=" * 30)
    print(f"  护栏检测: {guard_calls} 次 × 0.0015 元 = {guard_cost:.4f} 元")
    print(f"  glm-5.3 : {llm_calls} 次, tokens={llm_tokens}（按量计费，预估 < 0.1 元）")
    print(f"  合计远低于 20 元预算 ✅")


if __name__ == "__main__":
    if not AK or not SK:
        raise SystemExit("❌ .env 缺少 Aliyun-AccessKey-ID / Aliyun-AccessKey-Secret")
    phase = sys.argv[1] if len(sys.argv) > 1 else "status"
    phases = {"status": phase_status, "baseline": phase_baseline, "setup": phase_setup,
              "verify": phase_verify, "e2e": phase_e2e, "cleanup": phase_cleanup}
    if phase == "all":
        for name in ("status", "baseline", "setup"):
            phases[name]()
        print("\n⏳ 等待 60s 让词库配置生效...")
        time.sleep(60)
        phase_verify()
        phase_e2e()
    elif phase in phases:
        phases[phase]()
    else:
        raise SystemExit(f"未知阶段: {phase}，可选: {'/'.join(phases)}/all")
    cost_report()