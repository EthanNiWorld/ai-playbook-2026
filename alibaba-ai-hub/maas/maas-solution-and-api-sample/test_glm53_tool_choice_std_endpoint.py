"""测试 glm-5.3 tool_choice 兼容性 — 标准国际站域名 + 国际站北京 workspace

补充探针（2026-09-24）：test_glm53_tool_choice.py 已在新加坡 workspace 端点验证
嵌套对象格式通过；本脚本覆盖其他网关场景（用户可能未走 workspace）：

  Case 1: dashscope-intl（新加坡标准域名）嵌套对象 → 期望通过
  Case 2: dashscope-intl 平铺 {type, name} → 期望复现 "Expected field function"
  Case 3: dashscope-us（美西标准域名）嵌套对象 → 期望通过
  Case 4: dashscope-us 平铺 {type, name} → 在标准域名上补全复现证据
    （初版因 Case 2 撞 401 未能在标准域名复现，Case 4 填补该缺口）
  Case 5: 国际站北京 workspace（cn-beijing maas 网关）嵌套对象 → 第三条链路交叉验证
  Case 6: 国际站北京 workspace 平铺 {type, name} → 复现报错

端点与凭证：
  DASHSCOPE_API_KEY_US（sk- 标准百炼 key）+ dashscope-intl / dashscope-us
  DASHSCOPE_API_KEY_INTL_BJ_TEST（sk-ws- workspace key）+ 对应 _URL

实测结论（2026-09-24，三条链路交叉验证）：
  dashscope-us 嵌套对象 ✅（与新加坡 workspace 端点结论一致）
  dashscope-us 平铺 {type, name} ❌ —— 精确复现报错
     "Expected field `function` in `tool_choice`"（Case 4）
  国际站北京 workspace（cn-beijing maas 网关）嵌套对象 ✅（Case 5，
     但该端点 glm-5.3 首 token 较慢，采样 41 chunks 耗时 ~152s）
  国际站北京 workspace 平铺 ❌ 精确复现同一报错（Case 6）
  → 三条链路（新加坡 workspace / 美西标准域名 / 国际站北京 workspace）
     校验行为完全一致：嵌套通过、平铺报同一错误，彻底排除网关差异
  dashscope-intl ❖ 无法验证——该 key 非新加坡账号 key，报 401

排障建议（可直接转述给客户）：
  报错 "Expected field `function` in `tool_choice`" 仅在 tool_choice 含
  type:"function" 但缺 function 字段时触发；客户贴出的标准嵌套格式实测能通
  → 实际发出的请求体与贴出的不一致（大概率 tool_choice 被拍平）。

  修复三步：
  1. 抓真实请求体：发送前 print(json.dumps(payload, ensure_ascii=False))，
     大概率可见 tool_choice 被拍平为 {"type":"function","name":"get_weather"}
     或只剩 {"type":"function"}
  2. 改回标准嵌套格式（即客户原本贴出的样子，无需变动）：
     {"type": "function", "function": {"name": "get_weather"}}
  3. 排查改写来源（谁把结构拍平了）：
     a) 手写 dict 时少写了一层 function 嵌套
     b) 从智谱开放平台（bigmodel.cn）官方 SDK/旧封装迁移时，中间转换层
        带过来的非 OpenAI 格式
     c) LangChain / Dify 等中间框架序列化改写——绕过框架裸发一次 curl
        即可定位是否框架问题（openai 官方 SDK 直接传 dict 是原样透传，
        不会改写结构）

  给客户的一句话答复：你贴的请求体格式正确、实测能通；报错说明实际请求里
  tool_choice 丢了 function 字段，打印一下真实请求体，把拍平/丢字段的那层
  代码修正为标准嵌套格式即可。
"""
from openai import OpenAI
import os
import time

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

API_KEY = os.getenv("DASHSCOPE_API_KEY_US", "").strip()
API_KEY_BJ = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", "").strip()
URL_BJ = os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "").strip() or \
    "https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"

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


def run_case(name, base_url, tool_choice, api_key):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    print(f"URL: {base_url}")
    print(f"tool_choice = {repr(tool_choice)}")
    client = OpenAI(api_key=api_key, base_url=base_url, timeout=120)
    t0 = time.time()
    try:
        stream = client.chat.completions.create(
            model="glm-5.3", messages=MESSAGES, tools=TOOLS,
            tool_choice=tool_choice, stream=True,
        )
        tool_calls_head = []
        n = 0
        for i, chunk in enumerate(stream):
            n = i + 1
            if chunk.choices and chunk.choices[0].delta.tool_calls:
                for tc in chunk.choices[0].delta.tool_calls:
                    if tc.function and tc.function.name:
                        tool_calls_head.append(tc.function.name)
            if i >= 40 or (tool_calls_head and i >= 8):
                break
        ms = (time.time() - t0) * 1000
        if tool_calls_head:
            print(f"✅ PASS（{ms:.0f}ms）→ 工具调用：{tool_calls_head}")
        else:
            print(f"✅ 参数校验通过（{ms:.0f}ms，采样 {n} chunks）")
        return True
    except Exception as e:
        ms = (time.time() - t0) * 1000
        msg = str(e).replace("\n", " ")[:300]
        print(f"❌ FAIL（{ms:.0f}ms）：{type(e).__name__}: {msg}")
        return False


print(f"API Key(US):  {(API_KEY[:8] + '...' + API_KEY[-4:]) if len(API_KEY) > 12 else '(未设置)'}")
print(f"API Key(BJ):  {(API_KEY_BJ[:8] + '...' + API_KEY_BJ[-4:]) if len(API_KEY_BJ) > 12 else '(未设置)'}")
print("=" * 60)

if not API_KEY:
    print("\n❌ 未检测到环境变量 DASHSCOPE_API_KEY_US（.env）")
    raise SystemExit(1)

results = {}
results["intl 嵌套对象"] = run_case(
    "Case 1: dashscope-intl 嵌套对象（标准 OpenAI 格式）",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "function": {"name": "get_weather"}},
    API_KEY,
)
results["intl 平铺格式"] = run_case(
    "Case 2: dashscope-intl 平铺 {type, name}（复现报错用）",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "name": "get_weather"},
    API_KEY,
)
results["us 嵌套对象"] = run_case(
    "Case 3: dashscope-us 嵌套对象（标准 OpenAI 格式）",
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "function": {"name": "get_weather"}},
    API_KEY,
)
results["us 平铺格式"] = run_case(
    "Case 4: dashscope-us 平铺 {type, name}（标准域名复现用）",
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "name": "get_weather"},
    API_KEY,
)
if API_KEY_BJ:
    results["bj-ws 嵌套对象"] = run_case(
        "Case 5: 国际站北京 workspace 嵌套对象（第三条链路）",
        URL_BJ,
        {"type": "function", "function": {"name": "get_weather"}},
        API_KEY_BJ,
    )
    results["bj-ws 平铺格式"] = run_case(
        "Case 6: 国际站北京 workspace 平铺 {type, name}（复现用）",
        URL_BJ,
        {"type": "function", "name": "get_weather"},
        API_KEY_BJ,
    )
else:
    print("\n⚠️ 未检测到 DASHSCOPE_API_KEY_INTL_BJ_TEST，跳过 Case 5/6")

print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
for k, v in results.items():
    print(f"  {k}: {'✅' if v else '❌'}")
