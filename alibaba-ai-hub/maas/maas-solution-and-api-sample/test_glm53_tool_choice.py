"""测试 glm-5.3 tool_choice 兼容性 — 阿里云国际站（新加坡 workspace 端点）

背景（2026-09-24）：
  在阿里云国际站调用 glm-5.3 指定 tool_choice 强制函数调用时报 400：
  <400> InvalidParameter: Expected field `function` in `tool_choice`.
  Correct usage: `{"type": "function", "function": {"name": "my_function"}}`
  —— 但请求体中 tool_choice 已是报错提示的"正确用法"（嵌套对象格式），
  疑似服务端对 tool_choice 对象形式的解析与 OpenAI 标准不一致。

探针用例：
  Case 1: 原始请求原样重放（tool_choice 嵌套对象 {"type","function","name"}）→ 复现 400
  Case 2: tool_choice = "auto"（字符串）
  Case 3: tool_choice = "required"（字符串）
  Case 4: tool_choice = "none"（字符串）
  Case 5: 不传 tool_choice（默认行为，看模型是否自主调用 get_weather）
  Case 6: 非标准平铺格式 {"type": "function", "name": "get_weather"} → 探测服务端期望
  Case 7: 对照组 — qwen3.8-max 用 Case 1 同样的嵌套对象格式 → 判断是 glm-5.3 专属还是端点整体行为

端点与凭证：DASHSCOPE_API_KEY_INTL_SG_TEST + DASHSCOPE_API_KEY_INTL_SG_TEST_URL（.env）
模型 ID：glm-5.3 / qwen3.8-max（国际站 workspace 端点）

验证技巧：tool_choice 非法时 400 会立即抛出（不耗 token）；合法时用
stream + 首 chunk break 快速确认通过（避免等待 glm-5.3 完整思考+生成）。

实测结论（2026-09-24，新加坡 workspace + 美西 dashscope-us 交叉验证，
后者见 test_glm53_tool_choice_std_endpoint.py）：
  C1 嵌套对象（用户原始请求）✅ —— 两端点均通过，且模型正确发起 get_weather 调用
  C2/C3/C4/C5 'auto'/'required'/'none'/不传 均 ✅（参数校验通过）
  C6 平铺 {"type": "function", "name": ...} ❌ —— 精确复现报错
     "Expected field `function` in `tool_choice`"
  → 根因：用户实际发出的请求体中 tool_choice 缺少 function 字段
    （大概率被拍平为 {"type":"function","name":"get_weather"}），
    与用户贴出的 JSON 不一致；标准嵌套格式本身无需修改。
  附带发现 C7：同端点 qwen3.8-max 在思考模式下不支持 tool_choice 为
  required/对象（报 "The tool_choice parameter does not support being set to
  required or object in thinking mode"），glm-5.3 无此限制。
"""
from openai import OpenAI
import os
import time

# 加载 .env（.env 已被 .gitignore 忽略，密钥不会进 Git）
env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()
BASE_URL = os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip() or \
    "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询指定城市的当前天气",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_current_time",
            "description": "查询指定城市的当前时间",
            "parameters": {
                "type": "object",
                "properties": {"location": {"type": "string"}},
                "required": ["location"],
            },
        },
    },
]

MESSAGES = [{"role": "user", "content": "请处理上海相关的信息。"}]


def run_case(name, model, tool_choice="DEFAULT"):
    """执行单用例。tool_choice 传 DEFAULT 表示不传该参数；None 表示显式 null。"""
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    kwargs = dict(model=model, messages=MESSAGES, tools=TOOLS, stream=True)
    if tool_choice != "DEFAULT":
        kwargs["tool_choice"] = tool_choice
    tc_desc = "(不传)" if tool_choice == "DEFAULT" else repr(tool_choice)
    print(f"tool_choice = {tc_desc}")
    t0 = time.time()
    try:
        stream = client.chat.completions.create(**kwargs)
        # 首 chunk 即视为通过（参数校验已过），再收几块看是否有 tool_calls 苗头
        first = None
        tool_calls_head = []
        for i, chunk in enumerate(stream):
            if i == 0:
                first = chunk
                # 参数校验已通过
            if chunk.choices and chunk.choices[0].delta.tool_calls:
                for tc in chunk.choices[0].delta.tool_calls:
                    if tc.function and tc.function.name:
                        tool_calls_head.append(tc.function.name)
            if i >= 40 or (tool_calls_head and i >= 8):
                break  # 收到工具名即可，不等待完整推理
        ms = (time.time() - t0) * 1000
        if tool_calls_head:
            print(f"✅ PASS（{ms:.0f}ms）→ 模型发起了工具调用：{tool_calls_head}")
        elif first is not None:
            print(f"✅ 参数校验通过（{ms:.0f}ms，采样 {i + 1} chunks，未观察到 tool_call 头）")
        return True
    except Exception as e:
        ms = (time.time() - t0) * 1000
        msg = str(e).replace("\n", " ")[:300]
        print(f"❌ FAIL（{ms:.0f}ms）：{type(e).__name__}: {msg}")
        return False


print(f"Base URL: {BASE_URL}")
print(f"Model:    glm-5.3（国际站新加坡 workspace）")
print(f"API Key:  {(API_KEY[:8] + '...' + API_KEY[-4:]) if len(API_KEY) > 12 else '(未设置)'}")
print("=" * 60)

if not API_KEY:
    print("\n❌ 未检测到环境变量 DASHSCOPE_API_KEY_INTL_SG_TEST（.env）")
    raise SystemExit(1)

client = OpenAI(api_key=API_KEY, base_url=BASE_URL, timeout=120)

results = {}

# Case 1: 原始请求原样重放（用户报错的格式）
results["C1 glm-5.3 嵌套对象(原始)"] = run_case(
    "Case 1: glm-5.3 tool_choice 嵌套对象（用户原始请求，复现 400）",
    "glm-5.3",
    {"type": "function", "function": {"name": "get_weather"}},
)

# Case 2: 字符串 "auto"
results["C2 glm-5.3 'auto'"] = run_case(
    "Case 2: glm-5.3 tool_choice='auto'",
    "glm-5.3",
    "auto",
)

# Case 3: 字符串 "required"（强制调用某个工具但不指定哪个）
results["C3 glm-5.3 'required'"] = run_case(
    "Case 3: glm-5.3 tool_choice='required'",
    "glm-5.3",
    "required",
)

# Case 4: 字符串 "none"
results["C4 glm-5.3 'none'"] = run_case(
    "Case 4: glm-5.3 tool_choice='none'",
    "glm-5.3",
    "none",
)

# Case 5: 不传 tool_choice
results["C5 glm-5.3 不传"] = run_case(
    "Case 5: glm-5.3 不传 tool_choice（默认）",
    "glm-5.3",
)

# Case 6: 非标准平铺格式（探测服务端是否期望这种非 OpenAI 结构）
results["C6 glm-5.3 平铺格式"] = run_case(
    "Case 6: glm-5.3 tool_choice 平铺 {type, name}（非标准，探测用）",
    "glm-5.3",
    {"type": "function", "name": "get_weather"},
)

# Case 7: 对照组 — qwen3.8-max 同样嵌套对象格式
results["C7 qwen3.8-max 嵌套对象"] = run_case(
    "Case 7: 对照 qwen3.8-max tool_choice 嵌套对象（判断是否 glm-5.3 专属）",
    "qwen3.8-max",
    {"type": "function", "function": {"name": "get_weather"}},
)

print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
for k, v in results.items():
    print(f"  {k}: {'✅' if v else '❌'}")
