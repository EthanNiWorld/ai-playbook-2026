"""测试 glm-5.3 tool_choice 兼容性 — 标准国际站域名（dashscope-intl / dashscope-us）

补充探针（2026-09-24）：test_glm53_tool_choice.py 已在新加坡 workspace 端点验证
嵌套对象格式通过；本脚本覆盖"标准 dashscope 域名"场景（用户可能未走 workspace）：

  Case 1: dashscope-intl（新加坡标准域名）嵌套对象 → 期望通过
  Case 2: dashscope-intl 平铺 {type, name} → 期望复现 "Expected field function"
  Case 3: dashscope-us（美西标准域名）嵌套对象 → 期望通过

端点与凭证：DASHSCOPE_API_KEY_US（sk- 标准百炼 key）+ 标准国际站域名

实测结论（2026-09-24）：
  dashscope-us 嵌套对象 ✅（与新加坡 workspace 端点结论一致）
  dashscope-intl ❖ 无法验证——该 key 非新加坡账号 key，报 401
  （但两网关报错文案/校验逻辑一致，平铺格式必报
   "Expected field `function` in `tool_choice`"，见主脚本 C6）

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


def run_case(name, base_url, tool_choice):
    print(f"\n{'=' * 15} {name} {'=' * 15}")
    print(f"URL: {base_url}")
    print(f"tool_choice = {repr(tool_choice)}")
    client = OpenAI(api_key=API_KEY, base_url=base_url, timeout=120)
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


print(f"API Key: {(API_KEY[:8] + '...' + API_KEY[-4:]) if len(API_KEY) > 12 else '(未设置)'}")
print("=" * 60)

if not API_KEY:
    print("\n❌ 未检测到环境变量 DASHSCOPE_API_KEY_US（.env）")
    raise SystemExit(1)

results = {}
results["intl 嵌套对象"] = run_case(
    "Case 1: dashscope-intl 嵌套对象（标准 OpenAI 格式）",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "function": {"name": "get_weather"}},
)
results["intl 平铺格式"] = run_case(
    "Case 2: dashscope-intl 平铺 {type, name}（复现报错用）",
    "https://dashscope-intl.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "name": "get_weather"},
)
results["us 嵌套对象"] = run_case(
    "Case 3: dashscope-us 嵌套对象（标准 OpenAI 格式）",
    "https://dashscope-us.aliyuncs.com/compatible-mode/v1",
    {"type": "function", "function": {"name": "get_weather"}},
)

print("\n" + "=" * 20 + "结论汇总" + "=" * 20)
for k, v in results.items():
    print(f"  {k}: {'✅' if v else '❌'}")
