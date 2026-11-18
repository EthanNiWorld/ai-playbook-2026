"""
DeepSeek-V4.1-Flash(-1017) developer 角色拒绝问题复现脚本
==========================================================

背景
----
客户反馈：通过 DashScope 调用 ds1017 版本（deepseek-v4.1-flash-1017 快照）报错
"请求消息里使用了该模型不支持的 developer 角色，请求被直接拒绝。本次请求未产生费用。"
疑似 messages 中出现 role=developer，而接口只接受 system/assistant/user/tool/function。

本脚本做三件事
--------------
1. 在多个公共 compatible-mode 端点上，用 role=developer 复现 400 拒绝，记录原始错误体
2. 对照组：同一请求把 developer 换成 system，验证 200 正常返回（证明仅角色问题）
3. 横向对照：qwen 系列模型传 developer，判断拒绝发生在公共 Schema 层还是模型层

说明
----
- 非流式、max_tokens 极小、关闭思考，单次费用可忽略
- .env 从工作区根目录（向上 3 级）加载，Python 侧逐行解析，密钥不打印、不落盘
- 用 urllib 直接发 HTTP，保留服务端原始 status / error body（不被 SDK 包装）
"""

import json
import os
import time
import urllib.request
import urllib.error
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]


def load_env(path: Path) -> dict:
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if "  #" in v:
            v = v.split("  #")[0].strip()
        env[k] = v
    return env


ENV = load_env(ROOT / ".env")

# (标签, Key 变量, base_url 变量或固定值)
# 注：_URL 变量实际指向 workspace 专属推理端点；US 为真正的公共域名端点
ENDPOINTS = [
    ("CN 北京(workspace端点)", "DASHSCOPE_API_KEY_CN_TEST", "DASHSCOPE_API_KEY_CN_URL",
     "https://dashscope.aliyuncs.com/compatible-mode/v1"),
    ("国际站新加坡(workspace端点)", "DASHSCOPE_API_KEY_INTL_SG_TEST", "DASHSCOPE_API_KEY_INTL_SG_TEST_URL",
     "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    ("国际站北京(workspace端点)", "DASHSCOPE_API_KEY_INTL_BJ_TEST", "DASHSCOPE_API_KEY_INTL_BJ_TEST_URL",
     "https://dashscope-intl.aliyuncs.com/compatible-mode/v1"),
    ("US 弗吉尼亚(公共端点)", "DASHSCOPE_API_KEY_US", None,
     "https://dashscope-us.aliyuncs.com/compatible-mode/v1"),
]

DS_MODELS = ["deepseek-v4.1-flash-1017", "deepseek-v4.1-flash"]
QWEN_MODEL = "qwen3.8-flash"  # 横向对照：判断拒绝是公共 Schema 层还是 DeepSeek 模型层


def chat(base_url: str, key: str, model: str, messages: list, extra: dict | None = None):
    """非流式调用，返回 (http_status, 耗时s, 响应dict)"""
    body = {"model": model, "messages": messages, "max_tokens": 32, "stream": False}
    if extra:
        body.update(extra)
    req = urllib.request.Request(
        base_url.rstrip("/") + "/chat/completions",
        data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"},
        method="POST",
    )
    t0 = time.time()
    try:
        with urllib.request.urlopen(req, timeout=90) as resp:
            return resp.status, time.time() - t0, json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raw = e.read().decode("utf-8", errors="replace")
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError:
            parsed = {"raw": raw}
        return e.code, time.time() - t0, parsed
    except Exception as e:
        return -1, time.time() - t0, {"error": str(e)}


def brief(resp: dict) -> str:
    """提取关键信息：错误码/错误消息 或 usage/回答摘要"""
    if "error" in resp and isinstance(resp["error"], dict):
        err = resp["error"]
        return f"code={err.get('code')} | message={err.get('message')}"
    if "code" in resp:  # DashScope 原生错误格式
        return f"code={resp.get('code')} | message={resp.get('message')}"
    usage = resp.get("usage") or {}
    content = ""
    choices = resp.get("choices") or []
    if choices:
        content = (choices[0].get("message") or {}).get("content") or ""
    return (f"model={resp.get('model')} | usage={json.dumps(usage, ensure_ascii=False)} "
            f"| content={content[:50]!r}")


def run_case(label: str, base_url: str, key: str, model: str, first_role: str, extra=None):
    messages = [
        {"role": first_role, "content": "你是一个简洁的助手，回答尽量短。"},
        {"role": "user", "content": "回复两个字：在的"},
    ]
    status, elapsed, resp = chat(base_url, key, model, messages, extra)
    print(f"  [{label}] model={model} first_role={first_role} "
          f"-> HTTP {status} ({elapsed:.2f}s)")
    print(f"      {brief(resp)}")
    return status, resp


def main():
    for ep_label, key_var, url_var, default_url in ENDPOINTS:
        key = ENV.get(key_var)
        if not key:
            print(f"\n[跳过] {ep_label}: {key_var} 未设置")
            continue
        base_url = (ENV.get(url_var) if url_var else None) or default_url
        print("\n" + "=" * 70)
        print(f"端点: {ep_label} ({base_url})")
        print("=" * 70)

        # 先确认快照模型名有效（system 角色对照，若 404/model not exist 则记录）
        for model in DS_MODELS:
            print(f"\n--- {model} ---")
            # 1) 复现：developer 角色（关闭思考，省费用）
            run_case("复现", base_url, key, model, "developer",
                     extra={"enable_thinking": False})
            # 2) 对照：system 角色
            run_case("对照", base_url, key, model, "system",
                     extra={"enable_thinking": False})

        # 3) 横向对照：qwen 传 developer，判断拒绝层级
        print(f"\n--- 横向对照 {QWEN_MODEL} ---")
        run_case("对照", base_url, key, QWEN_MODEL, "developer",
                 extra={"enable_thinking": False})


if __name__ == "__main__":
    main()