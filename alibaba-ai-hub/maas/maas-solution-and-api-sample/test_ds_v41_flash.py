"""
DeepSeek-V4.1-Flash 实测脚本（对比 deepseek-v4-flash-0731）
============================================================

背景
----
- DeepSeek V4.1 Flash 于 2026-09-10 发布：552B MoE，全新 Causal-Encoder-Decoder 结构，
  输入激活 8B / 输出激活 16B（非对称），原生多模态视觉理解。
- 官方 API 模型名: deepseek-flash；百炼平台模型名: deepseek-v4.1-flash。
- 旧模型 deepseek-v4-flash / deepseek-v4-flash-vision-exp 已下线，
  官方 API 侧旧模型名暂时路由到 V4.1 Flash；百炼侧 deepseek-v4-flash-0731 快照仍在列表中。

本脚本做三件事
--------------
1. 探测 deepseek-v4.1-flash 在哪些节点可用（US legacy 域名 / 北京 workspace / 新加坡 workspace）
2. 用相同 prompt 对比 deepseek-v4.1-flash 与 deepseek-v4-flash-0731 的 TTFT / tokens / reasoning tokens
3. 验证 deepseek-v4.1-flash 在百炼上是否接受图像输入（原生多模态）

说明
----
- 单次冒烟测试，非严谨 benchmark；TTFT 受网络/时段影响，仅供数量级参考
- .env 从工作区根目录（向上 3 级）加载，密钥不打印、不落盘
"""

import base64
import os
import time
from pathlib import Path

from openai import OpenAI

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

CANDIDATES = [
    ("US 节点(legacy域名)", "DASHSCOPE_API_KEY_US",
     "https://dashscope-us.aliyuncs.com/compatible-mode/v1"),
    ("北京节点(workspace)", "DASHSCOPE_API_KEY_INTL_BJ_TEST",
     "https://llm-kvw0aiysjfv4g6fh.cn-beijing.maas.aliyuncs.com/compatible-mode/v1"),
    ("新加坡节点(workspace)", "DASHSCOPE_API_KEY_INTL_SG_TEST",
     "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"),
    ("SGP 主Key(workspace)", "DASHSCOPE_API_KEY_SGP",
     "https://llm-ablnum2bgfvl34hs.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"),
]

# 1x1 红色像素 PNG，用于探测图像输入是否被接受
TINY_PNG_B64 = ("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR4"
                "2mP8z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def probe_v41_flash():
    """探测 deepseek-v4.1-flash 可用节点，返回 (label, key, base_url) 或 None"""
    print("=" * 70)
    print("STEP 1: 探测 deepseek-v4.1-flash 可用节点")
    print("=" * 70)
    for label, key_var, base_url in CANDIDATES:
        key = ENV.get(key_var)
        if not key:
            print(f"  [跳过] {label}: {key_var} 未设置")
            continue
        client = OpenAI(api_key=key, base_url=base_url, timeout=90)
        try:
            t0 = time.time()
            stream = client.chat.completions.create(
                model="deepseek-v4.1-flash",
                messages=[{"role": "user", "content": "回复两个字：在的"}],
                stream=True,
                max_tokens=256,
            )
            first_ttft, served_model, out = None, "", ""
            for chunk in stream:
                if getattr(chunk, "model", None):
                    served_model = chunk.model
                if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                    if first_ttft is None:
                        first_ttft = time.time() - t0
                    out += chunk.choices[0].delta.content
            ttft_str = f"{first_ttft:.2f}s" if first_ttft is not None else "无content(思考吃满max_tokens)"
            print(f"  [成功] {label} | TTFT={ttft_str} | served={served_model} | 输出: {out[:40]!r}")
            return label, key, base_url
        except Exception as e:
            print(f"  [失败] {label}: {str(e)[:180]}")
    return None


def compare_flash_models(label, key, base_url):
    """相同 prompt 冒烟对比 deepseek-v4.1-flash vs deepseek-v4-flash-0731"""
    print()
    print("=" * 70)
    print(f"STEP 2: 冒烟对比（节点: {label}，单次测试非严谨 benchmark）")
    print("=" * 70)
    client = OpenAI(api_key=key, base_url=base_url, timeout=180)
    prompt = "用三句话解释什么是 MoE（混合专家）架构，为什么能省算力。"
    results = {}
    for model in ["deepseek-v4.1-flash", "deepseek-v4-flash-0731"]:
        print(f"\n>>> {model}")
        try:
            t0 = time.time()
            stream = client.chat.completions.create(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                stream=True,
                stream_options={"include_usage": True},
                max_tokens=1024,
            )
            ttft, served_model, content, reasoning = None, "", "", ""
            usage = None
            for chunk in stream:
                if getattr(chunk, "model", None):
                    served_model = chunk.model
                if chunk.usage:
                    usage = chunk.usage
                    continue
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                rc = getattr(delta, "reasoning_content", None)
                if rc:
                    reasoning += rc
                if delta and delta.content:
                    if ttft is None:
                        ttft = time.time() - t0
                    content += delta.content
            total = time.time() - t0
            u = usage
            reason_toks = None
            if u and getattr(u, "completion_tokens_details", None):
                reason_toks = getattr(u.completion_tokens_details, "reasoning_tokens", None)
            print(f"  served model : {served_model}")
            print(f"  TTFT         : {ttft:.2f}s" if ttft is not None else "  TTFT         : N/A(思考吃满max_tokens)")
            print(f"  总耗时       : {total:.2f}s")
            if u:
                print(f"  tokens       : in={u.prompt_tokens} out={u.completion_tokens} "
                      f"(reasoning={reason_toks})")
            else:
                print("  tokens       : N/A")
            print(f"  回答摘要     : {content[:120]!r}")
            results[model] = {"ttft": ttft, "total": total, "usage": u}
        except Exception as e:
            print(f"  [错误] {str(e)[:200]}")
    return results


def test_vision(label, key, base_url):
    """验证 deepseek-v4.1-flash 是否接受图像输入（原生多模态）"""
    print()
    print("=" * 70)
    print("STEP 3: deepseek-v4.1-flash 图像输入探测（百炼侧）")
    print("=" * 70)
    client = OpenAI(api_key=key, base_url=base_url, timeout=120)
    try:
        stream = client.chat.completions.create(
            model="deepseek-v4.1-flash",
            messages=[{
                "role": "user",
                "content": [
                    {"type": "text", "text": "这张图里是什么颜色？一个词回答。"},
                    {"type": "image_url",
                     "image_url": {"url": f"data:image/png;base64,{TINY_PNG_B64}"}},
                ],
            }],
            stream=True,
            max_tokens=1024,
        )
        out = ""
        for chunk in stream:
            if chunk.choices and chunk.choices[0].delta and chunk.choices[0].delta.content:
                out += chunk.choices[0].delta.content
        print(f"  [图像输入被接受] 回答: {out[:60]!r}")
    except Exception as e:
        print(f"  [图像输入被拒绝/报错] {str(e)[:220]}")


if __name__ == "__main__":
    found = probe_v41_flash()
    if not found:
        print("\n所有候选节点均无法调用 deepseek-v4.1-flash，请先在百炼控制台对应地域完成模型授权。")
        raise SystemExit(1)
    label, key, base_url = found
    compare_flash_models(label, key, base_url)
    test_vision(label, key, base_url)
