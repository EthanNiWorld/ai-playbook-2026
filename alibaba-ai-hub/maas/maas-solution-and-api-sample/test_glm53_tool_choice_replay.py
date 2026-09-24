"""逐字节重放客户原始请求体 — glm-5.3 tool_choice 400 排障终局验证

背景（2026-09-24）：
  客户坚持其发出的请求体就是下方 REPLAY_BODY（嵌套 tool_choice 格式），
  但服务端报 400 "Expected field `function` in `tool_choice`"。
  此前探针（test_glm53_tool_choice*.py）使用的是"语义等价"的请求
  （tools 无 additionalProperties:false、键顺序不同、经 openai SDK 重新
  序列化），客户可能质疑差异。本脚本把客户 JSON **原样字节**直接 POST
  （requests + data=原始字符串 encode，不经任何 JSON 重序列化），
  三个国际站端点并行重放：

  端点 1: 新加坡 workspace（DASHSCOPE_API_KEY_INTL_SG_TEST + _URL）
  端点 2: 国际站北京 workspace（DASHSCOPE_API_KEY_INTL_BJ_TEST + _URL）
  端点 3: 美西标准域名（DASHSCOPE_API_KEY_US + dashscope-us）

  若全部通过 → 这份 JSON 文本本身合法，问题锁定在客户侧
  "代码构造 → 网络字节"之间（SDK 序列化改写 / 中间代理改写）；
  若失败 → 抓住差异（additionalProperties 或其他）继续深挖。

实测结论（2026-09-24）：
  三端点全部 HTTP 200（含模型正常思考与响应）——客户提供的原始 JSON
  逐字节合法，阿里云国际站对该字节串不会报 400。结合平铺格式三端点
  均报同一 400（见 test_glm53_tool_choice*.py）：客户实际到服务端的
  字节流与其贴出的请求体不一致，tool_choice 在发送链路上丢失了
  function 子对象。定位方向：SDK 序列化改写（dashscope 原生 SDK /
  LangChain / 自研封装）、企业中间代理改写、或应用层打印时机不当
  （打印的是序列化前的对象）。
"""
import os
from concurrent.futures import ThreadPoolExecutor

import requests

env_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), ".env")
if os.path.exists(env_path):
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                k, v = line.split("=", 1)
                os.environ[k.strip()] = v.strip()

# ↓↓↓ 客户提供的原始请求体，逐字符保留（键顺序、additionalProperties、缩进均未动）
REPLAY_BODY = """{
  "messages": [
    {
      "content": "请处理上海相关的信息。",
      "role": "user"
    }
  ],
  "model": "glm-5.3",
  "tool_choice": {
    "function": {
      "name": "get_weather"
    },
    "type": "function"
  },
  "tools": [
    {
      "function": {
        "description": "查询指定城市的当前天气",
        "name": "get_weather",
        "parameters": {
          "additionalProperties": false,
          "properties": {
            "location": {
              "type": "string"
            }
          },
          "required": [
            "location"
          ],
          "type": "object"
        }
      },
      "type": "function"
    },
    {
      "function": {
        "description": "查询指定城市的当前时间",
        "name": "get_current_time",
        "parameters": {
          "additionalProperties": false,
          "properties": {
            "location": {
              "type": "string"
            }
          },
          "required": [
            "location"
          ],
          "type": "object"
        }
      },
      "type": "function"
    }
  ]
}"""

ENDPOINTS = [
    ("新加坡workspace",
     os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST_URL", "").strip().rstrip("/") + "/chat/completions",
     os.getenv("DASHSCOPE_API_KEY_INTL_SG_TEST", "").strip()),
    ("国际站北京workspace",
     os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST_URL", "").strip().rstrip("/") + "/chat/completions",
     os.getenv("DASHSCOPE_API_KEY_INTL_BJ_TEST", "").strip()),
    ("美西标准域名",
     "https://dashscope-us.aliyuncs.com/compatible-mode/v1/chat/completions",
     os.getenv("DASHSCOPE_API_KEY_US", "").strip()),
]


def replay(name, url, key):
    if not url or not key:
        return name, None, "缺 key/URL，跳过"
    try:
        r = requests.post(
            url,
            data=REPLAY_BODY.encode("utf-8"),  # 原始字节，不重序列化
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": "application/json",
            },
            timeout=300,
        )
        body = r.text[:400].replace("\n", " ")
        return name, r.status_code, body
    except Exception as e:
        return name, None, f"{type(e).__name__}: {str(e)[:200]}"


if __name__ == "__main__":
    print(f"重放体大小: {len(REPLAY_BODY.encode('utf-8'))} bytes（逐字节原样）")
    print("=" * 60)
    with ThreadPoolExecutor(max_workers=3) as pool:
        for name, code, body in pool.map(lambda a: replay(*a), ENDPOINTS):
            status = "✅" if code == 200 else "❌"
            print(f"\n[{name}] HTTP {code} {status}")
            print(f"  {body}")

    print("\n" + "=" * 20 + "结论" + "=" * 20)
    print("若三端点均 200：客户 JSON 文本本身合法，400 根因在客户侧")
    print("发送链路（SDK 序列化改写或中间代理改写），需客户 curl 重放+抓包定位。")
